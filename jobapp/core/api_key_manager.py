from typing import Optional, Set, Dict
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from jobapp.core.logger import get_logger

class APIKeyManager:
    """
    Manages API key rotation for rate-limited services.
    Keeps track of failed keys and quota-exhausted keys with daily reset tracking.
    """
    
    # Class-level tracking to ensure quota reset only happens once per session
    _session_reset_checked = {}  # provider -> date_checked
    
    def __init__(self, primary_key_env: str, backup_key_envs: list[str], state_file: Optional[str] = None, config_manager=None):
        """
        Initialize the key manager.
        
        Args:
            primary_key_env: Environment variable name for the primary API key
            backup_key_envs: List of environment variable names for backup API keys
            state_file: Path to store quota state (defaults to using ConfigManager's cache path)
            config_manager: ConfigManager instance for path resolution
        """
        self.logger = get_logger(__name__)
        self.primary_key_env = primary_key_env
        self.backup_key_envs = backup_key_envs
        self.current_key_env = primary_key_env
        self.failed_keys: Set[str] = set()
        
        # Set up state file for persistent quota tracking using ConfigManager
        if state_file is None:
            if config_manager is None:
                from .config_manager import ConfigManager
                config_manager = ConfigManager()
            cache_dir = Path(config_manager.get_cache_path())
            cache_dir.mkdir(parents=True, exist_ok=True)
            self.state_file = cache_dir / "api_key_state.json"
        else:
            self.state_file = Path(state_file)
        
        # Load quota state from file
        self.quota_exhausted_keys: Dict[str, str] = {}  # key_env -> date_exhausted (YYYY-MM-DD)
        self._load_quota_state()
        
        # Determine provider name for session tracking
        self.provider_name = self._get_provider_name_from_key(primary_key_env)
        
        # Only reset expired quotas once per session when first needed
        # This will be called lazily in get_next_key_env() or when explicitly requested
        
        self.logger.info(f"Initialized APIKeyManager with {len(backup_key_envs)} backup keys available")
        if self.quota_exhausted_keys:
            self.logger.info(f"Loaded {len(self.quota_exhausted_keys)} quota-exhausted keys from state file")

    def _get_provider_name_from_key(self, key_env: str) -> str:
        """Extract provider name from key environment variable name."""
        key_lower = key_env.lower()
        if 'google' in key_lower:
            return 'google'
        elif 'anthropic' in key_lower:
            return 'anthropic'
        elif 'openai' in key_lower:
            return 'openai'
        elif 'openrouter' in key_lower:
            return 'openrouter'
        else:
            return 'unknown'

    def _should_check_quota_reset(self) -> bool:
        """Check if we should perform quota reset for this session."""
        current_date = self._get_current_date_for_provider()
        last_checked = self._session_reset_checked.get(self.provider_name)
        
        # Check if we haven't checked today for this provider
        return last_checked != current_date

    def _mark_quota_reset_checked(self) -> None:
        """Mark that we've checked quota reset for this provider today."""
        current_date = self._get_current_date_for_provider()
        self._session_reset_checked[self.provider_name] = current_date

    def _get_pacific_date(self) -> str:
        """Get current date in Pacific timezone (YYYY-MM-DD format) for Google APIs."""
        # Pacific timezone (handles both PST and PDT automatically)
        pacific_tz = timezone(timedelta(hours=-8))  # PST base
        now_pacific = datetime.now(pacific_tz)
        
        # Adjust for daylight saving time (rough approximation)
        # DST typically runs from second Sunday in March to first Sunday in November
        if now_pacific.month >= 3 and now_pacific.month <= 10:
            # Likely daylight saving time, adjust to PDT (-7 hours)
            pacific_tz = timezone(timedelta(hours=-7))
            now_pacific = datetime.now(pacific_tz)
        
        return now_pacific.strftime("%Y-%m-%d")

    def _get_utc_date(self) -> str:
        """Get current date in UTC timezone (YYYY-MM-DD format) for OpenRouter APIs."""
        now_utc = datetime.now(timezone.utc)
        return now_utc.strftime("%Y-%m-%d")

    def _get_current_date_for_provider(self) -> str:
        """Get current date in the appropriate timezone for the provider."""
        if self.provider_name == 'google':
            return self._get_pacific_date()
        elif self.provider_name in ['openrouter', 'openai', 'anthropic']:
            return self._get_utc_date()
        else:
            # Default to UTC for unknown providers
            return self._get_utc_date()

    def _load_quota_state(self) -> None:
        """Load quota state from persistent storage."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.quota_exhausted_keys = data.get('quota_exhausted_keys', {})
        except Exception as e:
            self.logger.warning(f"Failed to load quota state from {self.state_file}: {e}")
            self.quota_exhausted_keys = {}

    def _save_quota_state(self) -> None:
        """Save quota state to persistent storage."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'quota_exhausted_keys': self.quota_exhausted_keys,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save quota state to {self.state_file}: {e}")

    def _reset_expired_quotas(self) -> None:
        """Reset quota status for keys whose daily limit should have reset."""
        current_date = self._get_current_date_for_provider()
        expired_keys = []
        
        for key_env, exhausted_date in self.quota_exhausted_keys.items():
            if exhausted_date < current_date:
                expired_keys.append(key_env)
        
        for key_env in expired_keys:
            del self.quota_exhausted_keys[key_env]
            self.logger.info(f"Reset quota status for {key_env} (was exhausted on {self.quota_exhausted_keys.get(key_env, 'unknown date')})")
        
        if expired_keys:
            self._save_quota_state()
            self.logger.info(f"Session quota reset completed for {self.provider_name} - cleared {len(expired_keys)} expired keys")

    def _ensure_quota_reset_checked(self) -> None:
        """Ensure quota reset has been checked once for this session."""
        if self._should_check_quota_reset():
            self.logger.debug(f"Performing daily quota reset check for {self.provider_name}")
            self._reset_expired_quotas()
            self._mark_quota_reset_checked()
    
    def is_rate_limit_error(self, error: Exception) -> bool:
        """
        Check if an error is a rate limit error (RPM - requests per minute).
        These are temporary and should be retried after a cooldown.
        """
        error_msg = str(error).lower()
        
        # Generic rate limiting indicators
        generic_rpm_indicators = [
            'rate limit exceeded',
            'too many requests',
            'requests per minute',
            'rpm',
            '429' # Some 429s are RPM, not quota
        ]
        
        # OpenRouter specific RPM indicators
        openrouter_rpm_indicators = [
            'free-models-per-min',
            'requests-per-minute',
            'x-ratelimit-limit',
            'x-ratelimit-remaining'
        ]
        
        # OpenAI specific RPM indicators
        openai_rpm_indicators = [
            'rate limit reached',
            'ratelimiterror',
            'x-ratelimit-remaining-requests',
            'x-ratelimit-remaining-tokens',
            'tokens per minute',
            'tpm'
        ]
        
        # Anthropic specific RPM indicators
        anthropic_rpm_indicators = [
            'anthropic-ratelimit-requests-remaining',
            'anthropic-ratelimit-tokens-remaining',
            'retry-after',
            'input tokens per minute',
            'output tokens per minute',
            'itpm',
            'otpm'
        ]
        
        all_rpm_indicators = (generic_rpm_indicators + openrouter_rpm_indicators + 
                             openai_rpm_indicators + anthropic_rpm_indicators)
        
        # Only consider it an RPM error if it's NOT a daily quota error
        if any(indicator in error_msg for indicator in all_rpm_indicators):
            return not self.is_quota_exhausted_error(error)
            
        return False

    def is_quota_exhausted_error(self, error: Exception) -> bool:
        """
        Check if an error specifically indicates daily quota exhaustion (RPD - requests per day).
        These persist until midnight PT/UTC and require key rotation.
        """
        error_msg = str(error).lower()
        
        # Google/Gemini specific daily quota exhaustion indicators
        google_quota_indicators = [
            'daily limit exceeded',
            'quota exceeded',
            'resourceexhausted',
            'generativelanguage.googleapis.com/generate_content_free_tier_requests',
            'generaterequestsperdayperprojectpermodel-freetier',
            'requests per day',
            'rpd',
            'daily quota'
        ]
        
        # OpenRouter specific daily quota indicators
        openrouter_quota_indicators = [
            'free-models-per-day',
            'requests-per-day',
            'daily limit',
            'credit limit',
            'negative credit balance',
            '402'  # OpenRouter returns 402 for insufficient credits
        ]
        
        # OpenAI specific quota indicators
        openai_quota_indicators = [
            'insufficient_quota',
            'you exceeded your current quota',
            'please check your plan and billing details',
            'quota exceeded',
            'billing details'
        ]
        
        # Anthropic specific quota indicators
        anthropic_quota_indicators = [
            'monthly spend limit',
            'spend limit',
            'credit limit exceeded',
            'monthly usage limit',
            'organization limit exceeded'
        ]
        
        all_quota_indicators = (google_quota_indicators + openrouter_quota_indicators + 
                               openai_quota_indicators + anthropic_quota_indicators)
        
        return any(indicator in error_msg for indicator in all_quota_indicators)

    def _get_openrouter_reset_time(self, error: Exception) -> Optional[datetime]:
        """
        Extract reset time from OpenRouter error message if available.
        OpenRouter includes X-RateLimit-Reset as Unix timestamp in milliseconds.
        """
        error_msg = str(error)
        
        # Look for X-RateLimit-Reset timestamp in error message
        import re
        reset_pattern = r"'X-RateLimit-Reset':\s*'(\d+)'"
        match = re.search(reset_pattern, error_msg)
        
        if match:
            try:
                # OpenRouter timestamps are in milliseconds
                timestamp_ms = int(match.group(1))
                timestamp_s = timestamp_ms / 1000
                reset_time = datetime.fromtimestamp(timestamp_s, tz=timezone.utc)
                return reset_time
            except (ValueError, OSError):
                pass
        
        return None

    def _get_openrouter_date_from_reset(self, reset_time: datetime) -> str:
        """
        Convert OpenRouter reset time to date string for quota tracking.
        OpenRouter likely resets at UTC midnight.
        """
        # Convert to UTC if not already
        if reset_time.tzinfo is None:
            reset_time = reset_time.replace(tzinfo=timezone.utc)
        elif reset_time.tzinfo != timezone.utc:
            reset_time = reset_time.astimezone(timezone.utc)
        
        # For daily quotas, the reset happens at the start of the next day
        # So if reset is at 2024-01-02 00:00:00 UTC, the quota was for 2024-01-01
        quota_date = (reset_time - timedelta(days=1)).strftime("%Y-%m-%d")
        return quota_date
    
    def mark_key_failed(self, key_env: str) -> None:
        """Mark a key as failed (for non-quota issues) and log it."""
        self.failed_keys.add(key_env)
        self.logger.warning(f"Marked key {key_env} as failed. Total failed keys: {len(self.failed_keys)}")
    
    def mark_key_quota_exhausted(self, key_env: str, error: Exception = None) -> None:
        """Mark a key as quota exhausted for the current day."""
        # Try to get more precise date from OpenRouter error if available
        if self.provider_name == 'openrouter' and error:
            reset_time = self._get_openrouter_reset_time(error)
            if reset_time:
                exhausted_date = self._get_openrouter_date_from_reset(reset_time)
                self.logger.info(f"Using OpenRouter reset time to determine quota date: {exhausted_date}")
            else:
                exhausted_date = self._get_current_date_for_provider()
        else:
            exhausted_date = self._get_current_date_for_provider()
        
        self.quota_exhausted_keys[key_env] = exhausted_date
        self._save_quota_state()
        
        timezone_info = "Pacific Time" if self.provider_name == 'google' else "UTC"
        self.logger.warning(f"Marked key {key_env} as quota exhausted for {exhausted_date}. "
                          f"Will reset at midnight {timezone_info}.")

    def handle_api_error(self, error: Exception, key_env: str) -> str:
        """
        Handle an API error by marking the key appropriately.
        
        Args:
            error: The exception that occurred
            key_env: The environment variable name of the key that failed
            
        Returns:
            'quota_exhausted', 'rate_limited', or 'failed' indicating the error type
        """
        if self.is_quota_exhausted_error(error):
            self.mark_key_quota_exhausted(key_env, error)
            return 'quota_exhausted'
        elif self.is_rate_limit_error(error):
            # For temporary rate limits, don't mark as failed permanently
            self.logger.warning(f"Rate limit hit for {key_env}, will retry after cooldown")
            return 'rate_limited'
        else:
            self.mark_key_failed(key_env)
            return 'failed'

    def is_key_available(self, key_env: str) -> bool:
        """Check if a key is available (not failed and not quota exhausted)."""
        return (key_env not in self.failed_keys and 
                key_env not in self.quota_exhausted_keys)

    def get_next_key_env(self) -> Optional[str]:
        """
        Get the next available API key environment variable name.
        Returns None if no keys are available.
        
        This is where quota reset is checked (lazily, once per session).
        """
        # Ensure quota reset has been checked once for this session
        self._ensure_quota_reset_checked()
        
        # If current key is still available, keep using it
        if self.is_key_available(self.current_key_env):
            return self.current_key_env
            
        # Find the next working key (not failed and not quota exhausted)
        all_keys = [self.primary_key_env] + self.backup_key_envs
        available_keys = [k for k in all_keys if self.is_key_available(k)]
        
        if not available_keys:
            self.logger.error("No more API keys available - all keys are either failed or quota exhausted")
            return None
            
        # Switch to the first available key
        self.current_key_env = available_keys[0]
        self.logger.info(f"Rotating to next available key: {self.current_key_env}")
        return self.current_key_env
    
    def get_quota_status(self) -> Dict[str, str]:
        """
        Get the quota status of all keys.
        
        Returns:
            Dict mapping key_env to status: 'available', 'quota_exhausted', 'failed'
        """
        # Ensure quota reset has been checked once for this session
        self._ensure_quota_reset_checked()
        
        all_keys = [self.primary_key_env] + self.backup_key_envs
        status = {}
        
        for key_env in all_keys:
            if key_env in self.failed_keys:
                status[key_env] = 'failed'
            elif key_env in self.quota_exhausted_keys:
                status[key_env] = f'quota_exhausted_until_midnight_pt'
            else:
                status[key_env] = 'available'
        
        return status

    def force_quota_reset_check(self) -> None:
        """Force a quota reset check regardless of session state (useful for testing)."""
        self.logger.info(f"Forcing quota reset check for {self.provider_name}")
        self._reset_expired_quotas()
        self._mark_quota_reset_checked()

    def reset(self) -> None:
        """Reset the key manager state (clears all failed and quota exhausted keys)."""
        self.failed_keys.clear()
        self.quota_exhausted_keys.clear()
        self.current_key_env = self.primary_key_env
        self._save_quota_state()
        self.logger.info("Reset APIKeyManager state - cleared all failed and quota exhausted keys")

    def reset_quota_only(self) -> None:
        """Reset only quota exhausted keys (useful for testing or manual reset)."""
        cleared_keys = list(self.quota_exhausted_keys.keys())
        self.quota_exhausted_keys.clear()
        self._save_quota_state()
        if cleared_keys:
            self.logger.info(f"Manually reset quota status for keys: {cleared_keys}") 