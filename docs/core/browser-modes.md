# Browser Modes for LinkedIn Scraper

The LinkedIn scraper supports three browser modes, each with its own advantages and use cases. Mode selection and CLI argument handling are implemented in:
- [jobapp/search/main.py](../jobapp/search/main.py)
- [jobapp/search/linkedin_scraper.py](../jobapp/search/linkedin_scraper.py)

## Available Browser Modes

### 1. Patchright Mode (Default)
- **Usage**: `--browser-mode=patchright` or default behavior
- **Description**: Uses Patchright's enhanced Chromium with built-in stealth capabilities
- **Advantages**: 
  - Best stealth detection evasion
  - Optimized for web scraping
  - Most reliable for automated tasks
- **Requirements**: Requires saved authentication state file
- **Best for**: Automated scraping, avoiding detection

### 2. Playwright Mode
- **Usage**: `--browser-mode=playwright`
- **Description**: Uses native Playwright Chromium with manual stealth configurations
- **Advantages**:
  - Pure Playwright implementation
  - Good performance
  - Standard Chromium behavior
- **Requirements**: Requires saved authentication state file
- **Best for**: Standard automation tasks, debugging

### 3. System Chrome Mode
- **Usage**: `--browser-mode=system_chrome`
- **Description**: Connects to your existing Chrome browser installation
- **Advantages**:
  - Uses your actual Chrome profile with all extensions and settings
  - No need for separate authentication
  - Full browser functionality
- **Requirements**: 
  - Google Chrome installed on system
  - Existing LinkedIn login in your Chrome profile
- **Best for**: Manual-assisted scraping, using existing sessions

## Usage Examples

```bash
# Use default Patchright mode (most stealthy)
python -m jobapp.search.main "Software Engineer"

# Use native Playwright mode
python -m jobapp.search.main "Data Scientist" --browser-mode=playwright

# Use system Chrome (requires existing login)
python -m jobapp.search.main "Product Manager" --browser-mode=system_chrome

# Use system Chrome with custom paths
python -m jobapp.search.main "DevOps Engineer" --browser-mode=system_chrome \
  --chrome-path="/usr/bin/google-chrome" \
  --chrome-profile="~/.config/google-chrome"
```

## Migration and Backward Compatibility

- The previous `browser-use` library and related flags have been **fully removed**.
- The `--use-system-chrome` flag is still supported but deprecated; it maps to `--browser-mode=system_chrome` automatically (see [main.py](../jobapp/search/main.py)).

## Troubleshooting

### Authentication Issues
- For Patchright/Playwright modes: Ensure you have a valid authentication state file
- For System Chrome mode: Ensure you're logged into LinkedIn in your Chrome browser

### Browser Detection
- If Patchright mode gets detected, try System Chrome mode
- If Playwright mode gets detected, try Patchright mode
- System Chrome mode is least likely to be detected as it uses a real browser profile

### Performance
- Patchright mode: Best for stealth, moderate performance
- Playwright mode: Good performance, standard detection profile  
- System Chrome mode: Variable performance, depends on extensions and profile size

---

See also:
- [jobapp/search/main.py](../jobapp/search/main.py)
- [jobapp/search/linkedin_scraper.py](../jobapp/search/linkedin_scraper.py) 