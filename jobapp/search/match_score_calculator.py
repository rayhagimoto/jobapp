import asyncio
import re
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import logging
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables.base import Runnable

# Set LLMInterface logger to DEBUG for troubleshooting
logging.getLogger("jobapp.core.llm_interface").setLevel(logging.DEBUG)

# Use your core modules for configuration, sheets, and LLM interaction
from ..core.config_manager import ConfigManager
from ..core.sheets_manager import SheetsManager
from ..core.llm_interface import LLMInterface

# Import the prompt from the local module
from .match_score_calculator_prompt import MATCH_SCORE_PROMPT




class MatchScoreCalculator:
    """
    Calculates a match score for jobs in a Google Sheet based on a user's
    experiences against the job description, using multithreading for concurrency.
    """

    def __init__(self):
        print("[INFO] Initializing Match Score Calculator...")
        self.config = ConfigManager()
        # LLMInterface will be created per thread/task to avoid potential thread-safety issues
        # with internal connection pools or state if not designed for multi-threading.
        self.sheets = SheetsManager() # SheetsManager is shared, gspread handles thread-safety for append/update.
        
        # Get experiences path from config
        experiences_path = self._get_experiences_path()
        
        # Load user experiences once during initialization
        self.experiences_md = self._load_file(experiences_path)
        # Use the imported prompt constant
        self.prompt_template = MATCH_SCORE_PROMPT

        if not all([self.experiences_md, self.prompt_template]):
            raise RuntimeError("Failed to load one or more required context/prompt files.")

        self.logger = logging.getLogger("jobapp.search.match_score_calculator")

    def _get_experiences_path(self) -> Path:
        """Get the user experiences file path from config."""
        experiences_path = self.config.get_experiences_path()
        return Path(experiences_path)

    def _load_file(self, path: Path) -> str:
        """Safely loads a file into a string."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                print(f"[INFO] Successfully loaded '{path.name}'")
                return f.read()
        except FileNotFoundError:
            print(f"[ERROR] File not found: {path}")
            return ""

    def _get_match_score_column_index(self) -> int | None:
        """Finds the 1-based index of the 'MatchScore' column."""
        try:
            headers = self.sheets.sheet.row_values(1)
            return headers.index("MatchScore") + 1
        except ValueError:
            print("[ERROR] 'MatchScore' column not found in the sheet.")
            return None

    def _process_single_job_for_score(self, job_data: dict, row_index: int, **llm_kwargs) -> tuple[int, int | None, str]:
        """
        Processes a single job to calculate its match score.
        This method will be run in a separate thread.
        Returns (row_index, score, message)
        """
        # Each thread gets its own LLMInterface instance to prevent thread-safety issues
        # with internal HTTP clients or state.
        llm_interface_per_thread = LLMInterface(self.config)
        llm = llm_interface_per_thread._get_llm("match_score")
        # Build the prompt template using LangChain (match resume_writer style)
        prompt_template = ChatPromptTemplate.from_messages([
            HumanMessagePromptTemplate.from_template(self.prompt_template)
        ])
        input_dict = {
            "user_experiences": self.experiences_md,
            "job_description": job_data["JobDescription"],
        }
        try:
            self.logger.info(f"[LLM] Invoking match_score LLM with input: {input_dict}")
            chain = prompt_template | llm
            response = chain.invoke(input_dict)
            # If using ChatModel, response is an AIMessage; get the content
            if hasattr(response, "content"):
                result_text = response.content
            else:
                result_text = str(response)
            self.logger.info(f"[LLM] LLM response: {result_text}")
        except Exception as e:
            self.logger.error(f"LLM invocation failed: {e}")
            result_text = None

        if result_text:
            match = re.search(r'\d+', result_text)
            if match:
                score = int(match.group(0))
                msg = f"LLM returned score: {score}"
                print(f"[INFO] Job {row_index}: {msg}")
                return row_index, score, msg
            else:
                msg = f"Could not parse a number from LLM response: '{result_text}'"
                print(f"[ERROR] Job {row_index}: {msg}")
                return row_index, None, msg
        else:
            msg = "LLM returned no valid response."
            print(f"[ERROR] Job {row_index}: {msg}")
            return row_index, None, msg

    def run(self, max_workers: int = 1):
        """
        Main method to iterate through the sheet, calculate scores, and update.
        Uses ThreadPoolExecutor for parallel processing of LLM calls.
        """
        print("\n[INFO] Fetching all jobs from Google Sheet...")
        all_jobs = self.sheets.get_all_records()
        match_score_col_index = self._get_match_score_column_index()

        if not all_jobs or match_score_col_index is None:
            print("[INFO] No jobs to process or 'MatchScore' column missing. Exiting.")
            return

        unscored_jobs = []
        for i, job in enumerate(all_jobs):
            # gspread rows are 1-indexed, and we have a header row, so actual row_index = i + 2
            row_index = i + 2
            if not job.get("MatchScore"):
                unscored_jobs.append((job, row_index))
            # else:
            #     print(f"[INFO] Skipping job {i+1} (already has a score: {job.get('MatchScore')})")
        
        if not unscored_jobs:
            print("[INFO] No unscored jobs found. Exiting.")
            return

        print(f"\n[INFO] Found {len(unscored_jobs)} unscored jobs to process using {max_workers} threads.")

        futures = []
        # Using ThreadPoolExecutor to run _process_single_job_for_score concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for job_data, row_index in unscored_jobs:
                future = executor.submit(self._process_single_job_for_score, job_data, row_index)
                futures.append(future)

            # Process results as they complete
            for future in as_completed(futures):
                row_index, score, msg = future.result()
                if score is not None:
                    try:
                        print(f"[INFO] Job {row_index}: Updating sheet with score {score}.")
                        self.sheets.sheet.update_cell(row_index, match_score_col_index, score)
                        # Add a small delay for Sheets API rate limits
                        time.sleep(0.5) # Reduced from 1.5s as now concurrent
                    except Exception as e:
                        print(f"[ERROR] Job {row_index}: Failed to update sheet. Error: {e}")
                else:
                    print(f"[INFO] Job {row_index}: No score to update for this job.")
        
        print("\n[SUCCESS] Match score calculation complete.")


async def main():
    """Asynchronous entry point for the calculator."""
    calculator = MatchScoreCalculator()
    
    # You can customize the number of workers here
    calculator.run(max_workers=1) # Process 5 jobs concurrently


if __name__ == "__main__":
    asyncio.run(main())