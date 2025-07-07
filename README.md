# JobApp - Personal Job Application Automation Tool

JobApp is a powerful, personal command-line tool built in Python to automate and streamline your job application workflow. It combines automated job searching on LinkedIn with a sophisticated, AI-powered pipeline to tailor your resume for each specific job description, ensuring you always put your best foot forward.

## Core Features

- **Automated Job Search**: Scrapes LinkedIn for job postings based on your search queries.
- **AI-Powered Resume Tailoring**: Utilizes a multi-step, multi-agent AI workflow to analyze job descriptions and optimize your resume's content, focusing on keywords, skills, and impact.
- **Intelligent Job Matching**: Uses Google Sheets to track applications and can be used to score jobs against your profile.
- **Advanced Validation**: Includes an independent AI validation step to prevent exaggeration and ensure your resume remains truthful and authentic.
- **Cross-Platform**: Supports system Chrome installations on Linux, macOS, and Windows for stable web scraping.
- **Multi-LLM Support**: Integrates with major AI providers like Anthropic, Google, OpenAI, and any provider supported by OpenRouter.

---

## 🚀 Getting Started

Follow these steps to get JobApp up and running on your local machine.

### 1. Prerequisites

Before you begin, ensure you have the following system dependencies installed:

1.  **Python 3.12+** & **UV**: JobApp uses `uv` for package management.
2.  **LaTeX**: Required for compiling your resume into a PDF.
    -   **Ubuntu/Debian**: `sudo apt-get install texlive-latex-recommended texlive-latex-extra latexmk`
    -   **macOS**: `brew install mactex`
    -   **Windows**: Install [MiKTeX](https://miktex.org/) or [TeX Live](https://www.tug.org/texlive/).
3.  **Google Chrome**: Recommended for the most reliable LinkedIn scraping experience.

You can verify your installations by running `latexmk --version` and `google-chrome --version`.

### 2. Installation

```bash
# Clone the repository
git clone <repository-url>
cd JobApp

# Create and activate a virtual environment using UV
uv venv --python 3.12
source .venv/bin/activate  # For Linux/macOS
# .venv\Scripts\activate  # For Windows

# Install Python dependencies
uv pip install -r requirements.txt

# Install in editable mode for development
uv pip install -e .

# Install browser dependencies for Playwright
playwright install chromium
```

### 3. Configuration

JobApp requires a few configuration steps to connect to AI services and use your personal data.

#### **`.env` File (API Keys)**

Create a file named `.env` in the root of the project. This is where you'll store your secret API keys.

```bash
# .env file

# Required: Add API keys for the AI models you want to use
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_gemini_key
OPENAI_API_KEY=your_openai_key
OPENROUTER_API_KEY=your_openrouter_key # Recommended for access to many models
PERPLEXITY_API_KEY=your_perplexity_key
```

#### **Authentication Files (`.auth/`)**

This directory stores credentials for Google Sheets and LinkedIn. It is ignored by git.

-   **`gspread_credentials.json`**: For Google Sheets integration. Follow Google Cloud's documentation to create a service account, enable the Sheets API, and download the JSON key file. Place it in `.auth/gspread_credentials.json`.
-   **`linkedin_state.json`**: To enable automated LinkedIn scraping without logging in every time. Run the following command once to log in manually and save your session:
    ```bash
    python tests/manual_playwright_login.py
    ```

#### **User Data (`configs/user/`)**

This is where you store your personal resume content.

```bash
# First, copy the template directory
cp -r configs/user.template configs/user

# Then, edit the files inside configs/user/
```
-   **`experiences.md`**: Your complete work history, project details, and skills. This is the "source of truth" the AI uses to validate claims.
-   **`base_resume.yaml`**: The foundational YAML structure of your resume that will be optimized.
-   **`projects_summary.md`**: A summary of your projects for validation purposes.

---

## 📖 Common Usage

JobApp is designed to be run from the command line. Here are the most common commands.

### 1. Search for Jobs

Use the `search` command to find and scrape job listings from LinkedIn.

```bash
# Basic search for a "Data Scientist"
jobapp search "Data Scientist"

# Search with a location
jobapp search "Software Engineer" --location "San Francisco, CA"

# Use your system's Chrome browser (recommended for stability)
jobapp search "ML Engineer" --use-system-chrome
```
Job data is automatically saved to your configured Google Sheet.

### 2. Optimize a Resume for a Single Job

This is the core feature of JobApp. Use the `ai-optimize` command to tailor your resume for a specific job description.

```bash
# Run AI optimization for a job description saved in a file
jobapp resume-writer ai-optimize \
  --input-resume configs/user/base_resume.yaml \
  --job-description "path/to/job_description.txt" \
  --output-dir ./optimized_resumes

# You can also pass the job description directly as a string
jobapp resume-writer ai-optimize \
  --input-resume configs/user/base_resume.yaml \
  --job-description "Data Scientist position requiring Python, ML, and SQL..." \
  --output-dir ./optimized_resumes \
  --compile-pdf # Add this flag to also generate a PDF
```
The output directory will contain the optimized YAML resume, conversation transcripts with the AI, and the final PDF if requested.

### 3. Run Batch Optimization

To automatically optimize your resume for all promising jobs found during your search, use the batch processing script. This script reads from your Google Sheet, filters for high-match-score jobs you haven't applied to, and runs the AI optimization for each one.

```bash
# This script is not a direct CLI command, but is run as follows:
python -m jobapp.resume_writer.batch_optimizer
```
This is the most powerful workflow for applying to multiple jobs efficiently.

---

## 🏗️ Architecture & Advanced Details

For those interested in the underlying mechanics, JobApp is organized into several core modules:

- **`jobapp/core/`**: Manages configuration, logging, LLM interfacing, and Google Sheets connections.
- **`jobapp/search/`**: Handles all LinkedIn scraping and job data extraction.
- **`jobapp/resume_writer/`**: Contains the logic for both the traditional and the advanced AI-powered resume optimization pipelines. This is where the prompt engineering magic happens.
- **`configs/`**: Contains all configuration files, including the sophisticated prompts that guide the AI agents.

### The AI Optimization Pipeline

The resume optimization is not a single AI call. It's a multi-agent workflow designed for high-quality results:

1.  **Job Analysis**: An AI agent analyzes the job description to extract key skills and qualifications.
2.  **Evidence Assessment**: The AI cross-references the job's needs with your background in `experiences.md`.
3.  **Strategic Planning**: A plan is formed to strategically weave keywords into your resume while maintaining a natural flow.
4.  **Content Generation**: The resume content is rewritten based on the plan.
5.  **Validation Loop**: A separate, independent AI agent acts as a "validator," checking the new resume for any claims that seem exaggerated or untruthful.
6.  **Refinement**: If the validator flags issues, the resume is revised until it passes inspection.
7.  **PDF Generation**: The final, validated resume is compiled into a professional PDF.

This process ensures the final product is not only keyword-optimized but also authentic and high-quality. You can inspect the full AI conversation transcripts for every run in the output directory.

## Troubleshooting

- **PDF Compilation Errors**: Ensure LaTeX is correctly installed and accessible in your PATH. Check for this with `latexmk --version`.
- **Browser Crashes**: Always prefer using `--use-system-chrome` during job searches. It's more stable as it uses your existing Chrome installation.
- **Authentication Issues**: If LinkedIn scraping fails, refresh your session state by running `python tests/manual_playwright_login.py`.
