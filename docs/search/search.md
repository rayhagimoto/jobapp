# JobApp Search Module – Developer Documentation

## Overview

The `jobapp/search` module provides all functionality for automated job searching (primarily on LinkedIn), job data extraction, and match score calculation using LLMs. It is designed for CLI-driven workflows, with a focus on extensibility, modularity, and robust browser automation.

---

## Code Organization

- **main.py**: CLI entrypoint. Handles argument parsing, subcommand dispatch, and high-level orchestration.
- **linkedin_scraper.py**: Core logic for browser automation, LinkedIn navigation, job scraping, and Google Sheets integration.
- **match_score_calculator.py**: Calculates job-to-candidate match scores using LLMs, updating results in Google Sheets.
- **match_score_calculator_prompt.py**: Contains the prompt template for LLM-based match scoring.
- **manual_login_playwright.py**: Script for manual LinkedIn login to obtain a valid session state for scraping.
- **__init__.py**: (empty, marks the directory as a package)

---

## CLI Usage

The main entrypoint is `main.py`, which exposes several subcommands:

### 1. Job Search (default / `search`)

**Purpose:**  
Automates job search and scraping on LinkedIn, saving results to Google Sheets.

**Usage:**  
```bash
python -m jobapp.search.main search "Data Scientist" --location="San Francisco" --max-pages=5 --browser-mode=patchright
```

**Arguments:**
- `job_title` (positional, required): One or more words describing the job title to search for.
- `--location` (optional): Location filter (currently stubbed, not fully implemented).
- `--max-results` (optional): Maximum number of jobs to fetch (stubbed).
- `--max-pages` (optional): Maximum number of LinkedIn result pages to scrape (overrides config).
- `--browser-mode` (optional, default: `patchright`):  
  - `patchright`: Stealth browser automation (recommended for avoiding detection).
  - `playwright`: Standard Playwright Chromium.
  - `system_chrome`: Uses your actual Chrome profile (for advanced users).
- `--chrome-path` (optional): Custom path to Chrome executable.
- `--chrome-profile` (optional): Custom path to Chrome user profile directory.
- `--verbose`: Enables detailed logging.
- `--use-system-chrome`: Deprecated; use `--browser-mode=system_chrome` instead.

**Example:**
```bash
python -m jobapp.search.main search "Software Engineer" --max-pages=3 --browser-mode=playwright
```

---

### 2. Match Score Calculation (`match-score`)

**Purpose:**  
Calculates a match score for each job in the Google Sheet using an LLM, based on the user's experiences and the job description.

**Usage:**  
```bash
python -m jobapp.search.main match-score
```

**Behavior:**
- Loads user experiences from the configured path.
- Iterates over all jobs in the Google Sheet.
- For each job without a match score, sends a prompt to the LLM and parses the numeric score.
- Updates the Google Sheet with the new score.
- Uses multithreading for concurrent LLM calls (configurable).

---

### 3. Manual LinkedIn Login (`login`)

**Purpose:**  
Allows the user to manually log in to LinkedIn in a browser, saving the session state for use in automated scraping.

**Usage:**  
```bash
python -m jobapp.search.main login --browser-mode=patchright
```

**Arguments:**
- `--browser-mode`: `patchright` (default), `playwright`, or `system_chrome` (not supported for login).
- `--chrome-path`, `--chrome-profile`: Present for API compatibility, but not used in manual login.

**Behavior:**
- Launches the selected browser.
- Navigates to the LinkedIn login page.
- Prompts the user to log in manually.
- After login, saves the session state to the path determined by `ConfigManager`.
- Required before running automated scraping if no valid session exists.

---

## Internal Architecture

### main.py

- Uses `argparse` to define subcommands: `search`, `match-score`, `login`.
- Dispatches to:
  - `run_linkedin_navigation_agent` (for job search)
  - `match_score_calculator.main()` (for match scoring)
  - `manual_login_playwright.manual_linkedin_login()` (for login)
- Handles deprecated flags and provides user feedback.

### linkedin_scraper.py

- **_LinkedinScraper**: Main class for scraping logic.
  - Supports three browser modes: `patchright`, `playwright`, `system_chrome`.
  - Handles browser/context setup, navigation, job extraction, and cleanup.
  - Uses human-like delays and actions to avoid detection.
  - Integrates with Google Sheets via an internal `SheetsManager` class.
  - Applies company blacklists and other filters from config.
- **run_linkedin_navigation_agent**: Async function called by CLI to orchestrate the scraping process.

### match_score_calculator.py

- **MatchScoreCalculator**: Class for LLM-based match scoring.
  - Loads user experiences and prompt template.
  - Uses a thread pool to process multiple jobs concurrently.
  - For each job, sends a prompt to the LLM and parses the numeric score.
  - Updates the Google Sheet with the result.
- **main()**: Async entrypoint for CLI use.

### manual_login_playwright.py

- Provides a function to launch a browser for manual LinkedIn login.
- Supports both Patchright and Playwright Chromium.
- Saves session state for later use by the scraper.

---

## Configuration & Extensibility

- All configuration is managed via `ConfigManager` (see core module rules).
- Paths, credentials, and settings are loaded hierarchically (env, user config, project config, defaults).
- Browser automation is abstracted to support new engines or stealth techniques.
- Google Sheets integration is modular and can be extended for other data stores.
- LLM provider and prompt can be customized via config and prompt files.

---

## Developer Notes

- **Adding New Sources**: To add new job sources, create a new scraper class and integrate it into the CLI and orchestration logic.
- **Extending Match Scoring**: Update the prompt template or scoring logic in `match_score_calculator.py` and `match_score_calculator_prompt.py`.
- **Debugging**: Use the `--verbose` flag and check logs for detailed output.
- **Session State**: Always ensure a valid LinkedIn session state is saved before scraping.
- **Thread Safety**: LLMInterface is instantiated per thread to avoid concurrency issues.

---

## Example Workflow

1. **Manual Login** (first time or when session expires):
   ```bash
   python -m jobapp.search.main login --browser-mode=patchright
   ```
2. **Job Search**:
   ```bash
   python -m jobapp.search.main search "Machine Learning Engineer" --max-pages=5
   ```
3. **Match Score Calculation**:
   ```bash
   python -m jobapp.search.main match-score
   ```

---

## File Reference

- `main.py`: CLI entrypoint, subcommand dispatcher.
- `linkedin_scraper.py`: Browser automation, scraping, Sheets integration.
- `match_score_calculator.py`: LLM-based scoring, concurrency.
- `match_score_calculator_prompt.py`: Prompt template for LLM.
- `manual_login_playwright.py`: Manual login utility.

--- 