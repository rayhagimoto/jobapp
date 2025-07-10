"""
Resume compilation module for converting YAML resumes to PDF.
This module acts as a wrapper around the standalone `compile_resume.py` script.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, Union, List
import asyncio

from ..core.logger import get_logger

logger = get_logger(__name__)

class ResumeCompiler:
    """
    Handles compilation of YAML resumes to PDF by calling the compiler script.
    """
    
    def __init__(self):
        """
        Initialize the compiler.
        """
        self.compiler_script_path = (
            Path(__file__).parent / "resume_template" / "compile_resume.py"
        ).resolve()

    def compile(self, content_file: Union[str, Path], output_path: Optional[Union[str, Path]] = None, build_dir: Optional[Union[str, Path]] = None) -> bool:
        """
        Compile a YAML resume to PDF by calling the compiler script.
        Args:
            content_file: Path to the YAML content file.
            output_path: Optional custom output path for the PDF. If not provided,
                         it will be created alongside the content_file with a .pdf extension.
            build_dir: Directory for build artifacts. If None, defaults to './build'.
        Returns:
            bool: True if compilation was successful.
        Raises:
            RuntimeError: If PDF compilation fails for any reason.
        """
        try:
            content_file = Path(content_file).resolve()
            if not content_file.exists():
                logger.error(f"YAML content file not found for compilation: {content_file}")
                raise RuntimeError(f"YAML content file not found: {content_file}")

            if output_path:
                output_path = Path(output_path).resolve()
            else:
                output_path = content_file.with_suffix('.pdf')

            if not self.compiler_script_path.exists():
                logger.error(f"Compiler script not found at: {self.compiler_script_path}")
                raise RuntimeError(f"Compiler script not found: {self.compiler_script_path}")

            if build_dir is None:
                build_dir = Path('./build').resolve()
            else:
                build_dir = Path(build_dir).resolve()

            cmd = [
                "python3",
                str(self.compiler_script_path),
                "--content", str(content_file),
                "--output", str(output_path),
                "--build", str(build_dir)
            ]

            logger.debug(f"Executing resume compiler: {' '.join(map(str, cmd))} (build_dir={build_dir})")

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=2  # Timeout after 2 seconds
                )
            except subprocess.TimeoutExpired:
                logger.error(f"PDF compilation timed out for {content_file} (timeout=2s)")
                print(f"[PDF Compiler] TIMEOUT: PDF compilation timed out for {content_file} (timeout=2s)")
                raise RuntimeError(f"PDF compilation timed out for {content_file} (timeout=2s)")

            if result.stdout:
                logger.debug(f"Compiler STDOUT: {result.stdout.strip()}")
            if result.stderr:
                logger.debug(f"Compiler STDERR: {result.stderr.strip()}")

            if result.returncode != 0:
                logger.error(f"PDF compilation script failed for {content_file}.")
                logger.error(f"Compiler STDOUT: {result.stdout.strip()}")
                logger.error(f"Compiler STDERR: {result.stderr.strip()}")
                print(f"[PDF Compiler] ERROR: PDF compilation failed for {content_file}")
                print(f"[PDF Compiler] STDOUT:\n{result.stdout.strip()}")
                print(f"[PDF Compiler] STDERR:\n{result.stderr.strip()}")
                raise RuntimeError(f"PDF compilation failed for {content_file}. See logs above for details.")

            # Check if PDF was actually generated
            if not output_path.exists():
                logger.error(f"PDF was not generated for {content_file} (expected at {output_path})")
                print(f"[PDF Compiler] ERROR: PDF was not generated for {content_file} (expected at {output_path})")
                raise RuntimeError(f"PDF was not generated for {content_file} (expected at {output_path})")

            logger.info(f"Successfully compiled {content_file.name} to {output_path.name}")
            return True

        except Exception as e:
            logger.error(f"An unexpected error occurred calling the resume compiler: {e}", exc_info=True)
            print(f"[PDF Compiler] UNEXPECTED ERROR: {e}")
            raise RuntimeError(f"PDF compilation failed for {content_file}: {e}")

def compile_resume(
    content_file: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    build_dir: Optional[Union[str, Path]] = None
) -> bool:
    """
    Compiles a resume YAML to PDF.
    This is a convenience wrapper around the ResumeCompiler class.
    """
    compiler = ResumeCompiler()
    return compiler.compile(content_file, output_path, build_dir)

async def compile_pdfs(jobs: List[tuple[Path, Path, Path]]):
    """
    Concurrently compile multiple YAML resumes to PDF.
    Takes a list of (yaml_path, pdf_path, build_dir) tuples.
    Each job uses its own build_dir.
    """
    logger = get_logger(__name__)
    if not jobs:
        logger.info("No PDFs to compile.")
        return
    
    tasks = []
    for yaml_path, pdf_path, build_dir in jobs:
        if not yaml_path or not yaml_path.exists():
            logger.warning(f"YAML file not found, cannot compile: {yaml_path}")
            continue
        logger.info(f"Queueing PDF compilation for {yaml_path} -> {pdf_path} (build_dir={build_dir})")
        task = asyncio.to_thread(lambda p=yaml_path, o=pdf_path, b=build_dir: compile_resume(content_file=p, output_path=o, build_dir=b))
        tasks.append(task)
    
    if tasks:
        await asyncio.gather(*tasks)
    logger.info("PDF compilation complete.") 