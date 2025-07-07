# Configuration Reference

This document provides a comprehensive reference for JobApp's configuration system, updated to match the actual implementation in [jobapp/core/config_manager.py](../jobapp/core/config_manager.py) and related modules.

---

## Configuration Hierarchy

JobApp uses a layered configuration system with the following precedence (highest to lowest):

1. **Constructor Parameters / CLI Overrides**
2. **Environment Variables** (from `~/.config/jobapp/secrets/.env` by default)
3. **User Config Files** (`~/.config/jobapp/config/*.yaml`)
4. **Project Config Files** (`JobApp/configs/*.yaml`)
5. **Default Values** (hardcoded in code)

See: [jobapp/core/config_manager.py](../jobapp/core/config_manager.py)

---

## Directory Structure

```
~/.config/jobapp/
├── secrets/
│   └── .env                    # API keys and credentials (default load location)
├── auth/
│   ├── gspread_credentials.json # Google Sheets API credentials
│   └── linkedin_auth.json      # LinkedIn session state
├── data/
│   ├── resume.yaml            # Master resume content
│   └── experiences.md         # Detailed work history
├── logs/                      # Application logs
└── config/
    ├── default.yaml           # Global app settings
    ├── resume_writer.yaml     # Resume optimization settings
    └── search.yaml            # Job search configuration

./configs/
├── default.yaml               # Project-level fallback config
├── resume_writer.yaml         # Project-level resume config
├── search.yaml                # Project-level search config
└── prompts/                   # AI prompt templates
```

---

## Environment Variables

**Location:** `~/.config/jobapp/secrets/.env` (default)

### Required Variables

```bash
# AI API Keys (at least one required)
GOOGLE_API_KEY=           # Required for Gemini models
ANTHROPIC_API_KEY=        # Optional: For Claude models
OPENAI_API_KEY=           # Optional: For GPT models
OPENROUTER_API_KEY=       # Optional: For multi-model access
PERPLEXITY_API_KEY=       # Optional: For Perplexity models

# LinkedIn Credentials
LINKEDIN_USERNAME=        # Your LinkedIn login email
LINKEDIN_PASSWORD=        # Your LinkedIn password
```

### Optional Variables

```bash
# Path Overrides
DATA_DIR=                 # Override default data directory
AUTH_DIR=                 # Override default auth directory
LOG_DIR=                  # Override default log directory

# Debug Settings
DEBUG=true               # Enable debug logging
LOG_LEVEL=DEBUG         # Set specific log level
```

---

## Application Configuration

**Location:** `~/.config/jobapp/config/default.yaml` (user) or `JobApp/configs/default.yaml` (project fallback)

### Google Spreadsheet Settings

```yaml
google_spreadsheet:
  spreadsheet_id: "your-spreadsheet-id"  # Found in the sheet's URL
  tab_name: "Data"
```

### Resume Settings

```yaml
settings:
  models:
    resume_optimization:
      provider: "google"
      model: "gemini-2.5-flash"
      temperature: 0.7
      max_tokens: 2048
    # ... other model settings ...
```

---

## Google Sheets Integration

### Credentials

**Location:** `~/.config/jobapp/auth/gspread_credentials.json`

This file contains the Google service account credentials needed to access the spreadsheet. It should be obtained from the Google Cloud Console and contains sensitive authentication information.

### Sheet Structure

The tracking sheet must have the following columns:

```
A: Date Applied
B: Company
C: Position
D: Location
E: Match Score
F: Status
G: Notes
H: Job Description
I: Resume Version
J: Follow-up Date
```

### Configuration Priority

The Google Sheets configuration follows this priority order:

1. Constructor parameters (when creating a SheetsManager instance)
2. Configuration file (`default.yaml`)
3. Raises ValueError if neither is provided

Example usage in code:

```python
from jobapp.core.sheets_manager import SheetsManager

# Using config file values
sheets_manager = SheetsManager()

# Overriding config values
sheets_manager = SheetsManager(
    spreadsheet_id="custom-id",
    tab_name="CustomTab"
)
```

---

## Resume Configuration

**Location:** `~/.config/jobapp/config/resume_writer.yaml` (user) or `JobApp/configs/resume_writer.yaml` (project fallback)

### AI Model Settings

```yaml
settings:
  models:
    resume_optimization:
      provider: "google"
      model: "gemini-2.5-flash"
      temperature: 0.7
      max_tokens: 2048
    resume_validation:
      provider: "google"
      model: "gemini-2.0-flash"
      temperature: 0.2
      max_tokens: 1024
    resume_refinement:
      provider: "google"
      model: "gemini-2.0-flash"
      temperature: 0.5
      max_tokens: 1024
    resume_formatting:
      provider: "google"
      model: "gemini-1.5-flash"
      temperature: 0.3
      max_tokens: 512
```

### Section Optimization

- The pipeline uses `content.sections_to_optimize` for targeted optimization.
- If not present, it will attempt to infer section paths from the resume YAML structure.

```yaml
content:
  sections_to_optimize:
    - "profile.description"
    - "skills"
    - "experience[Company Name]"
    - "education[University]"
```

See: [get_section_paths() in config_manager.py](../jobapp/core/config_manager.py)

---

## Search Configuration

**Location:** `~/.config/jobapp/config/search.yaml` (user) or `JobApp/configs/search.yaml` (project fallback)

### Search Settings

```yaml
search:
  criteria:
    max_age_days: 30
    min_score: 0.8
    excluded_companies:
      - "Company A"
      - "Company B"
  browser:
    use_system_chrome: true
    headless: true
    timeout: 30000
  limits:
    max_pages: 10
    delay: 2000
    max_retries: 3
```

### Scoring Settings

```yaml
scoring:
  weights:
    skills: 0.4
    experience: 0.3
    education: 0.2
    location: 0.1
  thresholds:
    min_skills: 0.6
    min_experience: 0.5
```

---

## User Data Files

### Master Resume

**Location:** `~/.config/jobapp/data/resume.yaml`

```yaml
personal:
  name: "John Doe"
  email: "john@example.com"
  location: "San Francisco, CA"
profile:
  title: "Senior Software Engineer"
  description: "10+ years experience..."
experience:
  - company: "Tech Corp"
    title: "Senior Developer"
    dates: "2020-present"
    highlights:
      - "Led team of 5 engineers..."
education:
  - institution: "University"
    degree: "BS Computer Science"
    year: "2015"
skills:
  languages: ["Python", "JavaScript"]
  frameworks: ["React", "Django"]
  tools: ["Docker", "AWS"]
```

### Experiences Document

**Location:** `~/.config/jobapp/data/experiences.md`

```markdown
# Work Experience

## Tech Corp (2020-present)
Senior Developer
- Led development of microservices architecture
- Implemented CI/CD pipeline
- Reduced deployment time by 60%

## Previous Company (2018-2020)
...

# Projects

## Project A
- Technologies: Python, AWS
- Description: Built scalable data pipeline
...
```

---

## Logging Configuration

- Log level and format can be set via environment variables or code.
- Log files are written to `~/.config/jobapp/logs/` by default.

### Log Levels

```python
LOG_LEVEL = {
    "DEBUG": "Detailed debugging information",
    "INFO": "General operational information",
    "WARNING": "Warning messages for potential issues",
    "ERROR": "Error messages for failures",
    "CRITICAL": "Critical failures requiring immediate attention"
}
```

### Log Format

```python
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

---

## Configuration Validation

- The documentation references JSON schema validation, but this is **not currently implemented** in [config_manager.py](../jobapp/core/config_manager.py).
- All config files are loaded and parsed as YAML, with basic error handling for missing or invalid files.

---

## Development Configuration

- For development and testing, you can use:
  - `configs/local.yaml` for local overrides (git-ignored)
  - `configs/test.yaml` for test-specific settings
  - Set `DEBUG=true` in `.env` for additional logging 