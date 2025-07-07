"""
Manual LinkedIn login for JobApp with browser selection.

Usage:
    jobapp search login [--browser-mode=patchright|playwright|system_chrome] [--chrome-path=...] [--chrome-profile=...]

This script launches the selected browser for manual login,
then saves the session state to the path determined by ConfigManager.
"""
import asyncio
import os
from jobapp.core.config_manager import ConfigManager

# Import both Playwright and Patchright
from playwright.async_api import async_playwright
try:
    from patchright.async_api import async_playwright as async_patchright
except ImportError:
    async_patchright = None

async def manual_linkedin_login(browser_mode="patchright", chrome_path=None, chrome_profile=None):
    config = ConfigManager()
    auth_state_path = config.get_linkedin_auth_state_path()

    # Select browser engine
    if browser_mode == "patchright":
        if not async_patchright:
            print("[ERROR] Patchright is not installed. Please install it with 'pip install patchright' and try again.")
            return
        print("[INFO] Using Patchright Chromium for manual login...")
        playwright = await async_patchright().start()
        browser = await playwright.chromium.launch(headless=False)
    elif browser_mode == "playwright":
        print("[INFO] Using Playwright Chromium for manual login...")
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
    elif browser_mode == "system_chrome":
        print("[ERROR] System Chrome mode is not supported for manual login. Please use 'patchright' or 'playwright'.")
        return
    else:
        print(f"[ERROR] Unknown browser mode: {browser_mode}")
        return

    context = await browser.new_context(viewport={"width": 1920, "height": 1080})
    page = await context.new_page()

    print("[INFO] Navigating to https://www.linkedin.com/login ...")
    await page.goto("https://www.linkedin.com/login")

    print("\n[ACTION REQUIRED] Please log in to LinkedIn in the opened browser window.")
    print("    - After successful login, ensure you are on your LinkedIn homepage.")
    print("    - Then, press ENTER here in the terminal to save the session state and close the browser.")
    input()  # Wait for user confirmation

    os.makedirs(os.path.dirname(auth_state_path), exist_ok=True)
    await context.storage_state(path=auth_state_path)
    print(f"\n[INFO] Auth state saved to {auth_state_path}")

    await context.close()
    await browser.close()
    await playwright.stop()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Manual LinkedIn login for JobApp with browser selection.")
    parser.add_argument("--browser-mode", type=str, choices=["patchright", "playwright", "system_chrome"], default="patchright", help="Browser mode to use for login.")
    parser.add_argument("--chrome-path", type=str, default=None, help="Custom path to Chrome executable (not used in manual login).")
    parser.add_argument("--chrome-profile", type=str, default=None, help="Custom path to Chrome profile directory (not used in manual login).")
    args = parser.parse_args()
    asyncio.run(manual_linkedin_login(browser_mode=args.browser_mode, chrome_path=args.chrome_path, chrome_profile=args.chrome_profile)) 