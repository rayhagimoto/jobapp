import argparse
from pathlib import Path

def _create_common_parent_parser():
    """
    Creates a parser with common arguments shared across multiple subparsers.
    This parser is used as a parent to avoid duplicating argument definitions.
    """
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--input-resume",
        type=str,
        help="Path to input YAML resume file (defaults to config setting)"
    )
    parent_parser.add_argument(
        "-e", "--experiences",
        type=str,
        help="Path to consolidated experiences file (defaults to config setting)"
    )
    parent_parser.add_argument(
        "-o", "--output-dir",
        type=str,
        help="Directory to save optimized resume (defaults to './output')"
    )
    parent_parser.add_argument(
        "--model",
        type=str,
        help="Specific AI model to use (overrides config)"
    )
    parent_parser.add_argument(
        "--no-validation",
        action="store_true",
        help="Disable validation loops"
    )
    parent_parser.add_argument(
        "--no-compile-pdf",
        action="store_true",
        help="Disable automatic compilation of optimized YAML to PDF."
    )
    parent_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed logging"
    )
    return parent_parser

def _add_compile_subparser_args(subparsers: argparse._SubParsersAction):
    """Adds the 'compile' subparser and its arguments."""
    compile_parser = subparsers.add_parser(
        "compile",
        help="Compile a YAML resume file to PDF using the resume template"
    )
    compile_parser.add_argument(
        "--content",
        type=str,
        help="Full path to content.yaml file"
    )
    compile_parser.add_argument(
        "-o", "--output",
        type=str,
        help="Full path for the output PDF, e.g., /path/to/output.pdf"
    )

def _add_optimize_subparser_args(subparsers: argparse._SubParsersAction, common_parent_parser: argparse.ArgumentParser):
    """
    Adds the 'optimize' subparser and its arguments to the given subparsers object.
    Uses the common_parent_parser for shared arguments.
    """
    optimize_parser = subparsers.add_parser(
        "optimize",
        parents=[common_parent_parser], # Inherit common arguments
        help="AI-powered resume optimization for specific job descriptions"
    )
    optimize_parser.add_argument(
        "input_resume_positional",
        type=str,
        nargs="?",
        help="Path to input YAML resume file (positional, alternative to --input-resume)"
    )
    optimize_parser.add_argument(
        "-j", "--job-description",
        type=str,
        required=True,
        help="Job description text or path to file containing job description"
    )
    optimize_parser.add_argument(
        "--company",
        type=str,
        default="Test Company",
        help="Company name for the job (default: Test Company)"
    )
    optimize_parser.add_argument(
        "--location",
        type=str,
        default="Remote",
        help="Job location (default: Remote)"
    )
    optimize_parser.add_argument(
        "--job-title",
        type=str,
        help="Job title (optional, will be extracted from resume if not provided)"
    )
    optimize_parser.add_argument(
        "--include-sections",
        type=str,
        help="Comma-separated list of sections to optimize (e.g., 'profile,skills,experience')"
    )
    # Set default for no_compile_pdf to False (meaning compile by default)
    optimize_parser.set_defaults(no_compile_pdf=False)


def _add_optimize_batch_subparser_args(subparsers: argparse._SubParsersAction, common_parent_parser: argparse.ArgumentParser):
    """Adds the 'optimize-batch' subparser and its arguments."""
    batch_parser = subparsers.add_parser(
        "optimize-batch",
        parents=[common_parent_parser], # Inherit common arguments
        help="Run AI-powered resume optimization for a batch of jobs from Google Sheets."
    )
    batch_parser.add_argument(
        "-m", "--match-score-threshold",
        type=int,
        default=75,
        help="Minimum match score (1-100) to be eligible for optimization (default: 75)."
    )
    batch_parser.add_argument(
        "--max-resumes",
        type=int,
        help="Maximum number of resumes to optimize in this batch (overrides config setting)."
    )
    batch_parser.add_argument(
        "--overwrite-files",
        choices=['true', 'false'],
        nargs='?',
        const=None,
        help="Control file overwriting behavior: 'true' to overwrite, 'false' to skip, or omit value to prompt user (default: prompt)."
    )
    # Set default for no_compile_pdf to False (meaning compile by default)
    batch_parser.set_defaults(no_compile_pdf=False)


def _add_optimize_job_subparser_args(subparsers: argparse._SubParsersAction, common_parent_parser: argparse.ArgumentParser):
    """Adds the 'optimize-job' subparser and its arguments."""
    optimize_job_parser = subparsers.add_parser(
        "optimize-job",
        parents=[common_parent_parser], # Inherit common arguments
        help="Fuzzy search for a job in Google Sheets and optimize resume for it, or use a job description file."
    )
    optimize_job_parser.add_argument(
        "query",
        type=str,
        nargs='*',
        help="Search terms for job/company/location (e.g., 'visa data scientist', 'google software engineer'). If omitted, you must provide -j/--jd."
    )
    optimize_job_parser.add_argument(
        "-j", "--jd", "--job-description",
        dest="job_description_file",
        type=str,
        help="Path to a file containing the job description. If provided, skips Google Sheets fuzzy search."
    )
    optimize_job_parser.add_argument(
        "--company",
        type=str,
        default=None,
        help="Company name for the job (optional, overrides value from Google Sheets if provided)"
    )
    optimize_job_parser.add_argument(
        "--location",
        type=str,
        default=None,
        help="Job location (optional, overrides value from Google Sheets if provided)"
    )
    optimize_job_parser.add_argument(
        "--job-title",
        type=str,
        default=None,
        help="Job title (optional, overrides value from Google Sheets if provided)"
    )
    optimize_job_parser.add_argument(
        "--include-sections",
        type=str,
        help="Comma-separated list of sections to optimize (e.g., 'profile,skills,experience')"
    )
    # Set default for no_compile_pdf to False (meaning compile by default)
    optimize_job_parser.set_defaults(no_compile_pdf=False)


def _add_process_subparser_args(subparsers: argparse._SubParsersAction):
    """Adds the 'process' subparser and its arguments."""
    process_parser = subparsers.add_parser(
        "process",
        help="Process jobs for resume generation (existing functionality)"
    )
    # No specific arguments for process mode currently, based on main.py


def _add_single_subparser_args(subparsers: argparse._SubParsersAction, common_parent_parser: argparse.ArgumentParser):
    """Adds the 'single' subparser and its arguments."""
    single_parser = subparsers.add_parser(
        "single",
        parents=[common_parent_parser], # Inherit common arguments
        help="Find a single job from Google Sheets via fuzzy search and optimize for it"
    )
    single_parser.add_argument(
        "query",
        type=str,
        help="Fuzzy search query to find the job in Google Sheets"
    )
    # Set default for no_compile_pdf to False (meaning compile by default)
    single_parser.set_defaults(no_compile_pdf=False)


def _add_cache_subparser_args(subparsers: argparse._SubParsersAction):
    """Adds the 'cache' subparser and its 'clean' subcommand."""
    cache_parser = subparsers.add_parser(
        "cache",
        help="Cache management commands."
    )
    cache_subparsers = cache_parser.add_subparsers(dest="action", required=True)
    clean_parser = cache_subparsers.add_parser(
        "clean",
        help="Clean up all files in the cache directory."
    )
    clean_parser.set_defaults(mode="cache", action="clean")


def parse_arguments():
    """
    Parses all command-line arguments for the resume_writer module.
    This is the main entry point for argument parsing.
    """
    parser = argparse.ArgumentParser(
        description="Generate tailored resumes for job applications."
    )
    subparsers = parser.add_subparsers(dest="mode", required=True, help="Operation mode")

    common_parent_parser = _create_common_parent_parser()

    _add_compile_subparser_args(subparsers)
    _add_optimize_subparser_args(subparsers, common_parent_parser)
    _add_optimize_batch_subparser_args(subparsers, common_parent_parser)
    _add_optimize_job_subparser_args(subparsers, common_parent_parser)
    _add_process_subparser_args(subparsers)
    _add_single_subparser_args(subparsers, common_parent_parser)
    _add_cache_subparser_args(subparsers)

    args = parser.parse_args()

    # Handle positional input_resume for 'optimize' subcommand
    if args.mode == "optimize" and args.input_resume_positional:
        args.input_resume = args.input_resume_positional

    # Validate optimize-job: must provide either query or job_description_file
    if args.mode == "optimize-job":
        if (not args.query or len(args.query) == 0) and not args.job_description_file:
            parser.error("optimize-job: You must provide either a search query or -j/--jd <job_description_file>.")

    return args
