import asyncio
import datetime
import random
import re
from pathlib import Path

# Core imports for SheetsManager, moved to top-level scope
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from dotenv import load_dotenv

# Use Patchright for stealth capabilities
from patchright.async_api import async_playwright as async_patchright
# Use standard Playwright for native Chromium support
from playwright.async_api import async_playwright, Page, Locator, Browser, BrowserContext

from ..core.config_manager import ConfigManager
from ..core.chrome_manager import ChromeManager
# REMOVED: from ..core.sheets_manager import SheetsManager (because it's now defined here)
from ..utils import parse_linkedin_date
from .match_score_calculator import MatchScoreCalculator

# Initialize the config manager once globally
config = ConfigManager()
AUTH_STATE_PATH = Path(config.get_linkedin_auth_state_path())
SEARCH_CONFIG = config.get_yaml_config(
    "search", default={"linkedin_filters": {"company_blacklist": []}}
)
COMPANY_BLACKLIST = [
    company.lower()
    for company in SEARCH_CONFIG.get("linkedin_filters", {}).get(
        "company_blacklist", []
    )
]
DEFAULT_MAX_PAGES = SEARCH_CONFIG.get("linkedin_filters", {}).get(
    "max_pages", 20
)

SHEET_HEADERS = [
    "JobTitle", "Company", "Location", "DatePosted", "DateUpdated",
    "LinkedinURL", "CompanyURL", "Applied", "Status", "JobDescription",
    "MatchScore",
]


# --- HELPER FUNCTIONS FOR HUMAN-LIKE INTERACTION ---
async def human_delay(min_s: float = 0.8, max_s: float = 2.5):
    """Introduces a human-like, random delay."""
    await asyncio.sleep(random.uniform(min_s, max_s))

async def human_click(page: Page, locator: Locator):
    """Performs a human-like click, ensuring the action completes."""
    try:
        # Attempt to hover first, then click. Adds realism.
        await locator.hover(timeout=5000)
        await human_delay(0.1, 0.3)  # Small delay after hover
        await locator.click(timeout=10000)
    except Exception as e:
        print(
            f"    - [WARNING] Human-like click failed. Falling back to direct click. Error: {e}"
        )
        # Ensure the click still happens even if the human-like part fails
        await locator.click(timeout=10000)
    await human_delay(0.5, 1.0)  # Delay after the click


async def human_fill(page: Page, locator: Locator, text: str):
    """Types text with human-like pauses between characters."""
    # This assumes the locator has already been clicked once to gain focus
    await human_delay(0.3, 0.7)  # Pause before typing starts

    for char in text:
        # Type character by character with random delays
        await locator.type(char, delay=random.uniform(50, 150))  # delay in ms
        await asyncio.sleep(random.uniform(0.01, 0.05))  # very short inter-char pause
    await human_delay(0.5, 1.0)  # Pause after typing is complete


# --- INTERNAL IMPLEMENTATION: The Hardcoded Scraper Class ---
class _LinkedinScraper:
    def __init__(self, job_title: str, location: str, max_pages: int, browser_mode: str = "patchright", 
                 chrome_path: str = None, chrome_profile: str = None):
        self.job_title = job_title
        self.location = location
        self.max_pages = max_pages
        self.browser_mode = browser_mode  # "patchright", "playwright", or "system_chrome"
        self.chrome_path = chrome_path
        self.chrome_profile = chrome_profile
        self.jobs_data = []
        
        # Browser instances
        self.playwright_instance = None
        self.patchright_playwright_instance = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.chrome_manager: ChromeManager | None = None

    async def run(self) -> list[dict]:
        if self.browser_mode == "system_chrome":
            return await self._run_with_system_chrome()
        elif self.browser_mode == "playwright":
            return await self._run_with_playwright()
        else:  # default to patchright
            return await self._run_with_patchright()

    async def _run_with_playwright(self) -> list[dict]:
        """Run with native Playwright Chromium support"""
        print("[INFO] Using native Playwright Chromium browser...")
        
        if not AUTH_STATE_PATH.exists():
            raise FileNotFoundError(
                f"Auth file not found at '{AUTH_STATE_PATH}'. "
                "Please run the manual login script first to create a session state."
            )

        try:
            self.playwright_instance = await async_playwright().start()
            
            # Launch Chromium with stealth-like settings
            self.browser = await self.playwright_instance.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--disable-extensions",
                    "--disable-plugins-discovery",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-infobars",
                    "--disable-notifications",
                    "--disable-popup-blocking"
                ]
            )
            
            # Create context with saved authentication state
            self.context = await self.browser.new_context(
                storage_state=str(AUTH_STATE_PATH),
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            # Create new page
            page = await self.context.new_page()
            
            # Navigate to LinkedIn main page to start
            print("[INFO] Navigating to LinkedIn...")
            await page.goto("https://www.linkedin.com", wait_until="domcontentloaded", timeout=60000)
            await human_delay(2.0, 3.0)
            
            return await self._run_scraping_logic(page)
            
        finally:
            await self._cleanup_playwright()

    async def _run_with_system_chrome(self) -> list[dict]:
        print("[INFO] Using system Chrome browser...")
        
        # Initialize Chrome manager
        self.chrome_manager = ChromeManager()
        
        # Find Chrome executable
        chrome_exe = self.chrome_manager.find_chrome_executable(self.chrome_path)
        if not chrome_exe:
            raise RuntimeError("Could not find Chrome executable. Please install Google Chrome or specify the path with --chrome-path")
        
        # Find Chrome profile
        profile_dir = self.chrome_manager.find_chrome_profile_dir(self.chrome_profile)
        if not profile_dir:
            raise RuntimeError("Could not find Chrome profile directory. Please specify the profile directory with --chrome-profile")
        
        # Start Chrome with remote debugging using actual profile
        try:
            self.chrome_manager.start_chrome_debug(chrome_exe, profile_dir, open_linkedin=True, use_actual_profile=True)
            
            if not self.chrome_manager.wait_for_debug_ready():
                raise RuntimeError("Chrome remote debugging failed to start")
            
            print("[INFO] Chrome is ready. You should see a Chrome window with LinkedIn loaded.")
            print("[INFO] Using your actual Chrome profile - all settings and extensions will be available.")
            
            # Connect to Chrome via CDP
            self.playwright_instance = await async_playwright().start()
            self.browser = await self.playwright_instance.chromium.connect_over_cdp(f"http://localhost:{self.chrome_manager.debug_port}")
            
            # Get the first (or create new) page
            contexts = self.browser.contexts
            if contexts:
                context = contexts[0]
                pages = context.pages
                if pages:
                    page = pages[0]
                else:
                    page = await context.new_page()
            else:
                context = await self.browser.new_context()
                page = await context.new_page()

            return await self._run_scraping_logic(page)
            
        except Exception as e:
            print(f"[ERROR] Failed to start or connect to Chrome: {e}")
            raise
        finally:
            await self._cleanup_system_chrome()

    async def _run_with_patchright(self) -> list[dict]:
        """Run with Patchright for enhanced stealth capabilities"""
        if not AUTH_STATE_PATH.exists():
            raise FileNotFoundError(
                f"Auth file not found at '{AUTH_STATE_PATH}'. "
                "Please run the manual login script first to create a session state."
            )

        print("[INFO] Initializing Patchright browser engine...")
        
        try:
            self.patchright_playwright_instance = await async_patchright().start()

            print("[INFO] Starting Patchright browser with stealth mode...")
            
            # Launch Patchright Chromium with stealth settings
            self.browser = await self.patchright_playwright_instance.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-first-run",
                    "--no-default-browser-check"
                ]
            )
            
            # Create context with saved authentication state
            self.context = await self.browser.new_context(
                storage_state=str(AUTH_STATE_PATH),
                viewport={"width": 1920, "height": 1080}
            )
            
            # Create new page
            page = await self.context.new_page()
            
            # Navigate to LinkedIn main page to start
            print("[INFO] Navigating to LinkedIn...")
            await page.goto("https://www.linkedin.com", wait_until="domcontentloaded", timeout=60000)
            await human_delay(2.0, 3.0)
            
            return await self._run_scraping_logic(page)
            
        finally:
            await self._cleanup_patchright()

    async def _cleanup_playwright(self):
        """Clean up Playwright resources"""
        try:
            if self.context:
                await self.context.close()
        except Exception as e:
            print(f"[WARNING] Could not close browser context cleanly: {e}")
        
        try:
            if self.browser:
                await self.browser.close()
        except Exception as e:
            print(f"[WARNING] Could not close browser cleanly: {e}")
        
        try:
            if self.playwright_instance:
                await self.playwright_instance.stop()
        except Exception as e:
            print(f"[WARNING] Could not stop playwright instance cleanly: {e}")

    async def _cleanup_patchright(self):
        """Clean up Patchright resources"""
        try:
            if self.context:
                await self.context.close()
        except Exception as e:
            print(f"[WARNING] Could not close browser context cleanly: {e}")
        
        try:
            if self.browser:
                await self.browser.close()
        except Exception as e:
            print(f"[WARNING] Could not close browser cleanly: {e}")
        
        try:
            if self.patchright_playwright_instance:
                await self.patchright_playwright_instance.stop()
        except Exception as e:
            print(f"[WARNING] Could not stop patchright instance cleanly: {e}")

    async def _cleanup_system_chrome(self):
        """Clean up system Chrome resources"""
        try:
            if self.playwright_instance:
                await self.playwright_instance.stop()
        except Exception as e:
            print(f"[WARNING] Could not stop playwright instance cleanly: {e}")
        
        # Clean up Chrome manager (but don't clean up the actual profile!)
        if self.chrome_manager:
            self.chrome_manager.stop_chrome()
            self.chrome_manager.cleanup()  # Now safe - only cleans temp dirs

    async def _run_scraping_logic(self, page: Page) -> list[dict]:
        """Common scraping logic used by all browser modes"""
        try:
            await self._wait_for_manual_navigation(page)

            for i in range(self.max_pages):
                print(f"\n--- Scraping Page {i+1}/{self.max_pages} ---")
                try:
                    await self._scroll_to_load_jobs(page) # Ensure all jobs on current page are loaded
                    await self._scrape_jobs_on_page(page) # Process loaded jobs

                    can_continue = await self._navigate_to_next_page(page)
                    if not can_continue:
                        print("[INFO] No more pages to scrape.")
                        break
                    await human_delay(3.0, 7.0) # Longer delay between pages
                except Exception as e:
                    print(f"[ERROR] Page {i+1} processing failed (likely browser crash): {e}")
                    print(f"[INFO] Stopping scraping early. Collected {len(self.jobs_data)} jobs so far.")
                    break

            print(f"\n[INFO] Scraping complete. Collected {len(self.jobs_data)} jobs total. Browser will close in 5 seconds...")
            await human_delay(5.0, 8.0) # Final human delay before closing

        except Exception as e:
            print(f"[ERROR] Critical error during scraping: {e}")
            print(f"[INFO] Returning {len(self.jobs_data)} jobs collected before the error.")

        return self.jobs_data

    async def _wait_for_manual_navigation(self, page: Page):
        print(f"\n[MANUAL NAVIGATION REQUIRED]")
        print(f"Please manually navigate to LinkedIn job search with the following criteria:")
        print(f"  - Job Title: {self.job_title}")
        print(f"  - Location: {self.location}")
        print(f"  - Make sure you can see job cards on the left and job details on the right")
        print(f"  - Once you're on the correct job search page, press Enter to continue...")
        
        # Wait for user input
        try:
            input()  # This will block until user presses Enter
        except KeyboardInterrupt:
            print("\n[INFO] Scraping cancelled by user.")
            raise
        
        print("[INFO] Checking if we're on a valid LinkedIn job search page...")
        try:
            # Wait for job cards to be present
            await page.wait_for_selector("div[data-job-id]", timeout=30000)
            print("[SUCCESS] Job search page detected. Starting scraping...")
            await human_delay(1.5, 3.0)
        except Exception as e:
            print(f"[ERROR] Could not find job cards on the current page.")
            print(f"Please make sure you're on a LinkedIn job search page with visible job listings.")
            print(f"Error details: {e}")
            raise

    def _clean_text(self, text: str) -> str:
        """Removes common unwanted phrases and extra whitespace."""
        text = (
            text.replace("with verification", "")
            .replace("<!---->", "")
            .strip()
        )
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    async def _scrape_jobs_on_page(self, page: Page):
        # FIX: Robust iteration using data-job-id to prevent "Can't query n-th element" errors
        # Get all job IDs on the current page first
        job_card_elements = await page.locator("div[data-job-id]").all()
        job_ids_on_page = [
            await card.get_attribute("data-job-id")
            for card in job_card_elements
            if await card.get_attribute("data-job-id") is not None
        ]
        
        print(f"[INFO] Found {len(job_ids_on_page)} jobs on this page to process.")
        processed_count = 0
        
        # Iterate through IDs and create fresh locators for each
        for job_id in job_ids_on_page:
            try:
                # Create a specific locator for the job card using its unique ID
                job_element_by_id = page.locator(f'div[data-job-id="{job_id}"]').first
                
                # Ensure it's visible before trying to extract data or click
                if not await job_element_by_id.is_visible(timeout=5000):
                    print(f"  - [WARNING] Job with ID {job_id} not visible. Skipping.")
                    continue

                # --- Extract JobTitle and Company from the job card ---
                title_link_locator = job_element_by_id.locator('a[class*="job-card-container__link"]').first
                job_title_from_aria = await title_link_locator.get_attribute('aria-label', timeout=2000)
                job_title_on_card = self._clean_text(job_title_from_aria or await title_link_locator.inner_text(timeout=2000))

                company_locator = job_element_by_id.locator('div[class*="artdeco-entity-lockup__subtitle"] span').first
                company_name_on_card = self._clean_text(await company_locator.inner_text(timeout=2000))

                # --- Filtering (Blacklist and Ambiguous Title) ---
                if job_title_on_card == company_name_on_card:
                    print(f"  - [WARNING] Skipping job (ID {job_id}) due to ambiguous title/company name: '{job_title_on_card}'")
                    continue

                if company_name_on_card.lower() in COMPANY_BLACKLIST:
                    print(f"  - Skipping job (ID {job_id}): '{company_name_on_card}' is in blacklist.")
                    continue

                # Pass pre-scraped title and company. _extract_job_details will click this job_element_by_id
                job_data = await self._extract_job_details(job_element_by_id, page, job_title_on_card, company_name_on_card)

                if job_data:
                    self.jobs_data.append(job_data)
                    processed_count += 1
                    print(f"  - Scraped ({processed_count}/{len(job_ids_on_page)} processed): {job_data['JobTitle']} at {job_data['Company']}")
            except Exception as e:
                print(f"  - [WARNING] Failed to process job with ID {job_id}. Card extraction issue. Error: {e}")
        
        print(f"[INFO] Successfully processed {processed_count} jobs on this page.")


    async def _extract_job_details(
        self,
        job_element: Locator, # This is now always a specific locator for the current job_id
        page: Page,
        scraped_job_title: str,
        scraped_company_name: str,
    ) -> dict | None:
        try:
            await human_click(page, job_element)
        except Exception as e:
            print(
                f"    - [WARNING] Could not click job card for "
                f"'{scraped_job_title}'. Skipping. Error: {e}"
            )
            return None

        details_panel_selector = ".jobs-search__job-details--wrapper"
        try:
            await page.wait_for_selector(details_panel_selector, timeout=10000)
        except Exception:
            print(
                f"    - [WARNING] Details panel did not load for "
                f"'{scraped_job_title}'. Skipping."
            )
            return None

        job_id = await job_element.get_attribute("data-job-id")
        if not job_id:
            return None

        linkedin_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
        top_card_locator = page.locator(
            ".job-details-jobs-unified-top-card__primary-description-container"
        )
        details_text = await top_card_locator.inner_text()
        details_list = [
            item.strip() for item in details_text.split("·") if item.strip()
        ]

        location = details_list[0] if details_list else "N/A"
        date_posted_raw = (
            details_list[1] if len(details_list) > 1 else "N/A"
        )
        formatted_date_posted = parse_linkedin_date(date_posted_raw)

        linkedin_description = "No description found."
        try:
            see_more_button = page.locator(
                f'{details_panel_selector} button[aria-label="Click to see more description"]'
            )

            if await see_more_button.is_visible(timeout=2000):
                print("    - Clicking 'See more' to expand description in-panel...")
                await human_click(page, see_more_button)
                await asyncio.sleep(0.5)

            description_locator = page.locator(
                f"{details_panel_selector} #job-details"
            )
            linkedin_description = (
                await description_locator.inner_text(timeout=5000)
            ).strip()

        except Exception:
            try:
                linkedin_description = (
                    await page.locator(details_panel_selector).inner_text()
                ).strip()
            except Exception as final_e:
                linkedin_description = f"Error retrieving description: {final_e}"

        return {
            "JobTitle": scraped_job_title,
            "Company": scraped_company_name,
            "Location": location,
            "DatePosted": formatted_date_posted,
            "DateUpdated": datetime.date.today().strftime("%Y-%m-%d"),
            "LinkedinURL": linkedin_url,
            "CompanyURL": "",
            "Applied": "FALSE",
            "Status": "",
            "JobDescription": linkedin_description,
            "MatchScore": "",
            "Type": "",
        }

    async def _scroll_to_load_jobs(self, page: Page):
        print("[INFO] Scrolling job list panel with mouse wheel...")
        job_list_selector = "div[data-results-list-top-scroll-sentinel] + ul"
        job_item_selector = "li[data-occludable-job-id]"

        try:
            scrollable_list = page.locator(job_list_selector)
            await scrollable_list.wait_for(state="visible", timeout=10000)

            stall_count = 0
            max_scroll_attempts = 50
            max_stalls = 3

            for attempt in range(max_scroll_attempts):
                previous_job_count = await page.locator(job_item_selector).count()

                await scrollable_list.hover()
                await page.mouse.wheel(0, 1000)
                await human_delay(1.5, 3.0)

                current_job_count = await page.locator(job_item_selector).count()
                print(
                    f"    - Scroll attempt {attempt + 1}. "
                    f"Jobs found: {current_job_count}"
                )

                if current_job_count == previous_job_count:
                    stall_count += 1
                    print(
                        f"    - No new jobs loaded. Stall count: {stall_count}/{max_stalls}"
                    )
                else:
                    stall_count = 0

                if stall_count >= max_stalls:
                    print(
                        f"[SUCCESS] Scrolled to bottom of list (no new jobs for {max_stalls} attempts)."
                    )
                    break
            else:
                print("[WARNING] Max scroll attempts reached.")

        except Exception as e:
            print(f"[ERROR] Could not perform scroll on job list. Error: {e}")

    async def _navigate_to_next_page(self, page: Page) -> bool:
        print("[INFO] Attempting to navigate to the next page...")
        try:
            # First, ensure main window is scrolled to bottom where pagination usually lives
            await page.evaluate(
                "window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })"
            )
            await human_delay(1.0, 2.0) # Allow time for new content to render if scroll triggered it

            # Locate the 'Next' button specifically within the pagination area
            next_button_locator = page.locator('.jobs-search-pagination button[aria-label="View next page"]')

            # Robust loop to wait for and click the next button
            for attempt in range(3): # Try a few times
                if await next_button_locator.is_visible(timeout=5000):
                    if not await next_button_locator.is_disabled():
                        print("[INFO] Clicking 'Next' button...")
                        await human_click(page, next_button_locator)
                        # Wait for network idle or domcontentloaded after clicking next
                        await page.wait_for_load_state("domcontentloaded", timeout=60000)
                        await human_delay(2.0, 4.0) # Longer delay after page navigation
                        return True
                    else:
                        print("[INFO] 'Next' button is disabled (likely last page).")
                        return False
                print(f"[INFO] 'Next' button not visible (attempt {attempt + 1}/5). Retrying...")
                await human_delay(2.0, 3.0) # Longer delay before next visibility check

            print("[INFO] 'Next' button could not be found after multiple attempts. Assuming last page.")
            return False # Could not find/click next button after retries

        except Exception as e:
            print(f"[ERROR] Could not navigate to next page. Error: {e}")
            try:
                screenshot_path = f"debug_screenshot_page_nav_failed_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=screenshot_path, full_page=True)
                print(f"[DEBUG] Saved screenshot to {screenshot_path}")
            except Exception as screenshot_error:
                print(f"[WARNING] Could not take screenshot (page likely crashed): {screenshot_error}")
            return False


# --- SheetsManager class ---
class SheetsManager:
    def __init__(self, spreadsheet_id=None, tab_name=None, creds_path=None):
        from ..core.config_manager import ConfigManager
        load_dotenv()
        self.config = ConfigManager()
        self.spreadsheet_id = spreadsheet_id or os.getenv('SPREADSHEET_ID', '1tr5zC73JV1WF-04VkAe4181dIeM4wr2Yw7kuL7-xkxg')
        self.tab_name = tab_name or os.getenv('TAB_NAME', 'Data')
        self.creds_path = creds_path or self.config.get_gspread_credentials_path()
        self.scope = ['https://www.googleapis.com/auth/spreadsheets']
        self.creds = ServiceAccountCredentials.from_json_keyfile_name(self.creds_path, self.scope)
        self.client = gspread.authorize(self.creds)
        self.sheet = self.client.open_by_key(self.spreadsheet_id).worksheet(self.tab_name)

    def get_all_records(self):
        return self.sheet.get_all_records()

    def append_row(self, row):
        self.sheet.append_row(row)

    def append_rows(self, rows):
        if rows:
            self.sheet.append_rows(rows)

    def get_dataframe(self):
        records = self.get_all_records()
        return pd.DataFrame(records)


# --- PUBLIC INTERFACE ---
async def run_linkedin_navigation_agent(keyword: str, max_pages: int = None, browser_mode: str = "patchright",
                                        chrome_path: str = None, chrome_profile: str = None):
    """
    Orchestrates the hardcoded job scraping and sheet updating process.
    
    Args:
        keyword: Job title to search for
        max_pages: Maximum number of pages to scrape (overrides config)
        browser_mode: Browser mode to use ("patchright", "playwright", or "system_chrome")
        chrome_path: Custom path to Chrome executable (auto-detected if not specified)
        chrome_profile: Custom path to Chrome profile directory (auto-detected if not specified)
    """
    print(f"[INFO] Running hardcoded scraper with {browser_mode} browser mode...")

    location = "United States"
    max_pages = max_pages or DEFAULT_MAX_PAGES

    try:
        sheets_manager = SheetsManager()
        scraper = _LinkedinScraper(
            job_title=keyword, location=location, max_pages=max_pages, browser_mode=browser_mode,
            chrome_path=chrome_path, chrome_profile=chrome_profile
        )

        print(
            "[INFO] Fetching existing jobs from Google Sheet to prevent duplicates..."
        )
        existing_jobs_df = sheets_manager.get_dataframe()
        existing_urls = (
            set(existing_jobs_df["LinkedinURL"])
            if "LinkedinURL" in existing_jobs_df.columns
            else set()
        )
        print(
            f"[INFO] Found {len(existing_urls)} existing job URLs in the sheet."
        )

        scraped_jobs = await scraper.run()
        if not scraped_jobs:
            print("[INFO] No jobs were scraped. Exiting.")
            return

        # REMOVED: Unique job filtering from this section. It's handled by SheetsManager's append_rows
        # with the understanding that it won't re-add existing rows.
        # This simplifies the post-scrape processing.
        jobs_to_process_for_sheet = []
        for job in scraped_jobs:
            if job["LinkedinURL"] not in existing_urls:
                jobs_to_process_for_sheet.append(job)
            else:
                print(
                    f"[INFO] Skipping duplicate for sheet: {job['JobTitle']} at {job['Company']} (URL already exists)"
                )
        
        print(
            f"\n[RESULT] Scraped: {len(scraped_jobs)} | New jobs to add: {len(jobs_to_process_for_sheet)}"
        )

        if not jobs_to_process_for_sheet:
            print("[INFO] No new jobs to add to the sheet.")
            return

        print(f"[INFO] Appending {len(jobs_to_process_for_sheet)} new jobs to the sheet...")
        rows_to_append = [
            [job.get(header, "") for header in SHEET_HEADERS]
            for job in jobs_to_process_for_sheet
        ]
        sheets_manager.append_rows(rows_to_append)
        print(
            f"\n[SUCCESS] Successfully appended {len(jobs_to_process_for_sheet)} new jobs to the Google Sheet."
        )

        if jobs_to_process_for_sheet:
            print(
                "\n[INFO] Starting Match Score calculation for newly added jobs..."
            )
            match_calculator = MatchScoreCalculator()
            match_calculator.run(max_workers=15)

    except Exception as e:
        print(f"\n[FATAL ERROR] The scraping process failed: {e}")