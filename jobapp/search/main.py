import argparse
import sys
import asyncio
from jobapp.search.linkedin_scraper import run_linkedin_navigation_agent
from jobapp.search import match_score_calculator

async def main():
    parser = argparse.ArgumentParser(
        description="Search for jobs on LinkedIn and related sources, or calculate match scores."
    )
    subparsers = parser.add_subparsers(dest="command", required=False)

    # --- Job Search Subcommand (default) ---
    search_parser = subparsers.add_parser("search", help="Search for jobs on LinkedIn (default)")
    search_parser.add_argument(
        "job_title",
        type=str,
        nargs='+',
        help="Job title to search for (e.g., 'Data Scientist')."
    )
    search_parser.add_argument(
        "--location",
        type=str,
        default=None,
        help="Location filter for job search (optional, stubbed)."
    )
    search_parser.add_argument(
        "--max-results",
        type=int,
        default=None,
        help="Maximum number of results to fetch (optional, stubbed)."
    )
    search_parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum number of pages to scrape (overrides config setting)."
    )
    search_parser.add_argument(
        "--browser-mode",
        type=str,
        choices=["patchright", "playwright", "system_chrome"],
        default="patchright",
        help="Browser mode to use: 'patchright' (stealth, default), 'playwright' (native Chromium), or 'system_chrome' (existing Chrome profile)."
    )
    search_parser.add_argument(
        "--chrome-path",
        type=str,
        default=None,
        help="Custom path to Chrome executable (auto-detected if not specified)."
    )
    search_parser.add_argument(
        "--chrome-profile",
        type=str,
        default=None,
        help="Custom path to Chrome profile directory (auto-detected if not specified)."
    )
    search_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable detailed logging (optional, stubbed)."
    )
    search_parser.add_argument(
        "--use-system-chrome",
        action="store_true",
        help="[DEPRECATED] Use --browser-mode=system_chrome instead. Use system Chrome browser instead of Patchright."
    )

    # --- Match Score Subcommand ---
    match_score_parser = subparsers.add_parser("match-score", help="Calculate match scores for jobs in Google Sheets using LLM")
    # (No additional arguments for now)

    # --- Login Subcommand ---
    login_parser = subparsers.add_parser("login", help="Manually log in to LinkedIn using Playwright and save session state for scraping.")
    # No additional arguments

    # Parse args
    args = parser.parse_args()

    if args.command == "match-score":
        # Run the match score calculator (async entrypoint)
        await match_score_calculator.main()
        return

    if args.command == "login":
        try:
            from jobapp.search import manual_login_playwright
        except ImportError:
            print("[ERROR] Playwright is not installed. Please install it with 'pip install playwright' and try again.")
            sys.exit(1)
        await manual_login_playwright.manual_linkedin_login()
        return

    # Default to job search if no subcommand or 'search' is given
    if args.command == "search" or args.command is None:
        # Handle backward compatibility
        if hasattr(args, 'use_system_chrome') and args.use_system_chrome:
            print("[WARNING] --use-system-chrome is deprecated. Use --browser-mode=system_chrome instead.")
            browser_mode = "system_chrome"
        else:
            browser_mode = args.browser_mode

        job_title = ' '.join(args.job_title)
        print(f"[INFO] Searching for jobs with title: '{job_title}'")
        if args.location:
            print(f"[INFO] Location filter: {args.location}")
        if args.max_results:
            print(f"[INFO] Max results: {args.max_results}")
        if args.max_pages:
            print(f"[INFO] Max pages: {args.max_pages}")
        print(f"[INFO] Browser mode: {browser_mode}")
        if args.verbose:
            print(f"[INFO] Verbose mode enabled.")

        # Call the async LinkedIn agent
        await run_linkedin_navigation_agent(
            job_title, 
            max_pages=args.max_pages, 
            browser_mode=browser_mode,
            chrome_path=args.chrome_path,
            chrome_profile=args.chrome_profile
        )

if __name__ == "__main__":
    asyncio.run(main()) 