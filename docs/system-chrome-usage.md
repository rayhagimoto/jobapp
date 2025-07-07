# Using System Chrome for LinkedIn Scraping

The LinkedIn scraper now supports using your system's Chrome browser instead of Patchright. This has several advantages:

- Uses your existing LinkedIn login session
- No need for auth files or manual login scripts
- More stable connection (less likely to be detected as a bot)
- Uses your real Chrome profile with all cookies and settings

## Prerequisites

1. Google Chrome must be installed at `/usr/bin/google-chrome-stable`
2. You must be logged into LinkedIn in your Chrome browser
3. Chrome must be started with remote debugging enabled

## Quick Start

### Option 1: Using the Helper Script (Recommended)

1. **Start Chrome with debugging enabled:**
   ```bash
   ./scripts/start_chrome_debug.sh
   ```
   This will:
   - Close any existing Chrome processes
   - Start Chrome with remote debugging on port 9222
   - Use your existing Chrome profile
   - Display helpful status messages

2. **Navigate to LinkedIn in the opened Chrome window and ensure you're logged in**

3. **Run the scraper:**
   ```bash
   jobapp search "Data Scientist" --use-system-chrome --max-pages=3
   ```

### Option 2: Manual Chrome Startup

1. **Close any existing Chrome instances:**
   ```bash
   pkill -f "google-chrome-stable"
   ```

2. **Start Chrome with remote debugging:**
   ```bash
   google-chrome-stable \
       --remote-debugging-port=9222 \
       --user-data-dir="$HOME/.config/google-chrome" &
   ```

3. **Run the scraper:**
   ```bash
   jobapp search "Job Title" --use-system-chrome
   ```

## Command Examples

```bash
# Basic usage with system Chrome
jobapp search "Software Engineer" --use-system-chrome

# Limit to 2 pages
jobapp search "Product Manager" --use-system-chrome --max-pages=2

# With verbose logging
jobapp search "Data Analyst" --use-system-chrome --verbose

# Compare with Patchright (default behavior)
jobapp search "UX Designer"  # Uses Patchright + auth files
```

## Troubleshooting

### Chrome Connection Failed
If you see "Failed to connect to Chrome", ensure:
- Chrome is running with `--remote-debugging-port=9222`
- No firewall is blocking port 9222
- Chrome started successfully (check for error messages)

### LinkedIn Not Logged In
- Navigate to LinkedIn in the Chrome window that opened
- Log in manually if needed
- The scraper will use your existing session

### Multiple Chrome Instances
- Close all Chrome windows before running the helper script
- The script will automatically kill existing Chrome processes

## Stopping Chrome Debug Mode

After scraping, you can:
1. Close Chrome normally (it will return to normal mode on next start)
2. Or kill the debug process: `pkill -f "remote-debugging-port=9222"`

## Comparison: System Chrome vs Patchright

| Feature | System Chrome | Patchright |
|---------|---------------|------------|
| Setup | Start Chrome with debug flag | Requires auth files |
| Login | Uses existing session | Manual login script needed |
| Stealth | Uses real browser profile | Advanced stealth features |
| Stability | Very stable | May have compatibility issues |
| Dependencies | Standard Playwright | Patchright + BrowserUse |

## Security Note

When Chrome runs with `--remote-debugging-port=9222`, it allows local connections to control the browser. This is safe for local development but should not be used on shared or public machines. 