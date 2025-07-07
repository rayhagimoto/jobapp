# Cross-Platform Chrome Manager for LinkedIn Scraping

The JobApp package includes a cross-platform Chrome manager implemented in [jobapp/core/chrome_manager.py](../jobapp/core/chrome_manager.py), with CLI integration in [jobapp/search/main.py](../jobapp/search/main.py) and browser orchestration in [jobapp/search/linkedin_scraper.py](../jobapp/search/linkedin_scraper.py). This system works on **Windows**, **macOS**, and **Linux** and allows you to use your existing Chrome installation and LinkedIn login session for scraping.

## Features

✅ **Cross-Platform Support**: Works on Windows, macOS, and Linux  
✅ **Auto-Detection**: Automatically finds Chrome and profile directories  
✅ **Custom Paths**: Users can specify exact paths to Chrome executable and profile  
✅ **Session Preservation**: Copies your existing Chrome profile to preserve LinkedIn login  
✅ **Clean Management**: Properly starts, manages, and cleans up Chrome processes  

## Quick Start

### 1. Test Chrome Detection (Advanced)

If you want to test Chrome detection logic directly, you can use the ChromeManager class in a Python shell:

```python
from jobapp.core.chrome_manager import ChromeManager
cm = ChromeManager()
print(cm.find_chrome_executable())
print(cm.find_chrome_profile_dir())
```

### 2. Run the Scraper

```bash
jobapp search "Software Engineer" --browser-mode=system_chrome --max-pages=3
```

- The `--use-system-chrome` flag is **deprecated** but still supported for backward compatibility. Prefer `--browser-mode=system_chrome`.

## Platform-Specific Usage

### Linux
```bash
jobapp search "Data Scientist" --browser-mode=system_chrome
jobapp search "Product Manager" --browser-mode=system_chrome --chrome-path=/usr/bin/google-chrome-stable
jobapp search "UX Designer" --browser-mode=system_chrome --chrome-profile=~/.config/google-chrome
```

### macOS
```bash
jobapp search "Data Scientist" --browser-mode=system_chrome
jobapp search "Product Manager" --browser-mode=system_chrome --chrome-path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
jobapp search "UX Designer" --browser-mode=system_chrome --chrome-profile="~/Library/Application Support/Google/Chrome"
```

### Windows
```bash
jobapp search "Data Scientist" --browser-mode=system_chrome
jobapp search "Product Manager" --browser-mode=system_chrome --chrome-path="C:\Program Files\Google\Chrome\Application\chrome.exe"
jobapp search "UX Designer" --browser-mode=system_chrome --chrome-profile="%LOCALAPPDATA%\Google\Chrome\User Data"
```

## Command Reference

| Argument | Description | Example |
|----------|-------------|---------|
| `--browser-mode=system_chrome` | Use system Chrome browser | Required for Chrome manager |
| `--chrome-path` | Custom Chrome executable path | `/usr/bin/google-chrome-stable` |
| `--chrome-profile` | Custom Chrome profile directory | `~/.config/google-chrome` |
| `--max-pages` | Limit scraping pages | `--max-pages=5` |
| `--use-system-chrome` | [DEPRECATED] Same as `--browser-mode=system_chrome` | |

## Default Chrome Locations

The Chrome manager ([jobapp/core/chrome_manager.py](../jobapp/core/chrome_manager.py)) auto-detects Chrome in these locations:

### Linux
- `google-chrome-stable` (command)
- `google-chrome` (command)
- `/usr/bin/google-chrome-stable`
- `/usr/bin/google-chrome`
- `/opt/google/chrome/chrome`
- `/snap/bin/chromium`

**Profile directories:**
- `~/.config/google-chrome`
- `~/.config/chromium`
- `~/snap/chromium/common/chromium`

### macOS
- `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
- `/Applications/Chromium.app/Contents/MacOS/Chromium`
- `/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary`

**Profile directories:**
- `~/Library/Application Support/Google/Chrome`
- `~/Library/Application Support/Chromium`

### Windows
- `C:\Program Files\Google\Chrome\Application\chrome.exe`
- `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`
- `%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe`
- `%LOCALAPPDATA%\Chromium\Application\chrome.exe`

**Profile directories:**
- `%LOCALAPPDATA%\Google\Chrome\User Data`
- `%LOCALAPPDATA%\Chromium\User Data`

## How It Works

1. **Detection**: The Chrome manager detects your platform and searches for Chrome in standard locations.
2. **Profile Copy**: Creates a temporary debug profile directory and copies your existing Chrome session data (see [jobapp/core/chrome_manager.py](../jobapp/core/chrome_manager.py)).
3. **Chrome Startup**: Starts Chrome with remote debugging enabled on port 9222.
4. **Connection**: The scraper ([jobapp/search/linkedin_scraper.py](../jobapp/search/linkedin_scraper.py)) connects to Chrome via Chrome DevTools Protocol (CDP).
5. **Scraping**: Uses your existing LinkedIn login session for job scraping.
6. **Cleanup**: Stops Chrome and cleans up temporary files when done.

## Troubleshooting

### Chrome Not Found
```
❌ Chrome not found
```
**Solution**: Install Google Chrome or specify the path:
```bash
jobapp search "Job Title" --browser-mode=system_chrome --chrome-path="/path/to/chrome"
```

### Profile Not Found
```
❌ Chrome profile not found
```
**Solution**: Specify your Chrome profile directory:
```bash
jobapp search "Job Title" --browser-mode=system_chrome --chrome-profile="/path/to/profile"
```

### Remote Debugging Failed
```
[ERROR] Chrome remote debugging not responding
```
**Solutions**:
1. Close all Chrome windows and try again
2. Check if another process is using port 9222

### LinkedIn Not Logged In
- The Chrome manager copies your existing profile, so you should remain logged in
- If not logged in, manually log into LinkedIn in the opened Chrome window
- The scraper will wait for you to navigate to the job search page

## Distribution Considerations

- **No manual Chrome setup required** - Users just install Chrome normally
- **Preserves existing sessions** - Uses their current LinkedIn login
- **Cross-platform compatibility** - Works on Windows, macOS, Linux
- **User-friendly** - Auto-detects Chrome or accepts custom paths
- **Clean operation** - Properly manages Chrome processes and cleanup 