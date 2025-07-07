# Configuration Reference

This document provides a comprehensive reference for JobApp's configuration system, including all available options, their purposes, and how they interact.

## Configuration Hierarchy

JobApp uses a layered configuration system with the following precedence (highest to lowest):

1. Environment Variables
2. User Data Files
3. Application Config Files
4. Default Values

## Directory Structure

```
~/.config/jobapp/
├── auth/
│   ├── .env                    # API keys and credentials
│   ├── gspread_credentials.json # Google Sheets API credentials
│   └── linkedin_auth.json      # LinkedIn session state
├── data/
│   ├── resume.yaml            # Master resume content
│   └── experiences.md         # Detailed work history
└── logs/                      # Application logs

./configs/
├── resume.yaml               # Resume optimization settings
├── search.yaml              # Job search configuration
└── prompts/                 # AI prompt templates
```

## Environment Variables

Location: `~/.config/jobapp/auth/.env`

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

## Application Configuration

Location: `configs/default.yaml`

### Google Spreadsheet Settings

```yaml
google_spreadsheet:
  # ID of the Google Sheet used for job tracking
  # Found in the sheet's URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit
  spreadsheet_id: "your-spreadsheet-id"
  
  # Name of the worksheet tab to use
  tab_name: "Data"
```

### Resume Settings

```yaml
settings:
  models:
    # AI model configurations
    resume_optimization:
      provider: "google"
      model: "gemini-2.5-flash"
      temperature: 0.7
      max_tokens: 2048
    # ... other model settings ...
```

## Google Sheets Integration

### Credentials

Location: `~/.config/jobapp/auth/gspread_credentials.json`

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
2. Configuration file (`configs/default.yaml`)
3. Raises ValueError if neither is provided

Example usage in code:

```python
# Using config file values
sheets_manager = SheetsManager()

# Overriding config values
sheets_manager = SheetsManager(
    spreadsheet_id="custom-id",
    tab_name="CustomTab"
)
```

## Resume Configuration

Location: `configs/resume.yaml`

### AI Model Settings

```yaml
settings:
  models:
    # Primary optimization model
    resume_optimization:
      provider: "google"      # AI provider to use
      model: "gemini-2.5-flash"  # Specific model
      temperature: 0.7        # Creativity level
      max_tokens: 2048       # Response length limit
      
    # Validation model
    resume_validation:
      provider: "google"
      model: "gemini-2.0-flash"
      temperature: 0.2
      max_tokens: 1024
      
    # Refinement model
    resume_refinement:
      provider: "google"
      model: "gemini-2.0-flash"
      temperature: 0.5
      max_tokens: 1024
      
    # Formatting model
    resume_formatting:
      provider: "google"
      model: "gemini-1.5-flash"
      temperature: 0.3
      max_tokens: 512
```

### Validation Settings

```yaml
settings:
  validation:
    # Used in: AIResumeOptimizer.__init__() (resume_writer/ai_optimizer.py)
    # Controls whether AI-powered resume validation is performed
    enabled: true
    
    # Used in: ai_optimize_resume() (resume_writer/ai_optimizer.py)
    # Maximum validation/refinement attempts before giving up
    max_retries: 5
    
    # Used in: validate_resume() (resume_writer/ai_optimizer.py)
    # Maximum time per validation cycle
    timeout_seconds: 300
```

### Section Optimization

```yaml
content:
  # Used in: apply_selective_resume_updates() (resume_writer/ai_optimizer.py)
  # Specifies which sections to optimize using path syntax
  sections_to_optimize:
    - "profile.description"        # Dot notation for subsections
    - "skills"                     # Entire section
    - "experience[Company Name]"   # Array item by identifier
    - "education[University]"      # Matches case-insensitive
```

## Search Configuration

Location: `configs/search.yaml`

### Search Settings

```yaml
search:
  # Job search criteria
  criteria:
    max_age_days: 30          # Maximum job posting age
    min_score: 0.8           # Minimum match score
    excluded_companies:      # Companies to skip
      - "Company A"
      - "Company B"
    
  # Browser automation
  browser:
    use_system_chrome: true  # Use system Chrome
    headless: true          # Run in headless mode
    timeout: 30000          # Page load timeout (ms)
    
  # Rate limiting
  limits:
    max_pages: 10           # Maximum search pages
    delay: 2000             # Delay between requests (ms)
    max_retries: 3          # Failed request retries
```

### Scoring Settings

```yaml
scoring:
  weights:
    skills: 0.4             # Weight for skills match
    experience: 0.3         # Weight for experience match
    education: 0.2          # Weight for education match
    location: 0.1           # Weight for location match
    
  thresholds:
    min_skills: 0.6         # Minimum skills match
    min_experience: 0.5     # Minimum experience match
```

## User Data Files

### Master Resume

Location: `~/.config/jobapp/data/resume.yaml`

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

Location: `~/.config/jobapp/data/experiences.md`

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

## Logging Configuration

Location: Configured via environment variables and code

### Log Levels

```python
# Available log levels
LOG_LEVEL = {
    "DEBUG": Detailed debugging information
    "INFO": General operational information
    "WARNING": Warning messages for potential issues
    "ERROR": Error messages for failures
    "CRITICAL": Critical failures requiring immediate attention
}
```

### Log Format

```python
# Standard log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### Log Files

```
~/.config/jobapp/logs/
├── jobapp.log           # Main application log
├── browser.log         # Browser automation log
└── ai_operations.log   # AI interaction log
```

## Configuration Validation

The application validates all configuration files against JSON schemas:

1. **Schema Location**: `jobapp/core/schemas/`
2. **Validation Time**: At application startup
3. **Error Handling**: Clear error messages with specific validation failures

### Example Schema

```json
{
  "type": "object",
  "properties": {
    "settings": {
      "type": "object",
      "properties": {
        "models": {"type": "object"},
        "validation": {"type": "object"}
      }
    },
    "content": {
      "type": "object",
      "properties": {
        "sections_to_optimize": {
          "type": "array",
          "items": {"type": "string"}
        }
      }
    }
  }
}
```

## Development Configuration

For development and testing, you can use:

1. **Local Override Files**:
   - Create `configs/local.yaml` for development-specific settings
   - File is git-ignored

2. **Test Configuration**:
   - Use `configs/test.yaml` for test-specific settings
   - Contains mock credentials and test data

3. **Debug Mode**:
   - Set `DEBUG=true` in `.env`
   - Enables additional logging and validation 