import asyncio
from pathlib import Path
import pandas as pd
from typing import List, Dict, Any, Optional
import re
import copy

from ..core.sheets_manager import SheetsManager
from ..core.config_manager import ConfigManager
from ..core.logger import get_logger
from ..utils.filename import get_resume_filenames
from ..utils.fuzzy_find import fuzzy_find_job
from jobapp.resume_writer.pipelines import ResumePipeline, OutputManager
from jobapp.core.llm_interface import LLMInterface
from .compiler import compile_pdfs

def _get_name_from_resume(resume_path: Path) -> str:
    """
    Extract the name from the resume YAML file at profile.name.
    Falls back to "DefaultName" if not found.
    """
    logger = get_logger(__name__)
    try:
        import yaml
        with open(resume_path, 'r', encoding='utf-8') as f:
            resume_data = yaml.safe_load(f)
        
        profile = resume_data.get('profile', {})
        name = profile.get('name', 'DefaultName')
        return name
    except Exception as e:
        logger.warning(f"Failed to extract name from resume file {resume_path}: {e}. Using fallback 'DefaultName'.")
        return "DefaultName"

async def get_job_by_query(query: str, config=None) -> Optional[Dict[str, Any]]:
    """Fetches jobs from sheets and fuzzy finds one based on a query."""
    logger = get_logger(__name__)
    try:
        sheets_manager = SheetsManager(config=config)
        jobs = sheets_manager.get_all_records()
        job = fuzzy_find_job(jobs, query)
        if not job:
            logger.error(f"No job found matching the query: '{query}'")
            return None
        return job
    except Exception as e:
        logger.error(f"Failed to fetch or find job by query: {e}", exc_info=True)
        return None

async def process_single_job(
    job_info: dict,  # Accept dict for both pd.Series and dict
    input_resume_path: Path,
    experiences_path: Path,
    output_dir: Path,
    overwrite: bool = False,
    compile_pdf: bool = True,
    your_name: str = None,
    OptimizationPipeline = ResumePipeline,  # Default to new pipeline
    config=None,
) -> Dict[str, Any]:
    """
    Processes a single job dict (from spreadsheet or manual input).
    This is the core, reusable logic for resume optimization.
    Now fully async: all blocking operations are run in threads.
    """
    logger = get_logger(__name__)
    import time
    start_time = time.time()
    try:
        job_title = job_info.get("JobTitle", "Unknown Job")
        company = job_info.get("Company", "Unknown Company")
        location = job_info.get("Location", "Remote")
        match_score = job_info.get("MatchScore", 0)
        job_description = job_info.get("JobDescription", "")

        if not your_name or not isinstance(your_name, str) or not your_name.strip():
            raise ValueError(
                "'your_name' must be provided to process_single_job. This should come from ConfigManager.get_user_name()."
            )

        # Load input resume and experiences (blocking I/O)
        import yaml
        input_resume = await asyncio.to_thread(lambda: yaml.safe_load(open(input_resume_path, 'r', encoding='utf-8')))
        experiences = await asyncio.to_thread(lambda: open(experiences_path, 'r', encoding='utf-8').read())

        section_paths = config.get_section_paths() if config else []

        # Set up job-specific logger
        import re
        sanitized_title = re.sub(r'[^a-zA-Z0-9_]', '', job_title)
        sanitized_company = re.sub(r'[^a-zA-Z0-9_]', '', company)
        job_log_name = f"job.{match_score}_{sanitized_company}_{sanitized_title}"
        filenames = get_resume_filenames(
            your_name=your_name,
            job_title=job_title,
            company=company,
            location=location,
            match_score=match_score
        )
        job_specific_output_dir = output_dir / filenames['dir']
        job_specific_output_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = job_specific_output_dir / 'job.log'
        job_logger = get_logger(name=job_log_name, log_file=log_file_path)

        job_logger.info(f"[START] Processing job: '{job_title}' at '{company}' (started at {time.strftime('%X')})")
        job_logger.info(f"-> Output will be in: {job_specific_output_dir}")
        job_logger.info(f"Input resume path: {input_resume_path}")
        job_logger.info(f"Experiences path: {experiences_path}")
        job_logger.info(f"Section paths: {section_paths}")

        # Run the pipeline (blocking, so run in thread)
        llm = LLMInterface(config=config)
        pipeline = OptimizationPipeline(config, llm, job_logger)
        pipeline_output = await asyncio.to_thread(
            lambda: pipeline.invoke(
                input_resume=input_resume,
                job_description=job_description,
                experiences=experiences
            )
        )

        # Save outputs (blocking, so run in thread)
        output_manager = OutputManager(job_logger, config=config)
        written = await asyncio.to_thread(
            lambda: output_manager.write_all_outputs(
                context=pipeline_output,
                job_info=job_info,
                your_name=your_name,
                base_output_dir=output_dir,
                compile_pdf=compile_pdf
            )
        )

        yaml_path = written.get('edited_resume_yaml')
        pdf_path = written.get('edited_resume_pdf')

        if not yaml_path or not Path(yaml_path).exists():
            job_logger.error("Optimization failed, no resume was generated.")
            return {"success": False, "skipped": False, "reason": "Optimization returned no content."}

        end_time = time.time()
        job_logger.info(f"[END] Finished job: '{job_title}' at '{company}' (ended at {time.strftime('%X')}, duration: {end_time - start_time:.2f}s)")

        return {
            "success": True,
            "skipped": False,
            "output_dir": str(yaml_path.parent),
            "pdf_path": str(pdf_path) if pdf_path and Path(pdf_path).exists() else None,
            "yaml_path": str(yaml_path)
        }
    except FileExistsError:
        logger.info(f"Skipping job for {job_title} at {company} - output directory exists and overwrite is not enabled.")
        return {"success": True, "skipped": True, "reason": "Output directory exists."}
    except Exception as e:
        logger.error(f"An unexpected error occurred while processing job '{job_title} at {company}'.", exc_info=True)
        return {"success": False, "skipped": False, "reason": str(e)}

async def run_batch_optimization(
    input_resume_path: Path,
    experiences_path: Path,
    output_dir: Path,
    match_score_threshold: int,
    max_resumes: int = None,
    overwrite: bool = False,
    compile_pdf: bool = True,
    your_name: str = None,
    config=None
):
    """
    Runs the entire batch optimization process.
    Args:
        input_resume_path: Path to the input resume YAML file.
        experiences_path: Path to the experiences file.
        output_dir: Directory to write outputs.
        match_score_threshold: Minimum match score to include a job.
        max_resumes: Max number of jobs to process (optional).
        overwrite: Whether to overwrite existing outputs (default: False).
        compile_pdf: Whether to compile PDFs (default: True).
        your_name: User's name (required for job output naming).
    """
    logger = get_logger(__name__)
    logger.info("Starting batch optimization process...")

    # Step 1: Fetch and filter data from Google Sheets
    try:
        sheets_manager = SheetsManager(config=config)
        df = sheets_manager.get_dataframe()
    except Exception as e:
        logger.error(f"Failed to fetch or process data from Google Sheets: {e}")
        return

    if df.empty:
        logger.warning("The Google Sheet is empty. No jobs to process.")
        return

    required_columns = ["MatchScore", "Applied", "JobTitle", "Company", "Location", "JobDescription"]
    if not all(col in df.columns for col in required_columns):
        logger.error(f"Missing one or more required columns in the Google Sheet: {required_columns}")
        return

    df["MatchScore"] = pd.to_numeric(df["MatchScore"], errors="coerce")
    df["Applied"] = df["Applied"].fillna("").astype(str).str.lower()
    filtered_df = df[
        (df["MatchScore"] > match_score_threshold) &
        (df["Applied"] != "true")
    ].copy()

    if filtered_df.empty:
        logger.info("No jobs met the criteria for batch optimization.")
        return

    filtered_df.sort_values(by="MatchScore", ascending=False, inplace=True)
    
    if max_resumes is None:
        resume_writer_config = config.get_yaml_config('resume_writer', default={})
        batch_settings = resume_writer_config.get("settings", {}).get("batch", {})
        max_resumes = batch_settings.get("max_resumes", 5)
        logger.info(f"Using max_resumes from config: {max_resumes}")
    else:
        logger.info(f"Using max_resumes override: {max_resumes}")

    jobs_to_process_df = filtered_df
    logger.info(f"Preparing to process up to {max_resumes} jobs (after skipping existing outputs if overwrite is False).")

    # Step 2: Dispatch jobs in a while loop, skipping existing outputs if overwrite is False
    dispatched = 0
    total_examined = 0
    tasks = []
    jobs_iter = jobs_to_process_df.iterrows()
    while dispatched < max_resumes:
        try:
            idx, row = next(jobs_iter)
        except StopIteration:
            break
        job_info = row.to_dict()
        job_title = job_info.get("JobTitle", "Unknown Job")
        company = job_info.get("Company", "Unknown Company")
        location = job_info.get("Location", "Remote")
        match_score = job_info.get("MatchScore", 0)
        filenames = get_resume_filenames(
            your_name=your_name,
            job_title=job_title,
            company=company,
            location=location,
            match_score=match_score
        )
        yaml_path = output_dir / filenames["yaml"]
        if not overwrite and yaml_path.exists():
            logger.info(f"[SKIP] Output YAML already exists for job '{job_title}' at '{company}' (path: {yaml_path}). Skipping.")
            continue
        # Otherwise, dispatch this job
        tasks.append(process_single_job(
            job_info=job_info,
            input_resume_path=input_resume_path,
            experiences_path=experiences_path,
            output_dir=output_dir,
            overwrite=overwrite,
            compile_pdf=compile_pdf,
            your_name=your_name,
            config=config
        ))
        dispatched += 1
    if not tasks:
        logger.info("No jobs to process after skipping existing outputs.")
        return []
    results = await asyncio.gather(*tasks)

    # Step 3: Compile PDFs if requested
    if compile_pdf and results:
        successful_optimizations = [
            r for r in results 
            if r.get("success") and not r.get("skipped") and r.get("yaml_path")
        ]
        if successful_optimizations:
            # Get cache_dir from config
            cache_dir = config.get_cache_path() if config else './build'
            cache_dir = Path(cache_dir)
            pdf_jobs = []
            for r in successful_optimizations:
                yaml_path = Path(r['yaml_path'])
                pdf_path = Path(r['pdf_path'])
                # Reconstruct job_dir from yaml_path's parent
                job_dir = yaml_path.parent
                build_dir = cache_dir / job_dir.name
                pdf_jobs.append((yaml_path, pdf_path, build_dir))
            await compile_pdfs(pdf_jobs)
        else:
            logger.info("No successful optimizations to compile PDF for.")

    logger.info("Batch processing complete.")
    return results 