# OpenAI and Anthropic Integration with Intelligent Rate Limiting

This document describes the implementation of intelligent rate limiting and API key management for OpenAI and Anthropic providers in the JobApp core module system. All references to source code use local links for easy navigation.

## Overview

The system supports intelligent handling of rate limits and quota exhaustion for **OpenAI** and **Anthropic** APIs, as well as Google Gemini and OpenRouter. The implementation provides:

- **Automatic error detection** for RPM (requests per minute) vs RPD (requests per day) limits
- **Smart retry strategies**: exponential backoff for RPM, immediate key rotation for RPD
- **Persistent quota tracking** with provider-specific timezone handling
- **Session-based optimization** to prevent redundant quota reset checks
- **Automatic API key rotation** when daily quotas are exhausted

**Key Implementation Files:**
- [jobapp/core/llm_interface.py](../jobapp/core/llm_interface.py)
- [jobapp/core/api_key_manager.py](../jobapp/core/api_key_manager.py)
- [jobapp/core/config_manager.py](../jobapp/core/config_manager.py)

## Provider-Specific Rate Limit Information

(Provider details and error patterns remain as in the original doc, but note: the actual error pattern lists are maintained in [APIKeyManager](../jobapp/core/api_key_manager.py) and are up to date with provider docs.)

## Configuration Examples

(YAML and environment variable examples remain accurate. The code expects backup keys as shown.)

## Usage Examples

### Basic Usage (Python)

```python
from jobapp.core.llm_interface import LLMInterface

llm = LLMInterface()

# OpenAI request with automatic rate limiting and key rotation
response = llm.send_prompt(
    "Hello, world!",
    provider="openai",
    model="gpt-4o-mini"
)

# Anthropic request with automatic rate limiting and key rotation
response = llm.send_prompt(
    "Hello, world!",
    provider="anthropic", 
    model="claude-3-haiku-20240307"
)
```

### CLI/Script Usage Example

You can use the LLMInterface in your own scripts or CLI tools. All fallback and key rotation logic is handled automatically:

```python
from jobapp.core.llm_interface import LLMInterface
llm = LLMInterface()

try:
    response = llm.send_prompt(
        "Complex analysis task",
        provider="openai",
        model="gpt-4o-mini",
        max_retries=5,        # RPM retry attempts
        retry_delay=2.0,      # Base delay for exponential backoff
        fallback=True         # Use fallback model if primary fails
    )
    print(response)
except Exception as e:
    print(f"All attempts failed: {e}")
```

- **Fallback model logic** is handled in `LLMInterface.send_prompt()` ([llm_interface.py](../jobapp/core/llm_interface.py)).
- **Key rotation and quota state** are managed by `APIKeyManager` ([api_key_manager.py](../jobapp/core/api_key_manager.py)).

## Retry and Quota Handling

- **RPM (Rate Limit) Handling:**
  - Exponential backoff with jitter (configurable)
  - Retries with the same key after delay
- **RPD/Quota Exhaustion Handling:**
  - Immediate API key rotation
  - Persistent quota state is stored in the cache directory as determined by ConfigManager (see [config_manager.py](../jobapp/core/config_manager.py))
  - Quota state survives application restarts
- **Session Optimization:**
  - Quota reset is checked once per provider per session
  - State is stored in class variables and on disk

## Implementation Details

- All error pattern lists for rate limits and quota exhaustion are maintained in [APIKeyManager](../jobapp/core/api_key_manager.py) and are kept up to date with provider documentation.
- Persistent quota state is stored in a JSON file in the cache directory (see `get_cache_path()` in [config_manager.py](../jobapp/core/config_manager.py)).
- Fallback model logic is handled in [LLMInterface.send_prompt()](../jobapp/core/llm_interface.py).
- Logging and debug output are available for troubleshooting.

## Troubleshooting

- If you see "No API keys available" errors, check that backup keys are configured and not all exhausted.
- Frequent rate limiting on OpenAI free tier? Upgrade to Tier 1 for higher limits.
- Anthropic quota exhaustion? Monitor monthly spend and add credits.
- Timezone confusion for quota resets? The system automatically handles provider-specific timezones.
- Enable detailed logging for debugging:

```python
import logging
logging.getLogger('jobapp.core.api_key_manager').setLevel(logging.DEBUG)
```

- To manually reset quota state:

```python
from jobapp.core.api_key_manager import APIKeyManager
manager = APIKeyManager("YOUR_KEY", [])
manager.reset()  # Clears all failed and quota-exhausted keys
```

## Conclusion

The OpenAI and Anthropic integration in JobApp provides robust, intelligent rate limiting and key management:
- **Minimizes costs** through smart retry strategies
- **Maximizes uptime** with automatic key rotation
- **Optimizes performance** with session-based caching
- **Scales seamlessly** across multiple providers and keys

For implementation details, see [llm_interface.py](../jobapp/core/llm_interface.py) and [api_key_manager.py](../jobapp/core/api_key_manager.py). 