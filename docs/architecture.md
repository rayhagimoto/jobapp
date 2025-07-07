# JobApp Architecture Guide

This document provides a detailed technical overview of JobApp's architecture, components, and design principles.

## System Overview

JobApp is built as a modular Python application with three primary subsystems:

1. Job Search Engine
2. Resume Optimizer
3. Core Infrastructure

Each subsystem is designed to be independently maintainable while sharing common infrastructure components.

## Component Architecture

### 1. Job Search Engine (`jobapp/search/`)

The search engine is responsible for automated job discovery and evaluation.

#### Key Components:

- **`linkedin_scraper.py`**
  - Manages LinkedIn interaction using Playwright
  - Handles session management and authentication
  - Implements retry logic and error handling
  - Extracts structured job data from listings

- **`browser_agent.py`**
  - Provides browser automation abstraction
  - Supports both Playwright-managed and system Chrome
  - Implements connection pooling and resource cleanup
  - Handles cross-platform browser detection

- **`job_scorer.py`**
  - Evaluates job descriptions against user profile
  - Implements keyword matching and semantic scoring
  - Calculates match percentages for skills and requirements
  - Provides detailed scoring breakdown

- **`main.py`**
  - CLI interface for search operations
  - Coordinates component interactions
  - Manages output formatting and logging
  - Handles Google Sheets integration

### 2. Resume Optimizer (`jobapp/resume_writer/`)

The optimizer implements a sophisticated AI pipeline for resume customization.

#### Components:

- **`ai_optimizer.py`**
  - Implements the core AI optimization pipeline
  - Manages model interactions and prompt engineering
  - Handles selective section updates
  - Implements validation and refinement loops

- **`resume_generator.py`**
  - Manages resume YAML parsing and generation
  - Handles LaTeX template integration
  - Implements PDF compilation
  - Manages output file organization

- **`filename_formatter.py`**
  - Implements consistent file naming conventions
  - Handles date stamping and versioning
  - Sanitizes filenames for cross-platform compatibility

- **`batch_optimizer.py`**
  - Implements batch processing logic
  - Manages parallel optimization tasks
  - Handles error recovery and resumption
  - Implements progress tracking

#### AI Pipeline Stages:

1. **Job Analysis**
   - Input: Raw job description
   - Process: Extract key requirements and priorities
   - Output: Structured job requirements

2. **Content Planning**
   - Input: Job requirements + User experiences
   - Process: Strategic keyword placement planning
   - Output: Section-by-section optimization plan

3. **Content Generation**
   - Input: Optimization plan + Original resume
   - Process: AI-powered content rewriting
   - Output: Optimized resume sections

4. **Validation**
   - Input: New resume + Original experiences
   - Process: Truth verification and scoring
   - Output: Validation report or refinement needs

5. **Refinement (if needed)**
   - Input: Validation feedback
   - Process: Targeted content adjustment
   - Output: Revised resume sections

6. **Formatting**
   - Input: Final content
   - Process: Style consistency check
   - Output: Production-ready resume

### 3. Core Infrastructure (`jobapp/core/`)

Provides shared services and utilities used across the application.

#### Components:

- **`config_manager.py`**
  - Implements hierarchical configuration
  - Manages environment variable integration
  - Handles path resolution and validation
  - Implements configuration schema validation

- **`sheets_manager.py`**
  - Manages Google Sheets integration
  - Implements batch update operations
  - Handles authentication and credential management
  - Provides error handling and retry logic

- **`logger.py`**
  - Implements structured logging
  - Manages log rotation and cleanup
  - Provides context-aware logging helpers
  - Implements debug mode handling

- **`llm_interface.py`**
  - Abstracts LLM provider interactions
  - Manages API key handling
  - Implements rate limiting and quotas
  - Provides fallback handling

## Data Flow

1. **Job Search Flow**
   ```mermaid
   graph TD
     A[LinkedIn Search] --> B[Browser Agent]
     B --> C[Job Extraction]
     C --> D[Job Scorer]
     D --> E[Sheets Manager]
   ```

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

## Configuration Architecture

The system uses a hierarchical configuration system:

1. **Environment Layer**
   - Location: `~/.config/jobapp/auth/.env`
   - Purpose: Sensitive credentials
   - Priority: Highest (overrides all)

2. **User Data Layer**
   - Location: `~/.config/jobapp/data/`
   - Purpose: Personal content
   - Persistence: Long-term

3. **Application Layer**
   - Location: `configs/*.yaml`
   - Purpose: Application settings
   - Scope: Component-specific

4. **Default Layer**
   - Location: Embedded in code
   - Purpose: Fallback values
   - Priority: Lowest

## Error Handling

The application implements a comprehensive error handling strategy:

1. **Recoverable Errors**
   - Network timeouts
   - Rate limiting
   - Temporary auth failures
   - Implementation: Retry with backoff

2. **User Errors**
   - Invalid configuration
   - Missing credentials
   - Implementation: Clear error messages

3. **System Errors**
   - Browser crashes
   - PDF compilation failures
   - Implementation: Graceful degradation

4. **Data Errors**
   - Invalid resume format
   - Corrupt sheets data
   - Implementation: Validation and repair

## Performance Considerations

1. **Browser Automation**
   - Connection pooling
   - Resource cleanup
   - Memory management
   - Session persistence

2. **AI Operations**
   - Prompt optimization
   - Token management
   - Parallel processing
   - Result caching

3. **Batch Processing**
   - Progress tracking
   - Checkpoint saving
   - Error recovery
   - Resource limits

## Security Architecture

1. **Credential Management**
   - Secure storage location
   - Environment isolation
   - Access validation
   - Key rotation support

2. **Session Management**
   - Secure storage
   - Automatic renewal
   - Validation checks
   - Cleanup procedures

3. **Data Protection**
   - Local file security
   - Transport encryption
   - API key handling
   - Output sanitization

## Testing Architecture

1. **Unit Tests**
   - Component isolation
   - Mock integrations
   - Error scenarios
   - Edge cases

2. **Integration Tests**
   - Component interaction
   - Real API calls
   - Browser automation
   - PDF generation

3. **System Tests**
   - End-to-end workflows
   - Performance metrics
   - Resource usage
   - Error recovery

## Development Guidelines

1. **Code Organization**
   - Modular design
   - Clear separation
   - Consistent structure
   - Documentation

2. **Error Handling**
   - Comprehensive coverage
   - Clear messages
   - Recovery paths
   - Logging

3. **Configuration**
   - Schema validation
   - Default values
   - Override handling
   - Documentation

4. **Testing**
   - Coverage targets
   - Mock guidelines
   - Scenario coverage
   - Performance benchmarks 