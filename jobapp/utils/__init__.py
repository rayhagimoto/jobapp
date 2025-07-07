import re
from datetime import datetime, timedelta

def clean_text(text: str) -> str:
    """
    Removes extra whitespace and non-alphanumeric characters for consistent processing.
    """
    if not isinstance(text, str):
        return ""
    # Remove non-alphanumeric except spaces
    text = re.sub(r'[^\w\s]', '', text)
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def normalize_string(text: str) -> str:
    """
    Converts to lowercase and removes punctuation for comparison.
    """
    if not isinstance(text, str):
        return ""
    text = text.lower()
    # Remove punctuation
    text = re.sub(r'[^a-z0-9\s]', '', text)
    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_linkedin_date(date_string: str) -> str:
    """
    Converts LinkedIn-style date strings (e.g., '3 days ago', '1 month ago', 'more than 30 days ago') to YYYY-MM-DD format.
    Returns empty string if unparseable.
    """
    if not isinstance(date_string, str):
        return ""
    date_string = date_string.lower().strip()
    today = datetime.today()
    # Patterns: 'X days ago', 'X months ago', 'more than 30 days ago', etc.
    day_match = re.match(r'(\d+)\s+day[s]?\s+ago', date_string)
    month_match = re.match(r'(\d+)\s+month[s]?\s+ago', date_string)
    more_than_30 = re.match(r'more than 30 day[s]? ago', date_string)
    if day_match:
        days = int(day_match.group(1))
        dt = today - timedelta(days=days)
        return dt.strftime('%Y-%m-%d')
    elif month_match:
        months = int(month_match.group(1))
        # Approximate a month as 30 days
        dt = today - timedelta(days=months*30)
        return dt.strftime('%Y-%m-%d')
    elif more_than_30:
        dt = today - timedelta(days=31)
        return dt.strftime('%Y-%m-%d')
    # Try to parse as a date
    try:
        dt = datetime.strptime(date_string, '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    except Exception:
        pass
    return ""
