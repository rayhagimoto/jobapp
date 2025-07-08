# AI Resume Optimization Pipeline (Accurate Developer Documentation)

This document describes the actual implementation of the AI-powered resume optimization pipeline in JobApp, as found in:
- [jobapp/resume_writer/pipelines/langgraph_resume_pipeline.py](../jobapp/resume_writer/pipelines/langgraph_resume_pipeline.py)
- [jobapp/resume_writer/batch_optimizer.py](../jobapp/resume_writer/batch_optimizer.py)
- [jobapp/resume_writer/main.py](../jobapp/resume_writer/main.py)
- [jobapp/resume_writer/utils.py](../jobapp/resume_writer/utils.py)
- [jobapp/resume_writer/parser.py](../jobapp/resume_writer/parser.py)
- [jobapp/resume_writer/compiler.py](../jobapp/resume_writer/compiler.py)

## Overview

The resume optimization system is a multi-phase pipeline that takes a base resume, a job description, and a user's experience, and iteratively edits the resume to maximize relevance for a specific job. The pipeline is built using LangGraph and is highly modular, with each phase implemented as a class-based node. The system supports both single-job and batch optimization, as well as direct PDF compilation.

---

## CLI Interface & Usage

The main entrypoint is [main.py](../jobapp/resume_writer/main.py), which supports several modes:

### Modes
- `compile`: Compile a resume YAML to PDF using the LaTeX template.
- `optimize-job`: Optimize a resume for a single job (from file or Google Sheets).
- `optimize-batch`: Optimize resumes for multiple jobs from Google Sheets.

### Example CLI Usage

**Compile PDF:**
```bash
python -m jobapp.resume_writer.main compile --content path/to/resume.yaml --output path/to/resume.pdf
```

**Single Job Optimization:**
```bash
python -m jobapp.resume_writer.main optimize-job --input-resume configs/resume.yaml --experiences configs/experiences.md --job-description-file job.txt --output-dir output/single_job
```
Or, to select a job from Google Sheets by fuzzy query:
```bash
python -m jobapp.resume_writer.main optimize-job --query "Data Scientist Stripe" --output-dir output/single_job
```

**Batch Optimization:**
```bash
python -m jobapp.resume_writer.main optimize-batch \
  --input-resume configs/resume.yaml \
  --experiences configs/experiences.md \
  --output-dir ~/Desktop/optimized_resumes/2024-06-10 \
  --match-score-threshold 70 \
  --max-resumes 5
```

#### Arguments (selected):
- `--input-resume`: Path to the base resume YAML.
- `--experiences`: Path to the experiences Markdown file.
- `--output-dir`: Output directory for results.
- `--job-description-file`: Path to a job description text file (single job mode).
- `--query`: Fuzzy query to select a job from Google Sheets (single job mode).
- `--match-score-threshold`: Minimum match score to include a job (batch mode).
- `--max-resumes`: Maximum number of jobs to process (batch mode).
- `--overwrite-files`: Overwrite existing outputs (default: false).
- `--no-compile-pdf`: Skip PDF compilation (default: compile PDFs).

---

## Pipeline Phases & Node Classes

The pipeline is implemented in [langgraph_resume_pipeline.py](../jobapp/resume_writer/pipelines/langgraph_resume_pipeline.py) using LangGraph's `StateGraph` and a set of class-based nodes:

- **LoadInputsNode**: Validates and loads the input resume, job description, and experiences. Initializes the context dict.
- **PlanningPhaseNode**: Four-step planning process using LLM prompts:
  1. Job Description Analysis
  2. Skill Mapping & Prioritization
  3. Profile Planning (updates `profile.description`)
  4. Bullet Point Planning
- **OptimizationPhaseNode**: Uses the plans to generate targeted resume edits, updating only sections specified in `section_paths`.
- **ValidationPhaseNode**: Runs a validation LLM prompt to check for dishonesty, technical inaccuracies, and over-optimization. If validation fails, triggers a refinement loop.
- **RefinementPhaseNode**: Attempts to refine the resume using LLM feedback if validation fails, up to a configurable max retries.
- **FormattingPhaseNode**: Ensures YAML output is clean and ready for PDF compilation.
- **OutputCompileNode**: Saves the final resume YAML and changelog, and optionally compiles a PDF.

The pipeline is orchestrated by the `ResumeOptimizationPipeline` class, which builds the graph and manages the flow between nodes.

---

## Context Structure

The pipeline expects a context dictionary with the following keys:
```python
context = {
    'input_resume': dict,           # Immutable original resume (parsed from YAML)
    'edited_resume': dict,          # Deepcopy of input_resume, all mutations here
    'job_description': str,
    'experiences': str,
    'section_paths': list,          # YAML paths to optimize, from user config
    'intermediates': dict,          # For plans, LLM outputs, etc.
    'chats': dict,                  # Per-node chat histories
    'config': dict,                 # User config (optional)
}
```

---

## Batch Processing

Batch processing is implemented in [batch_optimizer.py](../jobapp/resume_writer/batch_optimizer.py):
- Jobs are fetched from Google Sheets using `SheetsManager`.
- Jobs are filtered by match score and application status.
- Each job is processed sequentially (not in parallel) using async functions.
- Output directories and filenames are generated using `get_resume_filenames`.
- Each job's output (YAML, PDF, logs) is saved in its own directory.
- Per-job log files are created using `get_logger`.
- Errors in processing a job are caught and logged; failed jobs are skipped.

---

## Configuration

All configuration is managed via [ConfigManager](../../core/config_manager.py):
- Section paths for selective updates are loaded from config or CLI.
- User name, resume paths, and experiences paths are loaded from config or CLI.
- The number of validation/refinement retries is configurable.
- All paths are OS-independent and support environment variable expansion.

---

## Utility Functions

[utils.py](../jobapp/resume_writer/utils.py) provides:
- Keyword analysis and extraction (`parse_keyword_analysis`, `get_unique_keywords`)
- Parsing and formatting of LLM YAML output (`parse_llm_yaml_to_dict`, `clean_yaml_from_llm`)
- Changelog formatting for human review (`format_changelog_to_markdown`)
- Bullet point change parsing (`parse_bullet_changes`)

---

## Logging & Error Handling

- All phases use structured logging via `get_logger`.
- Each job in batch mode has its own log file in the output directory.
- Errors in model calls, validation, or file I/O are caught and logged with details.
- If a job fails, the pipeline returns a detailed error reason and skips to the next job in batch mode.
- The CLI exits with a nonzero code on fatal errors.

---

## Features Not Yet Implemented (Planned)
- Persistent caching of optimizations (no `OptimizationCache` class yet)
- True parallel batch processing (currently async, but jobs are processed sequentially)
- Mock models for offline testing (not present in code)
- Automated metrics aggregation (metrics are logged, not aggregated)
- Some advanced validation/fact-checking features are planned but not yet implemented

---

## File Reference
- [main.py](../jobapp/resume_writer/main.py): CLI entrypoint, mode dispatcher.
- [parser.py](../jobapp/resume_writer/parser.py): CLI argument parsing.
- [batch_optimizer.py](../jobapp/resume_writer/batch_optimizer.py): Batch and single-job optimization logic.
- [pipelines/langgraph_resume_pipeline.py](../jobapp/resume_writer/pipelines/langgraph_resume_pipeline.py): Pipeline node classes and orchestration.
- [utils.py](../jobapp/resume_writer/utils.py): Utility functions for keyword analysis, YAML parsing, changelog formatting, etc.
- [compiler.py](../jobapp/resume_writer/compiler.py): PDF compilation logic.

---

## See Also
- [jobapp/resume_writer/pipelines/langgraph_resume_pipeline.py](../jobapp/resume_writer/pipelines/langgraph_resume_pipeline.py)
- [jobapp/resume_writer/batch_optimizer.py](../jobapp/resume_writer/batch_optimizer.py)
- [jobapp/resume_writer/utils.py](../jobapp/resume_writer/utils.py)
- [jobapp/resume_writer/main.py](../jobapp/resume_writer/main.py)
- [jobapp/resume_writer/parser.py](../jobapp/resume_writer/parser.py)
- [jobapp/resume_writer/compiler.py](../jobapp/resume_writer/compiler.py) 