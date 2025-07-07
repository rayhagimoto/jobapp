# AI Resume Optimization Pipeline

This document describes the actual implementation of the AI-powered resume optimization pipeline in JobApp, as found in:
- [jobapp/resume_writer/pipelines/langgraph_resume_pipeline.py](../jobapp/resume_writer/pipelines/langgraph_resume_pipeline.py)
- [jobapp/resume_writer/batch_optimizer.py](../jobapp/resume_writer/batch_optimizer.py)
- [jobapp/resume_writer/utils.py](../jobapp/resume_writer/utils.py)

## Overview

The resume optimization system is a multi-phase pipeline that takes a base resume, a job description, and a user's experience, and iteratively edits the resume to maximize relevance for a specific job. The pipeline is built using LangGraph and is highly modular, with each phase implemented as a class-based node.

---

## Pipeline Phases (Actual Implementation)

### 1. **Input Loading**
- Validates and loads the input resume (YAML), job description, and experiences.
- Creates a deep copy of the resume for editing (`edited_resume`).
- Initializes intermediates and chat histories for traceability.

### 2. **Planning Phase**
- Four-step planning process using LLM prompts:
  1. **Job Description Analysis**
  2. **Skill Mapping & Prioritization**
  3. **Profile Planning** (updates `profile.description`)
  4. **Bullet Point Planning**
- All intermediate LLM outputs and plans are stored in the context for later use.

### 3. **Optimization Phase**
- Uses the plans from the previous phase to generate targeted resume edits.
- Only updates sections specified in `section_paths` (from config or CLI).
- Applies updates using utility functions for YAML manipulation.

### 4. **Validation Phase**
- Runs a validation LLM prompt to check for dishonesty, technical inaccuracies, and over-optimization.
- If validation fails, triggers a refinement loop (up to a configurable max retries).
- All validation and refinement steps are logged.

### 5. **Refinement & Formatting**
- If validation fails, the pipeline attempts to refine the resume using LLM feedback.
- Formatting phase ensures YAML output is clean and ready for PDF compilation.

### 6. **Output Compilation**
- Final resume YAML and changelog are saved.
- Optionally compiles a PDF using the external resume template repo.

---

## Selective Section Updates

- The pipeline supports path-based targeting of resume sections for optimization (see `section_paths`).
- Example config:

```yaml
section_paths:
  - "profile.description"
  - "skills"
  - "experience[Company Name]"
```

---

## Keyword & Experience Matching

- Keyword analysis and experience matching are performed using utility functions in [utils.py](../jobapp/resume_writer/utils.py).
- The system extracts keywords from the job description and matches them to resume content.
- Experience matching is used to prioritize which experiences to highlight or rewrite.

---

## Error Handling & Logging

- All phases use structured logging (see [logger.py](../jobapp/core/logger.py)).
- Errors in model calls, validation, or file I/O are caught and logged with details.
- If a job fails, the pipeline returns a detailed error reason and skips to the next job in batch mode.

---

## Batch Processing

- Batch optimization is implemented in [batch_optimizer.py](../jobapp/resume_writer/batch_optimizer.py).
- Jobs are filtered from Google Sheets based on match score and application status.
- Each job is processed in its own output directory, with logs and outputs saved per job.
- Batch processing supports skipping existing outputs, max resume limits, and PDF compilation.

**CLI Example:**

```bash
python -m jobapp.resume_writer.batch_optimizer \
  --input-resume configs/resume.yaml \
  --experiences configs/experiences.md \
  --output-dir ~/Desktop/optimized_resumes/2024-06-10 \
  --match-score-threshold 70 \
  --max-resumes 5 \
  --your-name "Ray Hagimoto"
```

---

## Validation & Refinement

- Validation is performed by a dedicated node in the pipeline, using LLM prompts to detect exaggeration, fabrication, or technical errors.
- If validation fails, the pipeline attempts up to N refinements before reverting to the original content.
- All validation and refinement steps are tracked in the context and logs.

---

## Utility Functions

- [utils.py](../jobapp/resume_writer/utils.py) provides:
  - Keyword analysis and extraction
  - Parsing and formatting of LLM YAML output
  - Changelog formatting for human review
  - Bullet point change parsing

---

## Monitoring & Metrics

- Each job's optimization process is logged with input/output lengths, validation scores, and timing.
- Logs are saved per job in the output directory for easy debugging.

---

## Features Not Yet Implemented (Planned)

- Persistent caching of optimizations (no `OptimizationCache` class yet)
- True parallel batch processing (currently uses asyncio.gather, but not full parallelism)
- Mock models for offline testing (not present in code)
- Automated metrics aggregation (metrics are logged, not aggregated)
- Some advanced validation/fact-checking features are planned but not yet implemented

---

## See Also
- [jobapp/resume_writer/pipelines/langgraph_resume_pipeline.py](../jobapp/resume_writer/pipelines/langgraph_resume_pipeline.py)
- [jobapp/resume_writer/batch_optimizer.py](../jobapp/resume_writer/batch_optimizer.py)
- [jobapp/resume_writer/utils.py](../jobapp/resume_writer/utils.py) 