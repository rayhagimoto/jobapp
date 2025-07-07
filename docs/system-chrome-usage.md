# Using System Chrome for LinkedIn Scraping

The LinkedIn scraper supports using your system's Chrome browser, managed automatically by the [ChromeManager](../jobapp/core/chrome_manager.py) class. CLI integration is in [jobapp/search/main.py](../jobapp/search/main.py), and browser orchestration is in [jobapp/search/linkedin_scraper.py](../jobapp/search/linkedin_scraper.py).

**Advantages:**
- Uses your existing LinkedIn login session
- No need for auth files or manual login scripts
- More stable connection (less likely to be detected as a bot)
- Uses your real Chrome profile with all cookies and settings

## Prerequisites

1. Google Chrome must be installed (auto-detected by ChromeManager)
2. You must be logged into LinkedIn in your Chrome browser (the manager copies your profile)

## Quick Start

**You do NOT need to manually start Chrome with remote debugging.**
The ChromeManager will:
- Detect your Chrome installation
- Copy your profile (or use the specified one)
- Start Chrome with remote debugging enabled on port 9222
- Clean up after scraping

### Run the Scraper

```bash
jobapp search "Data Scientist" --browser-mode=system_chrome --max-pages=3
```

- The `--use-system-chrome` flag is **deprecated** but still supported for backward compatibility. Prefer `--browser-mode=system_chrome`.

## Command Examples

```bash
# Basic usage with system Chrome
jobapp search "Software Engineer" --browser-mode=system_chrome

# Limit to 2 pages
jobapp search "Product Manager" --browser-mode=system_chrome --max-pages=2

# With verbose logging
jobapp search "Data Analyst" --browser-mode=system_chrome --verbose

# Compare with Patchright (default behavior)
jobapp search "UX Designer"  # Uses Patchright + auth files
```

## Troubleshooting

### Chrome Connection Failed
If you see "Failed to connect to Chrome", ensure:
- Chrome is installed and not blocked by a firewall
- No other process is using port 9222
- Try closing all Chrome windows before running the scraper

### LinkedIn Not Logged In
- The ChromeManager copies your existing profile, so you should remain logged in
- If not logged in, manually log into LinkedIn in the opened Chrome window
- The scraper will wait for you to navigate to the job search page

### Multiple Chrome Instances
- Close all Chrome windows before running the scraper if you encounter issues

## Stopping Chrome Debug Mode

The ChromeManager will automatically stop Chrome and clean up after scraping. If you need to manually stop Chrome:
1. Close Chrome normally
2. Or kill the debug process: `pkill -f "chrome-debug-profile"`

## Comparison: System Chrome vs Patchright

| Feature | System Chrome | Patchright |
|---------|---------------|------------|
| Setup | Automatic (ChromeManager) | Requires auth files |
| Login | Uses existing session | Manual login script needed |
| Stealth | Uses real browser profile | Advanced stealth features |
| Stability | Very stable | May have compatibility issues |
| Dependencies | Standard Playwright | Patchright + BrowserUse |

## Security Note

When Chrome runs with `--remote-debugging-port=9222`, it allows local connections to control the browser. This is safe for local development but should not be used on shared or public machines. 