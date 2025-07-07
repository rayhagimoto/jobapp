import argparse
import sys
from jobapp.core.sheets_manager import SheetsManager
from jobapp.utils.filename import get_resume_filenames
from jobapp.utils.fuzzy_find import fuzzy_find_job
import asyncio


async def _main_async():
    # Handle direct delegation to submodules
    if len(sys.argv) > 1:
        subcommand = sys.argv[1]
        
        if subcommand == "search":
            # Delegate directly to search module
            original_argv = sys.argv[:]
            sys.argv = ['search'] + sys.argv[2:]  # Remove 'jobapp' from argv
            try:
                from jobapp.search.main import main as search_main
                await search_main()
                return
            finally:
                sys.argv = original_argv
        elif subcommand == "resume":
            # Delegate directly to resume-writer module
            original_argv = sys.argv[:]
            sys.argv = ['resume-writer'] + sys.argv[2:]
            try:
                from jobapp.resume_writer.main import main as resume_writer_main
                await resume_writer_main()
                return
            finally:
                sys.argv = original_argv
    
    # If no valid subcommand or help requested, show main help
    parser = argparse.ArgumentParser(
        description="JobApp CLI: Automate job search and resume generation."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Resume subcommand
    resume_parser = subparsers.add_parser(
        "resume",
        help="Resume-related commands (see `jobapp resume --help`)."
    )
    # This will be handled by the resume_writer's main
    resume_parser.add_argument('resume_command', nargs='?', help="The subcommand for resume operations.")
    resume_parser.add_argument('options', nargs='*', help="Options for the resume subcommand.")

    # Search subcommand
    search_parser = subparsers.add_parser(
        "search",
        help="LinkedIn job search and scraping tools."
    )

    # Filename subcommand (implemented here)
    filename_parser = subparsers.add_parser(
        "filename",
        help="Generate a base filename for a job by fuzzy search."
    )
    filename_parser.add_argument(
        'query', 
        type=str, 
        help="Fuzzy search query for the job."
    )

    args = parser.parse_args()

    if args.command == "resume":
        # Delegate to the resume_writer's main function
        from jobapp.resume_writer.main import main as resume_main
        await resume_main()
    elif args.command == "search":
        # This allows the search module to handle its own arguments
        from jobapp.search.main import main as search_main
        await search_main()
    elif args.command == "filename":
        from .utils.fuzzy_find import fuzzy_search_jobs
        from .utils.filename import generate_base_filename
        
        job = fuzzy_search_jobs(args.query)
        if job:
            base_filename = generate_base_filename(
                job.get('JobTitle', ''), 
                job.get('Company', ''), 
                job.get('Location', '')
            )
            print(base_filename)
        else:
            print(f"No job found for query: '{args.query}'")
    else:
        parser.print_help()
        sys.exit(1)

def main():
    asyncio.run(_main_async())
 