import os
from pathlib import Path
from jobapp.core.config_manager import ConfigManager
from typing import Dict, Any, Optional
from jobapp.resume_writer.yaml_processing_utils import format_yaml_with_quotes, extract_by_path_advanced, strip_yaml_code_block
from jobapp.utils.filename import get_resume_filenames
from jobapp.resume_writer.compiler import compile_resume
import logging
import yaml

class ResumeOutputManager:
    def __init__(self, base_output_dir: Path = Path("."), config_manager: ConfigManager = None):
        self.base_output_dir = Path(base_output_dir)
        self.config_manager = config_manager or ConfigManager()
        self.logger = logging.getLogger(__name__)

    def save_formatted_resume_yaml(self, path: Path, formatted_resume: dict):
        """
        Save the formatted_resume dict as a single-quoted YAML string using the new two-step approach:
        - Serialize 'sections' with normal yaml.dump (no escaping)
        - Serialize the rest with format_yaml_with_quotes (exclude_sections=True)
        - Combine and write
        Strictly enforces that formatted_resume is a dict.
        """
        if not isinstance(formatted_resume, dict):
            raise TypeError("formatted_resume must be a dict before formatting as YAML")
        path.parent.mkdir(parents=True, exist_ok=True)
        # Separate out sections
        sections = {'sections': formatted_resume['sections']} if 'sections' in formatted_resume else {}
        rest = {k: v for k, v in formatted_resume.items() if k != 'sections'}
        # Serialize
        sections_yaml = yaml.dump(sections, default_flow_style=False, allow_unicode=True, sort_keys=False) if sections else ''
        rest_yaml = format_yaml_with_quotes(rest, exclude_sections=True)
        # Combine
        yaml_str = sections_yaml.strip() + '\n' + rest_yaml.strip() if sections else rest_yaml.strip()
        print(f"ResumeOutputManager: formatted resume = {formatted_resume}")
        print(yaml_str)
        with open(path, "w", encoding="utf-8") as f:
            f.write(yaml_str)

    def save_all_outputs(
        self,
        pipeline_output: dict,  # {"edited_resume": ..., "context": ..., "formatted_resume": ...}
        job_info: dict,         # {"name": ..., "job_title": ..., "company": ..., "location": ..., "match_score": ...}
        output_format: str = "full",
        compile_pdf: bool = True
    ) -> Dict[str, Path]:
        """
        Main entry point. Saves required outputs and returns a dict of file paths.
        output_format:
            - 'full': all outputs (default)
            - 'concise': only yaml, keywords, changelog
            - 'yaml_only': only yaml
        compile_pdf:
            - If True (default), compile PDF after writing YAML
            - If False, skip PDF compilation (for --no-compile-pdf)
        """
        context = pipeline_output["context"]
        edited_resume = pipeline_output["edited_resume"]
        filenames = get_resume_filenames(
            job_info["name"], job_info["job_title"], job_info["company"], job_info["location"], job_info.get("match_score")
        )
        job_dir = self.base_output_dir / filenames["dir"]
        job_dir.mkdir(parents=True, exist_ok=True)
        paths = {
            "job_description": job_dir / "job_description.md",
            "edited_resume_yaml": self.base_output_dir / filenames["yaml"],
            "edited_resume_pdf": self.base_output_dir / filenames["pdf"],
            "keywords": job_dir / "keywords.md",
            "planning_transcript": job_dir / "planning_transcript.md",
            "optimization_transcript": job_dir / "optimization_transcript.md",
            "changelog": job_dir / "changelog.md",
        }
        written = {}
        cache_dir = self.config_manager.get_cache_path()
        if output_format == "yaml_only":
            self._write_yaml(paths["edited_resume_yaml"], edited_resume)
            written["edited_resume_yaml"] = paths["edited_resume_yaml"]
            # PDF (optional)
            if compile_pdf:
                success = compile_resume(paths["edited_resume_yaml"], paths["edited_resume_pdf"], build_dir=cache_dir)
                if success:
                    self.logger.info(f"PDF compiled: {paths['edited_resume_pdf']}")
                    written["edited_resume_pdf"] = paths["edited_resume_pdf"]
                else:
                    self.logger.error(f"PDF compilation failed for {paths['edited_resume_yaml']}")
            return written
        if output_format == "concise":
            self._write_yaml(paths["edited_resume_yaml"], edited_resume)
            keywords_raw = context.get("intermediates", {}).get("jd_analysis_output", "")
            keywords_md = strip_yaml_code_block(keywords_raw)
            self._write_text(paths["keywords"], keywords_md)
            changelog_md = self._make_changelog(context)
            self._write_text(paths["changelog"], changelog_md)
            written["edited_resume_yaml"] = paths["edited_resume_yaml"]
            written["keywords"] = paths["keywords"]
            written["changelog"] = paths["changelog"]
            # PDF (optional)
            if compile_pdf:
                success = compile_resume(paths["edited_resume_yaml"], paths["edited_resume_pdf"], build_dir=cache_dir)
                if success:
                    self.logger.info(f"PDF compiled: {paths['edited_resume_pdf']}")
                    written["edited_resume_pdf"] = paths["edited_resume_pdf"]
                else:
                    self.logger.error(f"PDF compilation failed for {paths['edited_resume_yaml']}")
            return written
        # full (default): all outputs
        self._write_text(paths["job_description"], context.get("job_description", ""))
        # Use formatted_resume if available, else fallback to edited_resume
        formatted_resume = pipeline_output.get("formatted_resume")
        if formatted_resume is not None:
            print("Saving formatted resume")
            print(formatted_resume)
            self._write_yaml(paths["edited_resume_yaml"], formatted_resume)
        else:
            print("Saving edited_resume")
            print(f"{edited_resume}")
            self._write_yaml(paths["edited_resume_yaml"], edited_resume)
        keywords_raw = context.get("intermediates", {}).get("jd_analysis_output", "")
        keywords_md = strip_yaml_code_block(keywords_raw)
        self._write_text(paths["keywords"], keywords_md)
        planning_steps = [
            ("jd_analysis", "EditorPrompt1"),
            ("skill_mapping", "EditorPrompt2"),
            ("profile_planning", "EditorPrompt3"),
            ("bullet_points", "EditorPrompt4"),
        ]
        planning_md = self._make_transcript(context, planning_steps)
        self._write_text(paths["planning_transcript"], planning_md)
        optimization_steps = [
            ("optimizer_prompt", "OptimizerPrompt"),
            ("validation_prompt", "ValidationPrompt"),
            ("feedback_prompt", "FeedbackPrompt"),
        ]
        optimization_md = self._make_transcript(context, optimization_steps)
        self._write_text(paths["optimization_transcript"], optimization_md)
        changelog_md = self._make_changelog(context)
        self._write_text(paths["changelog"], changelog_md)
        written = paths.copy()
        # PDF (optional)
        if compile_pdf:
            success = compile_resume(paths["edited_resume_yaml"], paths["edited_resume_pdf"], build_dir=cache_dir)
            if success:
                self.logger.info(f"PDF compiled: {paths['edited_resume_pdf']}")
            else:
                self.logger.error(f"PDF compilation failed for {paths['edited_resume_yaml']}")
        # If you want to save the formatted_resume as a YAML file, do it here:
        formatted_resume = pipeline_output.get("formatted_resume")
        if formatted_resume is not None:
            formatted_resume_path = job_dir / "formatted_resume.yaml"
            self.save_formatted_resume_yaml(formatted_resume_path, formatted_resume)
            written["formatted_resume_yaml"] = formatted_resume_path
        return written

    def _write_text(self, path: Path, content: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content or "")

    def _write_yaml(self, path: Path, data: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        # Separate out sections
        sections = {'sections': data['sections']} if 'sections' in data else {}
        rest = {k: v for k, v in data.items() if k != 'sections'}
        # Serialize
        sections_yaml = yaml.dump(sections, default_flow_style=False, allow_unicode=True, sort_keys=False) if sections else ''
        rest_yaml = format_yaml_with_quotes(rest, exclude_sections=True)
        # Combine
        yaml_str = sections_yaml.strip() + '\n' + rest_yaml.strip() if sections else rest_yaml.strip()
        with open(path, "w", encoding="utf-8") as f:
            f.write(yaml_str)

    def _make_transcript(self, context: dict, steps: list) -> str:
        """
        Format transcript for a sequence of steps.
        Each step: (prompt_key, prompt_label)
        Uses intermediates: {prompt_key}_inputs and {prompt_key}_output
        """
        intermediates = context.get("intermediates", {})
        lines = []
        for prompt_key, prompt_label in steps:
            human = intermediates.get(f"{prompt_key}_inputs")
            ai = intermediates.get(f"{prompt_key}_output")
            if human is not None:
                lines.append(f"-- HUMAN MESSAGE ({prompt_label}) --\n{human}\n")
            if ai is not None:
                lines.append(f"-- AI MESSAGE ({prompt_label}) --\n{ai}\n")
        return "\n".join(lines)

    def _make_changelog(self, context: dict) -> str:
        section_paths = context.get('section_paths')
        if not section_paths:
            print(f"[DEBUG] section_paths not in context, getting from config_manager")
            section_paths = self.config_manager.get_section_paths()
        versions = context.get('intermediates', {}).get('edited_resume_versions', [])
        print(f"[DEBUG] section_paths = {section_paths}")
        if not section_paths or not versions or len(versions) < 1:
            print("[DEBUG] Not enough section_paths or versions for changelog.")
            return 'No net updates.'
        lines = []
        for section in section_paths:
            print(f"[DEBUG] Changelog for section: {section}")
            vals = [extract_by_path_advanced(v, section) for v in versions]
            for i, val in enumerate(vals):
                print(f"  [DEBUG] Version {i}: {val}")
            prev = vals[0]
            change_count = 1
            for i in range(1, len(vals)):
                if vals[i] != prev:
                    lines.append(f"# {section}\n**Change {change_count}**\nIN: {prev}\nOUT: {vals[i]}\n")
                    change_count += 1
                prev = vals[i]
        return '\n'.join(lines)
