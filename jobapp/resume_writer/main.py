import sys
import subprocess
from pathlib import Path
import os
import time
from jobapp.resume_writer.parser import parse_arguments
from jobapp.core.config_manager import ConfigManager
from jobapp.core.logger import get_logger
from jobapp.core.sheets_manager import SheetsManager
from jobapp.utils.filename import get_resume_filenames
from jobapp.utils.fuzzy_find import fuzzy_find_job
from .batch_optimizer import run_batch_optimization, get_job_by_query, process_single_job
from .compiler import compile_resume

async def main():
    args = parse_arguments()
    config = ConfigManager()
    logger = get_logger(__name__)

    # Centralized early check for modes that require the user's name
    if args.mode in ("optimize-job", "optimize-batch"):
        try:
            your_name = config.get_user_name()
        except ValueError as e:
            logger.error(str(e))
            sys.exit(1)
    else:
        your_name = None

    # Robust compile_pdf assignment for all modes
    compile_pdf = True if not hasattr(args, 'no_compile_pdf') else not args.no_compile_pdf

    if args.mode == "compile":
        # Always compile PDF in this mode
        script_dir = Path(__file__).parent
        resume_template_dir = script_dir / "resume_template"
        if args.content is None:
            args.content = str(resume_template_dir / "contents" / "resume.yaml")
        if args.output is None:
            args.output = str(resume_template_dir / "build" / "resume.pdf")
        compile_script = resume_template_dir / "compile_resume.py"
        cmd = [
            sys.executable,
            str(compile_script),
            "--content", args.content,
            "--output", args.output
        ]
        try:
            result = subprocess.run(cmd, check=True, capture_output=False)
            print(f"[SUCCESS] Resume compiled to: {args.output}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Compilation failed with exit code {e.returncode}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            sys.exit(1)

    elif args.mode == "optimize-job":
        input_resume_path = Path(args.input_resume) if args.input_resume else Path(config.get_user_resume_path())
        experiences_path = Path(args.experiences) if args.experiences else Path(config.get_experiences_path())

        if args.job_description_file:
            job_description_path = Path(args.job_description_file)
            if not job_description_path.is_file():
                logger.error(f"Job description file not found: {job_description_path}")
                sys.exit(1)
            with open(job_description_path, 'r', encoding='utf-8') as f:
                job_description = f.read()
            job_info = {
                "JobTitle": args.job_title or "Unknown Job",
                "Company": args.company or "Test Company",
                "Location": args.location or "Remote",
                "JobDescription": job_description,
                "MatchScore": 0
            }
        else:
            query = ' '.join(args.query)
            job_info = await get_job_by_query(query)
            if not job_info:
                logger.error(f"Could not find a job matching query: '{query}'")
                sys.exit(1)

        # --- SINGLE SOURCE OF TRUTH FOR OUTPUT FILENAMES/DIRS ---
        filenames = get_resume_filenames(
            your_name=your_name,
            job_title=job_info["JobTitle"],
            company=job_info["Company"],
            location=job_info["Location"],
            match_score=job_info.get("MatchScore")
        )
        output_dir = Path(args.output_dir) if args.output_dir else Path("output") / filenames['dir']
        # All output file paths (YAML, PDF, etc.) should be constructed using the values from get_resume_filenames
        # Pass output_dir and filenames to the pipeline/output manager as needed

        try:
            result = await process_single_job(
                job_info=job_info,
                input_resume_path=input_resume_path,
                experiences_path=experiences_path,
                output_dir=output_dir,
                overwrite=True,
                compile_pdf=compile_pdf,
                your_name=your_name
            )
            if result.get('success'):
                print(f"\n[SUCCESS] Single job optimization complete.")
                print(f"Output located at: {result.get('output_dir')}")
                sys.exit(0)
            else:
                logger.error(f"Single job optimization failed. Reason: {result.get('reason')}")
                sys.exit(1)
        except Exception as e:
            logger.error(f"An unexpected error occurred during optimization: {e}")
            sys.exit(1)

    elif args.mode == "optimize-batch":
        # --- SINGLE SOURCE OF TRUTH FOR OUTPUT FILENAMES/DIRS ---
        output_dir = Path(args.output_dir) if args.output_dir else Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)  # Ensure parent output directory exists before dispatching jobs
        # Pass output_dir to run_batch_optimization, which must use get_resume_filenames for each job
        if args.verbose:
            import logging
            logging.getLogger().setLevel(logging.INFO)
        if args.input_resume:
            input_resume_path = Path(args.input_resume).resolve()
        else:
            input_resume_path = Path(config.get_user_resume_path()).resolve()
        if args.experiences:
            experiences_path = Path(args.experiences).resolve()
        else:
            experiences_path = Path(config.get_experiences_path()).resolve()
        if not input_resume_path.is_file():
            logger.error(f"Input resume file not found at: {input_resume_path}")
            sys.exit(1)
        if not experiences_path.is_file():
            logger.error(f"Experiences file not found at: {experiences_path}")
            sys.exit(1)
        # Harmonize overwrite logic with optimize-job convention
        overwrite = (args.overwrite_files == 'true') if hasattr(args, 'overwrite_files') and args.overwrite_files is not None else False
        logger.info("Running Batch Optimization with the following settings:")
        logger.info(f"  - Input Resume: {input_resume_path}")
        logger.info(f"  - Experiences File: {experiences_path}")
        logger.info(f"  - Output Directory: {output_dir}")
        logger.info(f"  - Match Score Threshold: {args.match_score_threshold}")
        logger.info(f"  - Max Resumes: {args.max_resumes or 'default from config'}")
        logger.info(f"  - Overwrite: {overwrite}")
        logger.info(f"  - Compile PDF: {compile_pdf}")
        try:
            await run_batch_optimization(
                input_resume_path=input_resume_path,
                experiences_path=experiences_path,
                output_dir=output_dir,
                match_score_threshold=args.match_score_threshold,
                max_resumes=args.max_resumes,
                overwrite=overwrite,
                compile_pdf=compile_pdf,
                your_name=your_name
            )
        except KeyboardInterrupt:
            logger.info("Batch optimization cancelled by user.")
            sys.exit(0)
        except Exception as e:
            logger.critical(f"An unexpected error occurred during batch optimization: {e}")
            sys.exit(1)
    else:
        logger.error(f"Unknown mode: {args.mode}")
        sys.exit(1)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

    
 