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
            
        Returns:
            bool: True if compilation was successful.
        """
        try:
            content_file = Path(content_file).resolve()
            
            if not content_file.exists():
                logger.error(f"YAML content file not found for compilation: {content_file}")
                return False

            if output_path:
                output_path = Path(output_path).resolve()
            else:
                output_path = content_file.with_suffix('.pdf')
            
            if not self.compiler_script_path.exists():
                logger.error(f"Compiler script not found at: {self.compiler_script_path}")
                return False

            cmd = [
                "python3", 
                str(self.compiler_script_path),
                "--content", str(content_file),
                "--output", str(output_path),
            ]

            if build_dir:
                build_dir = Path(build_dir).resolve()
                cmd.append("-b")
                cmd.append(str(build_dir))

            logger.info(f"Executing resume compiler: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                logger.error(f"PDF compilation script failed for {content_file}.")
                logger.error(f"Compiler STDOUT: {result.stdout.strip()}")
                logger.error(f"Compiler STDERR: {result.stderr.strip()}")
                return False
            
            logger.info(f"Successfully compiled {content_file} to {output_path}")
            return True

        except Exception as e:
            logger.error(f"An unexpected error occurred calling the resume compiler: {e}", exc_info=True)
            return False

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

async def compile_pdfs(paths: List[tuple[Path, Path]]):
    """
    Concurrently compile multiple YAML resumes to PDF.
    Takes a list of (yaml_path, pdf_path) tuples.
    """
    logger = get_logger(__name__)
    if not paths:
        logger.info("No PDFs to compile.")
        return
    
    tasks = []
    for yaml_path, pdf_path in paths:
        if not yaml_path or not yaml_path.exists():
            logger.warning(f"YAML file not found, cannot compile: {yaml_path}")
            continue
        
        logger.info(f"Queueing PDF compilation for {yaml_path} -> {pdf_path}")
        # Use a lambda to capture the arguments for the loop iteration
        task = asyncio.to_thread(lambda p=yaml_path, o=pdf_path: compile_resume(content_file=p, output_path=o))
        tasks.append(task)
    
    if tasks:
        await asyncio.gather(*tasks)

    logger.info("PDF compilation complete.") 