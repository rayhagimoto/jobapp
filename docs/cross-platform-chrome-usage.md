# Cross-Platform Chrome Manager for LinkedIn Scraping

The JobApp package now includes a cross-platform Chrome manager that works on **Windows**, **macOS**, and **Linux**. This allows users to specify their Chrome installation and use their existing LinkedIn login session across all platforms.

## Features

✅ **Cross-Platform Support**: Works on Windows, macOS, and Linux  
✅ **Auto-Detection**: Automatically finds Chrome and profile directories  
✅ **Custom Paths**: Users can specify exact paths to Chrome executable and profile  
✅ **Session Preservation**: Copies your existing Chrome profile to preserve LinkedIn login  
✅ **Clean Management**: Properly starts, manages, and cleans up Chrome processes  

## Quick Start

### 1. Test Chrome Detection

First, verify that the Chrome manager can detect your Chrome installation:

```bash
python scripts/test_chrome_manager.py --detection-only
```

### 2. Test Chrome Startup (Optional)

Test the full Chrome startup process:

```bash
python scripts/test_chrome_manager.py
```

### 3. Run the Scraper

```bash
jobapp search "Software Engineer" --use-system-chrome --max-pages=3
```

## Platform-Specific Usage

### Linux

**Auto-detection** (recommended):
```bash
jobapp search "Data Scientist" --use-system-chrome
```

**Custom Chrome path**:
```bash
jobapp search "Product Manager" --use-system-chrome --chrome-path=/usr/bin/google-chrome-stable
```

**Custom profile path**:
```bash
jobapp search "UX Designer" --use-system-chrome --chrome-profile=~/.config/google-chrome
```

### macOS

**Auto-detection** (recommended):
```bash
jobapp search "Data Scientist" --use-system-chrome
```

**Custom Chrome path**:
```bash
jobapp search "Product Manager" --use-system-chrome --chrome-path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
```

**Custom profile path**:
```bash
jobapp search "UX Designer" --use-system-chrome --chrome-profile="~/Library/Application Support/Google/Chrome"
```

### Windows

**Auto-detection** (recommended):
```bash
jobapp search "Data Scientist" --use-system-chrome
```

**Custom Chrome path**:
```bash
jobapp search "Product Manager" --use-system-chrome --chrome-path="C:\Program Files\Google\Chrome\Application\chrome.exe"
```

**Custom profile path**:
```bash
jobapp search "UX Designer" --use-system-chrome --chrome-profile="%LOCALAPPDATA%\Google\Chrome\User Data"
```

## Command Reference

### Core Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `--use-system-chrome` | Enable system Chrome mode | Required for Chrome manager |
| `--chrome-path` | Custom Chrome executable path | `/usr/bin/google-chrome-stable` |
| `--chrome-profile` | Custom Chrome profile directory | `~/.config/google-chrome` |
| `--max-pages` | Limit scraping pages | `--max-pages=5` |

### Complete Example

```bash
jobapp search "Machine Learning Engineer" \
  --use-system-chrome \
  --chrome-path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --chrome-profile="~/Library/Application Support/Google/Chrome" \
  --max-pages=3
```

## Default Chrome Locations

The Chrome manager automatically detects Chrome in these locations:

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

1. **Detection**: The Chrome manager detects your platform and searches for Chrome in standard locations
2. **Profile Copy**: Creates a temporary debug profile directory and copies your existing Chrome session data
3. **Chrome Startup**: Starts Chrome with remote debugging enabled on port 9222
4. **Connection**: The scraper connects to Chrome via Chrome DevTools Protocol (CDP)
5. **Scraping**: Uses your existing LinkedIn login session for job scraping
6. **Cleanup**: Stops Chrome and cleans up temporary files when done

## Troubleshooting

### Chrome Not Found
```
❌ Chrome not found
```
**Solution**: Install Google Chrome or specify the path:
```bash
jobapp search "Job Title" --use-system-chrome --chrome-path="/path/to/chrome"
```

### Profile Not Found
```
❌ Chrome profile not found
```
**Solution**: Specify your Chrome profile directory:
```bash
jobapp search "Job Title" --use-system-chrome --chrome-profile="/path/to/profile"
```

### Remote Debugging Failed
```
[ERROR] Chrome remote debugging not responding
```
**Solutions**:
1. Close all Chrome windows and try again
2. Check if another process is using port 9222
3. Try a different debug port: `--port=9223` (in test script)

### LinkedIn Not Logged In
- The Chrome manager copies your existing profile, so you should remain logged in
- If not logged in, manually log into LinkedIn in the opened Chrome window
- The scraper will wait for you to navigate to the job search page

## Distribution Considerations

For distributing the package to users:

### ✅ Advantages
- **No manual Chrome setup required** - Users just install Chrome normally
- **Preserves existing sessions** - Uses their current LinkedIn login
- **Cross-platform compatibility** - Works on Windows, macOS, Linux
- **User-friendly** - Auto-detects Chrome or accepts custom paths
- **Clean operation** - Properly manages Chrome processes and cleanup

### ✅ User Requirements
- Google Chrome installed on their system
- Existing LinkedIn account (logged in via their regular Chrome)
- Python environment with jobapp package installed

### ✅ Simple User Workflow
1. Install Chrome (if not already installed)
2. Log into LinkedIn in their regular Chrome browser
3. Install jobapp package
4. Run: `jobapp search "Job Title" --use-system-chrome`

This approach provides the best user experience for cross-platform distribution while maintaining reliability and ease of use.

## Security Notes

- **Temporary Profile**: Chrome manager creates a temporary copy of your profile for debugging
- **Local Connection**: Remote debugging only accepts connections from localhost
- **Session Isolation**: Debug session is separate from your regular Chrome usage
- **Automatic Cleanup**: Temporary files are automatically cleaned up after scraping

## Comparison: Chrome Manager vs Patchright

| Feature | Chrome Manager | Patchright |
|---------|----------------|------------|
| **Cross-Platform** | ✅ Windows, macOS, Linux | ⚠️ Limited compatibility |
| **User Setup** | ✅ Minimal (just install Chrome) | ❌ Complex (auth files, manual login) |
| **Login Session** | ✅ Uses existing login | ❌ Requires separate login process |
| **Reliability** | ✅ Uses real Chrome browser | ⚠️ May have detection issues |
| **Dependencies** | ✅ Standard Playwright | ❌ Requires Patchright + BrowserUse |
| **Distribution** | ✅ Easy for end users | ❌ Complex setup for users |

The Chrome manager approach is recommended for distribution to end users due to its simplicity and cross-platform reliability. 