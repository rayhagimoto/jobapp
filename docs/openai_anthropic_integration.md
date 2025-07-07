# OpenAI and Anthropic Integration with Intelligent Rate Limiting

This document describes the implementation of intelligent rate limiting and API key management for OpenAI and Anthropic providers in the JobApp core module system.

## Overview

The system now supports intelligent handling of rate limits and quota exhaustion for **OpenAI** and **Anthropic** APIs, in addition to the existing Google Gemini and OpenRouter support. The implementation provides:

- **Automatic error detection** for RPM (requests per minute) vs RPD (requests per day) limits
- **Smart retry strategies**: exponential backoff for RPM, immediate key rotation for RPD
- **Persistent quota tracking** with provider-specific timezone handling
- **Session-based optimization** to prevent redundant quota reset checks
- **Automatic API key rotation** when daily quotas are exhausted

## Provider-Specific Rate Limit Information

### OpenAI API Rate Limits

**Free Tier (No payment required):**
- 3 RPM (requests per minute)
- 200 RPD (requests per day) 
- 40,000 TPM (tokens per minute)

**Tier 1 (After $5 payment):**
- 500 RPM
- 30,000 TPM
- No daily request limit

**Rate Limit Behavior:**
- Uses **rolling rate limits** (not fixed daily resets)
- **Reset time**: Continuous rolling windows
- **Timezone**: UTC (for our tracking purposes)
- **Headers**: `x-ratelimit-remaining-requests`, `x-ratelimit-remaining-tokens`

### Anthropic API Rate Limits

**Tier 1 (After $5 deposit):**
- 50 RPM (requests per minute)
- 20,000 ITPM (input tokens per minute)
- 8,000 OTPM (output tokens per minute)
- $100 monthly spend limit

**Rate Limit Behavior:**
- Uses **token bucket algorithm** with continuous replenishment
- **Reset time**: Monthly limits reset at calendar month start
- **Timezone**: UTC
- **Headers**: `anthropic-ratelimit-requests-remaining`, `anthropic-ratelimit-tokens-remaining`

### Comparison with Existing Providers

| Provider  | Daily Reset Time | Rate Limit Type | Free Tier Available |
|-----------|------------------|-----------------|-------------------|
| Google    | Midnight PT      | Fixed daily     | Yes (200 RPD)     |
| OpenRouter| Midnight UTC     | Rolling + Daily | Yes (20 RPM)      |
| OpenAI    | Rolling windows  | Rolling         | Yes (3 RPM, 200 RPD) |
| Anthropic | Monthly reset    | Token bucket    | No (requires $5)  |

## Error Detection Patterns

### OpenAI Error Patterns

**RPM (Rate Limit) Errors:**
```python
- "rate limit reached"
- "ratelimiterror" 
- "x-ratelimit-remaining-requests"
- "x-ratelimit-remaining-tokens"
- "tokens per minute"
- "tpm"
```

**Quota Exhaustion Errors:**
```python
- "insufficient_quota"
- "you exceeded your current quota"
- "please check your plan and billing details"
- "quota exceeded"
- "billing details"
```

### Anthropic Error Patterns

**RPM (Rate Limit) Errors:**
```python
- "anthropic-ratelimit-requests-remaining"
- "anthropic-ratelimit-tokens-remaining"
- "retry-after"
- "input tokens per minute"
- "output tokens per minute"
- "itpm", "otpm"
```

**Quota Exhaustion Errors:**
```python
- "monthly spend limit"
- "spend limit"
- "credit limit exceeded"
- "monthly usage limit"
- "organization limit exceeded"
```

## Configuration Examples

### OpenAI Configuration

```yaml
# config/default.yaml
models:
  default:
    provider: "openai"
    model: "gpt-4o-mini"  # Cheapest model
    key: "OPENAI_API_KEY"
    backup_keys:
      - "OPENAI_API_KEY_BACKUP_1"
      - "OPENAI_API_KEY_BACKUP_2"
```

### Anthropic Configuration

```yaml
# config/default.yaml
models:
  default:
    provider: "anthropic"
    model: "claude-3-haiku-20240307"  # Cheapest model
    key: "ANTHROPIC_API_KEY"
    backup_keys:
      - "ANTHROPIC_API_KEY_BACKUP_1"
      - "ANTHROPIC_API_KEY_BACKUP_2"
```

### Environment Variables

```bash
# Primary API keys
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Backup keys for rotation
export OPENAI_API_KEY_BACKUP_1="sk-..."
export OPENAI_API_KEY_BACKUP_2="sk-..."
export ANTHROPIC_API_KEY_BACKUP_1="sk-ant-..."
export ANTHROPIC_API_KEY_BACKUP_2="sk-ant-..."
```

## Usage Examples

### Basic Usage

```python
from jobapp.core.llm_interface import LLMInterface

# Initialize with automatic provider detection
llm = LLMInterface()

# OpenAI request with automatic rate limiting
response = llm.send_prompt(
    "Hello, world!",
    provider="openai",
    model="gpt-4o-mini"
)

# Anthropic request with automatic rate limiting
response = llm.send_prompt(
    "Hello, world!",
    provider="anthropic", 
    model="claude-3-haiku-20240307"
)
```

### Advanced Usage with Error Handling

```python
from jobapp.core.llm_interface import LLMInterface
from jobapp.core.api_key_manager import APIKeyManager

# Initialize components
llm = LLMInterface()

# Send prompt with custom retry settings
try:
    response = llm.send_prompt(
        "Complex analysis task",
        provider="openai",
        model="gpt-4o-mini",
        max_retries=5,        # RPM retry attempts
        retry_delay=2.0,      # Base delay for exponential backoff
        fallback=True         # Use fallback model if primary fails
    )
except Exception as e:
    print(f"All attempts failed: {e}")
```

## Retry Strategy Details

### RPM (Rate Limit) Handling
- **Strategy**: Exponential backoff with jitter
- **Max retries**: Configurable (default: 3)
- **Base delay**: Configurable (default: 1.0 seconds)
- **Backoff formula**: `delay * (2 ** retry_count)`
- **Behavior**: Retry with same API key after delay

### RPD/Quota Exhaustion Handling
- **Strategy**: Immediate API key rotation
- **Max attempts**: Number of available API keys
- **Fallback**: Switch to fallback model if all keys exhausted
- **Persistence**: Quota state saved to disk, survives application restarts

## Implementation Details

### Key Components Modified

1. **APIKeyManager** (`jobapp/core/api_key_manager.py`)
   - Added OpenAI and Anthropic error pattern detection
   - Enhanced timezone handling for different providers
   - Improved session-based quota reset checking

2. **LLMInterface** (`jobapp/core/llm_interface.py`)
   - Existing error handling already supports new providers
   - Automatic provider detection and API key management
   - Integrated retry logic with exponential backoff

3. **ConfigManager** (`jobapp/core/config_manager.py`)
   - Enhanced cache path resolution for quota state storage
   - Support for provider-specific configuration

### State Persistence

Quota state is persisted in:
```
~/.cache/jobapp/api_key_state.json  # Linux/macOS
%LOCALAPPDATA%/jobapp/api_key_state.json  # Windows
```

State includes:
- Quota-exhausted keys with expiration dates
- Provider-specific timezone tracking
- Session reset check timestamps

### Session Optimization

The system implements session-based quota reset checking to prevent redundant operations:

- **Once per session**: Quota reset is checked only once per provider per session
- **Lazy evaluation**: Reset check happens when first API call is made
- **Provider isolation**: Each provider tracks its own session state
- **Memory efficient**: Session state stored in class variables

## Testing

### Running Tests

```bash
# Navigate to JobApp directory
cd JobApp

# Activate virtual environment
source .venv/bin/activate

# Run comprehensive test suite
python test_openai_anthropic_integration.py
```

### Test Coverage

The test suite covers:
- ✅ Provider timezone handling
- ✅ Quota reset behavior and session tracking
- ✅ Rate limit error pattern detection
- ✅ API key rotation simulation
- ✅ Basic connectivity (when API keys provided)

### Sample Test Output

```
🧪 Testing OpenAI and Anthropic Integration with Smart Rate Limiting
======================================================================

=== Testing Provider Timezone Handling ===
   Google: 2025-06-26 (Pacific Time)
   Openai: 2025-06-27 (UTC)
   Anthropic: 2025-06-27 (UTC)
   Openrouter: 2025-06-27 (UTC)

=== Testing OpenAI Rate Limit Detection ===
   Test 1: Rate limit reached for default-gpt-4o-mini...
      ✅ Correctly identified as RPM limit
   Test 2: You exceeded your current quota...
      ✅ Correctly identified as quota exhaustion

=== Testing Anthropic Rate Limit Detection ===
   Test 1: 429 - anthropic-ratelimit-requests-remaining: 0...
      ✅ Correctly identified as RPM limit
   Test 2: Monthly spend limit exceeded...
      ✅ Correctly identified as quota exhaustion
```

## Cost Optimization Recommendations

### OpenAI
- **Start with free tier**: 3 RPM, 200 RPD sufficient for testing
- **Upgrade trigger**: When hitting daily limits consistently
- **Model choice**: Use `gpt-4o-mini` for cost-effective operations
- **Monitoring**: Track token usage via headers

### Anthropic
- **Minimum investment**: $5 deposit required for API access
- **Model choice**: Use `claude-3-haiku-20240307` for cost-effective operations
- **Spend tracking**: Monitor monthly spend limits carefully
- **Token optimization**: Separate input/output token limits

### Multi-Provider Strategy
- **Primary/Fallback**: Use cheaper provider as primary, premium as fallback
- **Load balancing**: Distribute requests across multiple providers
- **Quota management**: Configure backup keys for seamless rotation
- **Cost monitoring**: Track spend across all providers

## Future Enhancements

### Planned Improvements
1. **Dynamic rate limiting**: Adjust retry delays based on provider response headers
2. **Cost tracking**: Real-time spend monitoring across providers
3. **Smart routing**: Automatic provider selection based on cost/performance
4. **Usage analytics**: Detailed reporting on API usage patterns

### Provider Roadmap
- **Azure OpenAI**: Enterprise-grade OpenAI with enhanced security
- **Cohere**: Specialized models for specific use cases
- **Together AI**: Open-source model hosting
- **Replicate**: Community model marketplace

## Troubleshooting

### Common Issues

**Issue**: "No API keys available" error
**Solution**: Check that backup keys are properly configured and not all exhausted

**Issue**: Frequent rate limiting on OpenAI free tier
**Solution**: Upgrade to Tier 1 ($5 payment) for higher limits

**Issue**: Anthropic quota exhaustion
**Solution**: Monitor monthly spend limits and add more credits

**Issue**: Timezone confusion for quota resets
**Solution**: System automatically handles provider-specific timezones

### Debug Mode

Enable detailed logging:
```python
import logging
logging.getLogger('jobapp.core.api_key_manager').setLevel(logging.DEBUG)
```

### State Reset

Clear quota state if needed:
```python
from jobapp.core.api_key_manager import APIKeyManager
manager = APIKeyManager("YOUR_KEY", [])
manager.reset()  # Clears all failed and quota-exhausted keys
```

## Conclusion

The OpenAI and Anthropic integration provides robust, intelligent rate limiting that:

- **Minimizes costs** through smart retry strategies
- **Maximizes uptime** with automatic key rotation
- **Optimizes performance** with session-based caching
- **Scales seamlessly** across multiple providers and keys

The system is production-ready and handles the complexity of different provider rate limiting schemes transparently, allowing developers to focus on building applications rather than managing API quotas. 