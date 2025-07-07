# JobApp Architecture Guide

This document provides a detailed technical overview of JobApp's architecture, components, and design principles, updated to match the current codebase. All source file references use local links for easy navigation.

## System Overview

JobApp is a modular Python application with three primary subsystems:

1. Job Search Engine ([jobapp/search/](../jobapp/search/))
2. Resume Optimizer ([jobapp/resume_writer/](../jobapp/resume_writer/))
3. Core Infrastructure ([jobapp/core/](../jobapp/core/))

Each subsystem is independently maintainable but shares common infrastructure components.

## Component Architecture

### 1. Job Search Engine ([jobapp/search/](../jobapp/search/))

Responsible for automated job discovery, scraping, and match scoring.

#### Key Components:

- **[linkedin_scraper.py](../jobapp/search/linkedin_scraper.py)**
  - Manages LinkedIn interaction using Playwright and Patchright
  - Handles session management, authentication, and browser modes (stealth, system Chrome, native Chromium)
  - Implements retry logic, error handling, and human-like interaction
  - Extracts structured job data from listings
  - Integrates Google Sheets for job tracking

- **[main.py](../jobapp/search/main.py)**
  - CLI interface for search operations
  - Subcommands: `search` (default), `match-score`
  - Coordinates scraping and match score calculation
  - Manages output formatting and logging

- **[match_score_calculator.py](../jobapp/search/match_score_calculator.py)**
  - Calculates match scores for jobs using LLMs
  - Used by the `match-score` CLI subcommand

- **Note:**
  - There is no `browser_agent.py` file; browser automation is handled within [linkedin_scraper.py](../jobapp/search/linkedin_scraper.py) and [jobapp/core/chrome_manager.py](../jobapp/core/chrome_manager.py).
  - There is no `job_scorer.py`; match scoring is implemented in [match_score_calculator.py](../jobapp/search/match_score_calculator.py).

### 2. Resume Optimizer ([jobapp/resume_writer/](../jobapp/resume_writer/))

Implements the AI pipeline for resume customization and batch optimization.

#### Key Components:

- **[main.py](../jobapp/resume_writer/main.py)**
  - CLI for resume optimization, batch/single job, and PDF compilation
  - Argument parsing and orchestration

- **[batch_optimizer.py](../jobapp/resume_writer/batch_optimizer.py)**
  - Batch processing logic for resume optimization
  - Manages parallel optimization, error handling, and progress tracking

- **[pipelines/langgraph_resume_pipeline.py](../jobapp/resume_writer/pipelines/langgraph_resume_pipeline.py)**
  - Implements the core AI optimization pipeline (content planning, generation, validation, refinement)

- **[compiler.py](../jobapp/resume_writer/compiler.py)**
  - Handles LaTeX template integration and PDF compilation

- **[utils/filename.py](../jobapp/utils/filename.py)**
  - Implements consistent file naming conventions, date stamping, and sanitization

- **Note:**
  - There is no `ai_optimizer.py` or `resume_generator.py`; their described functionality is distributed across the above files.
  - `filename_formatter.py` is implemented as [utils/filename.py](../jobapp/utils/filename.py).

#### AI Pipeline Stages (Distributed Implementation):
1. **Job Analysis**: Extracted in [langgraph_resume_pipeline.py](../jobapp/resume_writer/pipelines/langgraph_resume_pipeline.py)
2. **Content Planning**: [langgraph_resume_pipeline.py](../jobapp/resume_writer/pipelines/langgraph_resume_pipeline.py)
3. **Content Generation**: [langgraph_resume_pipeline.py](../jobapp/resume_writer/pipelines/langgraph_resume_pipeline.py)
4. **Validation**: [langgraph_resume_pipeline.py](../jobapp/resume_writer/pipelines/langgraph_resume_pipeline.py)
5. **Refinement**: [langgraph_resume_pipeline.py](../jobapp/resume_writer/pipelines/langgraph_resume_pipeline.py)
6. **Formatting**: [compiler.py](../jobapp/resume_writer/compiler.py), [utils/filename.py](../jobapp/utils/filename.py)

### 3. Core Infrastructure ([jobapp/core/](../jobapp/core/))

Provides shared services and utilities used across the application.

#### Components:

- **[config_manager.py](../jobapp/core/config_manager.py)**
  - Hierarchical configuration (env vars, user config, project config, defaults)
  - Path resolution and validation
  - Module detection and config merging

- **[sheets_manager.py](../jobapp/core/sheets_manager.py)**
  - Google Sheets integration for job tracking
  - Batch update operations, authentication, error handling

- **[logger.py](../jobapp/core/logger.py)**
  - Structured logging, log rotation, context-aware helpers

- **[llm_interface.py](../jobapp/core/llm_interface.py)**
  - LLM provider abstraction, API key management, rate limiting, fallback handling

- **[api_key_manager.py](../jobapp/core/api_key_manager.py)**
  - API key rotation and quota tracking for rate-limited services

- **[chrome_manager.py](../jobapp/core/chrome_manager.py)**
  - Cross-platform Chrome browser automation for scraping

## Data Flow

1. **Job Search Flow**
   ```mermaid
   graph TD
     A[LinkedIn Search] --> B[Browser Automation]
     B --> C[Job Extraction]
     C --> D[Match Score Calculation]
     D --> E[Sheets Manager]
   ```
   - Browser automation is handled by [linkedin_scraper.py](../jobapp/search/linkedin_scraper.py) and [chrome_manager.py](../jobapp/core/chrome_manager.py).
   - Match scoring is handled by [match_score_calculator.py](../jobapp/search/match_score_calculator.py).

2. **Resume Optimization Flow**
   ```mermaid
   graph TD
     A[Job Description] --> B[AI Analysis]
     B --> C[Content Planning]
     C --> D[Generation]
     D --> E[Validation]
     E -->|Pass| F[Formatting]
     E -->|Fail| G[Refinement]
     G --> D
   ```
   - All pipeline stages are implemented in [langgraph_resume_pipeline.py](../jobapp/resume_writer/pipelines/langgraph_resume_pipeline.py) and orchestrated by [batch_optimizer.py](../jobapp/resume_writer/batch_optimizer.py).

## Configuration Architecture

The system uses a hierarchical configuration system:

1. **Environment Layer**
   - Location: `~/.config/jobapp/secrets/.env`
   - Purpose: Sensitive credentials
   - Priority: Highest (overrides all)

2. **User Data Layer**
   - Location: `~/.config/jobapp/data/`
   - Purpose: Personal content
   - Persistence: Long-term

3. **User Config Layer**
   - Location: `~/.config/jobapp/config/*.yaml`
   - Purpose: User-specific application settings
   - Scope: Component-specific

4. **Project Config Layer**
   - Location: `configs/*.yaml`
   - Purpose: Project-level settings
   - Scope: Fallback if user config is missing

5. **Default Layer**
   - Location: Embedded in code
   - Purpose: Fallback values
   - Priority: Lowest

## Error Handling, Performance, Security, and Testing

- Error handling, performance, security, and testing strategies are implemented as described, but details may be distributed across multiple files.
- See [config_manager.py](../jobapp/core/config_manager.py), [llm_interface.py](../jobapp/core/llm_interface.py), [api_key_manager.py](../jobapp/core/api_key_manager.py), and [logger.py](../jobapp/core/logger.py) for implementation details.

## Development Guidelines

- Code is organized modularly, with clear separation of concerns.
- Configuration, error handling, and logging follow best practices and are centralized in core modules.
- Testing and validation are ongoing; see the `tests/` directory (if present) and docstrings in each module for usage examples.

---

**For further details, see the source files linked above.** 