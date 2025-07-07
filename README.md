# JobApp: Personal Job Application Automation Tools

This repository contains a set of tools I built to help automate and streamline my job application workflows. **The setup is personal, a bit janky, and there may be mistakes in the installation instructions—use at your own risk!**

## Main Features

### 1. Job Search & Match Scoring
- **Scrape LinkedIn** for jobs based on a search query.
- **Save jobs to a Google Spreadsheet** for easy tracking and filtering.
- **Calculate a "MatchScore"** for each job using an LLM (Large Language Model) to estimate how relevant a job is to your background.

### 2. Automated Resume Tailoring
- **Resume editing is the most time-consuming and janky part of this project.** It's still under heavy development, and the process is not fully streamlined yet.
- I found that Google was giving away $300 worth of API credits, so I haven't really cared to optimize for token usage yet—but that's on the docket for future improvements.
- **Query the Google Spreadsheet** to get job info for the highest MatchScore jobs.
- **For each job, create a new output folder**:  
  `MatchScore_CompanyName_JobTitle_Location/`
- **Inside each folder:**
  - The job description (`job_description.md`)
  - The optimized resume as PDF (`YourName_CompanyName_JobTitle_Location.pdf`)
  - The YAML version of the resume
  - A `keywords.md` file with LLM-identified keywords
- **Sorting by MatchScore** is easy—just sort the folders locally.
- See [docs/ai_optimization.md](docs/ai_optimization.md) for more details.

### 3. Resume Compilation
- Uses my [resume compilation script](https://github.com/rayhagimoto/resume) (`compile_resume.py`) to turn YAML content into a professional PDF resume.
- You must clone/setup that repo as well for PDF generation.

### 4. LLM-Powered Keyword & Section Editing
- An agentic LLM routine attempts to subtly add relevant keywords to your resume.
- You can configure which sections are editable and which are not.
- The process outputs a `keywords.md` file for each job, listing the most important terms for quick reference.

#### Example `keywords.md` output:
```
KEYWORDS:
⦁   'Data Science'
⦁   'customer analytics'
⦁   'marketing data'
⦁   'customer behavior'
⦁   'statistical modeling'
⦁   'machine learning'
⦁   'pricing strategies'
⦁   'merchandising'
⦁   'finance'
⦁   'operations'
⦁   'predictive models'
⦁   'price elasticity'
⦁   'demand forecasting'
⦁   'customer segmentation'
⦁   'A/B testing'
⦁   'pricing optimization'
⦁   'data-driven insights'
⦁   'python'
⦁   'scikit-learn'
⦁   'XGBoost'
⦁   'SQL'
⦁   'data manipulation'
⦁   'large datasets'
⦁   'revenue management'
⦁   'AWS'
⦁   'Azure'
⦁   'GCP'
```

#### Example Output Folder Structure
```
MatchScore_CompanyName_JobTitle_Location/
├── job_description.md
├── keywords.md
├── YourName_CompanyName_JobTitle_Location.pdf
├── YourName_CompanyName_JobTitle_Location.yaml
```

## How I Organize My Optimized Resumes

This is just my personal way of keeping things organized—it's not required, but it works well for me:

- On my desktop, I have a folder called `optimized_resumes`.
- Inside that, I create a new subfolder for each day I apply to jobs (e.g., `2024-06-10/`, `2024-06-11/`).
- Each daily subfolder contains the output folders for each job I applied to that day, named like `MatchScore_CompanyName_JobTitle_Location/`.
- This helps me keep track of which jobs I applied to on which day, but you can organize things however you like.

Example:
```
optimized_resumes/
├── 2024-06-10/
│   ├── 88_SMU_PostdoctoralFellowInArtificialIntelligenceAndMachineLearning_DallasTX/
│   ├── 88_Amazon_AmazonRoboticsDataScientistCoOp2025_WestboroughMA/
│   └── ...
├── 2024-06-11/
│   ├── 85_Xometry_DataScientistII_LexingtonKY/
│   └── ...
```

## Caveats & Manual Review
- The LLM-based keyword and resume editing works well sometimes, but is not perfect. I always manually review resumes before submitting.
- The tools are designed for my own workflow and may require adaptation for others.

## Dependencies
- **Python 3.12+**
- **Google Sheets API credentials**
- **LinkedIn session state** (for scraping)
- **[resume](https://github.com/rayhagimoto/resume) repo** for PDF compilation

## ⚠️ Web Scraper Fragility

**Note:**
The LinkedIn web scraper is **very fragile** because it relies on specific CSS selectors and class name patterns that LinkedIn frequently changes. If scraping breaks, you’ll likely need to manually inspect the LinkedIn job search page and update the selectors in the code. *Inspect Element* and ChatGPT are your best friends for figuring out the right classes!

**What the Scraper Looks For:**
- **Job cards:**
  ```python
  "div[data-job-id]"
  ```
- **Job title link:**
  ```python
  'a[class*="job-card-container__link"]'
  ```
- **Company name:**
  ```python
  'div[class*="artdeco-entity-lockup__subtitle"] span'
  ```
- **Job details panel:**
  ```python
  ".jobs-search__job-details--wrapper"
  ```
- **Job description:**
  ```python
  f"{details_panel_selector} #job-details"
  ```
- **“See more” button for full description:**
  ```python
  f'{details_panel_selector} button[aria-label="Click to see more description"]'
  ```

If any of these selectors stop working, you’ll need to update them in `jobapp/search/linkedin_scraper.py`.

## Disclaimer
This project is a personal automation toolkit. Expect rough edges, missing features, and possible setup issues. PRs and suggestions are welcome, but the code is primarily for my own use.
