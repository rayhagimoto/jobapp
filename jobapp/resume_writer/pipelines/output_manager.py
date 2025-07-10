"""
OutputManager for writing resume pipeline outputs to disk.
Handles YAML, job description, keywords, and PDF (stub) outputs.
Follows legacy filename conventions and robust error handling.
"""

import os
import logging
from pathlib import Path
from jobapp.resume_writer.yaml_processing_utils import format_yaml_with_quotes
from jobapp.utils.filename import get_resume_filenames
from jobapp.resume_writer.compiler import ResumeCompiler

class OutputManager:
    def __init__(self, logger=None, config=None):
        self.logger = logger or logging.getLogger(__name__)
        self.compiler = ResumeCompiler()
        self.config = config

    def write_resume_yaml(self, edited_resume: dict, yaml_path: Path) -> Path:
        """
        Write the edited resume YAML to disk at the given path. Returns the file path.
        """
        resume_yaml_str = format_yaml_with_quotes(edited_resume)
        yaml_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(yaml_path, 'w', encoding='utf-8') as f:
                f.write(resume_yaml_str)
            self.logger.info(f"[OutputManager] Edited resume YAML written to {yaml_path}")
        except Exception as e:
            self.logger.error(f"[OutputManager] Failed to write edited resume YAML: {e}")
            raise
        return yaml_path

    def write_job_description(self, job_description: str, job_dir: Path) -> Path:
        """
        Write the job description to disk. Returns the file path.
        """
        jd_path = job_dir / 'job_description.md'
        try:
            with open(jd_path, 'w', encoding='utf-8') as f:
                f.write(job_description)
            self.logger.info(f"[OutputManager] Job description written to {jd_path}")
        except Exception as e:
            self.logger.error(f"[OutputManager] Failed to write job description: {e}")
            raise
        return jd_path

    def write_keywords_yaml(self, keywords_yaml: str, job_dir: Path) -> Path:
        """
        Write the keywords YAML to disk. Returns the file path.
        """
        keywords_path = job_dir / 'keywords.md'
        try:
            with open(keywords_path, 'w', encoding='utf-8') as f:
                f.write(keywords_yaml)
            self.logger.info(f"[OutputManager] Keywords YAML written to {keywords_path}")
        except Exception as e:
            self.logger.error(f"[OutputManager] Failed to write keywords YAML: {e}")
            raise
        return keywords_path

    def compile_pdf(self, yaml_path: Path, pdf_path: Path, build_dir=None):
        """
        Compile the PDF using ResumeCompiler, passing build_dir if provided.
        """
        success = self.compiler.compile(content_file=yaml_path, output_path=pdf_path, build_dir=build_dir)
        if success:
            self.logger.info(f"[OutputManager] PDF compiled: {pdf_path}")
        else:
            self.logger.error(f"[OutputManager] PDF compilation failed for {yaml_path}")
        return success

    def write_all_outputs(self, context: dict, job_info: dict, your_name: str, base_output_dir: Path, compile_pdf: bool = True):
        """
        Write all outputs (YAML, job description, keywords, PDF) using context dict and job info.
        Output paths and filenames match the legacy conventions.
        Args:
            context: Pipeline context dict (must contain 'edited_resume', 'job_description', 'intermediates.keywords_output').
            job_info: Dict with keys 'JobTitle', 'Company', 'Location', 'MatchScore'.
            your_name: User's name (for filename generation).
            base_output_dir: Base output directory (Path).
            compile_pdf: Whether to compile the PDF (default True).
        Returns:
            Dict of written file paths.
        """
        # Generate filenames and directories using legacy logic
        filenames = get_resume_filenames(
            your_name=your_name,
            job_title=job_info.get("JobTitle", "Unknown Job"),
            company=job_info.get("Company", "Unknown Company"),
            location=job_info.get("Location", "Remote"),
            match_score=job_info.get("MatchScore", 0)
        )
        job_dir = base_output_dir / filenames["dir"]
        job_dir.mkdir(parents=True, exist_ok=True)
        yaml_path = base_output_dir / filenames["yaml"]
        pdf_path = base_output_dir / filenames["pdf"]

        written = {}
        # Write edited resume YAML
        try:
            edited_resume = context['edited_resume']
        except KeyError:
            self.logger.error("[OutputManager] Missing 'edited_resume' in context.")
            raise KeyError("Missing 'edited_resume' in context for YAML output.")
        self.write_resume_yaml(edited_resume, yaml_path)
        written['edited_resume_yaml'] = yaml_path
        # Write job description
        try:
            job_description = context['job_description']
        except KeyError:
            self.logger.error("[OutputManager] Missing 'job_description' in context.")
            raise KeyError("Missing 'job_description' in context for job description output.")
        self.write_job_description(job_description, job_dir)
        written['job_description'] = job_dir / 'job_description.md'
        # Write keywords YAML
        try:
            keywords_yaml = context['intermediates']['keywords_output']
        except KeyError:
            self.logger.error("[OutputManager] Missing 'intermediates.keywords_output' in context.")
            raise KeyError("Missing 'intermediates.keywords_output' in context for keywords output.")
        self.write_keywords_yaml(keywords_yaml, job_dir)
        written['keywords'] = job_dir / 'keywords.md'
        # Get cache dir from config if available
        cache_dir = self.config.get_cache_path() if self.config else './build'
        cache_dir = Path(cache_dir)  # Ensure cache_dir is always a Path
        # Use a per-job build dir
        build_dir = cache_dir / job_dir.name
        build_dir.mkdir(parents=True, exist_ok=True)
        # Compile PDF if requested
        # When compiling PDF, always use per-job build_dir
        # If batch compilation is used, build a list of (yaml_path, pdf_path, build_dir) tuples
        # For single job, just call ResumeCompiler.compile with build_dir
        # (Assume this file only handles single-job output, but if batch, update accordingly)
        written['edited_resume_pdf'] = pdf_path  # Always set, even before compilation
        if compile_pdf:
            pdf_success = self.compiler.compile(
                content_file=written["edited_resume_yaml"],
                output_path=pdf_path,
                build_dir=build_dir
            )
            if pdf_success:
                self.logger.info(f"[OutputManager] PDF compiled: {pdf_path}")
            else:
                self.logger.error(f"[OutputManager] PDF compilation failed for {written['edited_resume_yaml']}")
        else:
            self.logger.info("[OutputManager] PDF compilation skipped (compile_pdf=False)")
        return written
