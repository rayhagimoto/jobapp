# Rate Limiting Quick Reference

## Supported Providers

| Provider   | Free Tier | Cheapest Paid | Reset Time    | Rate Limits |
|------------|-----------|---------------|---------------|-------------|
| **Google** | ✅ 200 RPD | Same (Free)   | Midnight PT   | 200 RPD     |
| **OpenRouter** | ✅ 20 RPM | $0.10 credit | Midnight UTC  | 20 RPM, varies RPD |
| **OpenAI** | ✅ 3 RPM, 200 RPD | $5 → 500 RPM | Rolling       | 3 RPM, 200 RPD |
| **Anthropic** | ❌ | $5 deposit   | Monthly       | 50 RPM, 20K ITPM |

## Environment Variables Setup

```bash
# Primary API keys
export GOOGLE_API_KEY="AIza..."
export OPENROUTER_API_KEY="sk-or-v1-..."
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Backup keys for automatic rotation
export GOOGLE_API_KEY_BACKUP_1="AIza..."
export OPENAI_API_KEY_BACKUP_1="sk-..."
# ... add more as needed
```

## Configuration Examples

### Cost-Effective Setup (Free Tiers)
```yaml
# config/default.yaml
models:
  default:
    provider: "google_genai"
    model: "gemini-2.0-flash-exp"
    key: "GOOGLE_API_KEY"
  fallback:
    provider: "openai"
    model: "gpt-4o-mini"
    key: "OPENAI_API_KEY"
```

### Production Setup (Paid Tiers)
```yaml
# config/default.yaml
models:
  default:
    provider: "anthropic"
    model: "claude-3-haiku-20240307"
    key: "ANTHROPIC_API_KEY"
    backup_keys:
      - "ANTHROPIC_API_KEY_BACKUP_1"
  fallback:
    provider: "openai"
    model: "gpt-4o-mini"
    key: "OPENAI_API_KEY"
```

## Error Types & Handling

### RPM (Rate Limit) Errors
- **Behavior**: Exponential backoff retry
- **Strategy**: Wait and retry with same key
- **Duration**: Temporary (seconds to minutes)

### RPD/Quota Exhaustion Errors  
- **Behavior**: Immediate key rotation
- **Strategy**: Switch to next available key
- **Duration**: Until daily/monthly reset

## Common Patterns

### Basic Usage
```python
from jobapp.core.llm_interface import LLMInterface

llm = LLMInterface()
response = llm.send_prompt("Your prompt here")
```

### With Specific Provider
```python
response = llm.send_prompt(
    "Your prompt here",
    provider="openai",
    model="gpt-4o-mini"
)
```

### With Custom Retry Settings
```python
response = llm.send_prompt(
    "Your prompt here",
    max_retries=5,
    retry_delay=2.0,
    fallback=True
)
```

## Troubleshooting

### "No API keys available" 
- Check environment variables are set
- Verify backup keys are configured
- Check if all keys are quota-exhausted

### Frequent rate limiting
- Add more backup keys
- Upgrade to paid tier
- Implement request batching

### Quota reset issues
- System handles timezone differences automatically
- State persists across application restarts
- Use `manager.reset()` to clear state if needed

## State Files

- **Linux/macOS**: `~/.cache/jobapp/api_key_state.json`
- **Windows**: `%LOCALAPPDATA%/jobapp/api_key_state.json`

## Testing

```bash
# Test without API keys (error detection patterns)
python test_openai_anthropic_integration.py

# Test with API keys (full connectivity)
export OPENAI_API_KEY="your-key"
python test_openai_anthropic_integration.py
```

## Cost Optimization Tips

1. **Start with free tiers** for development
2. **Use cheapest models** (`gpt-4o-mini`, `claude-3-haiku`)
3. **Configure backup keys** to avoid downtime
4. **Monitor usage** via provider dashboards
5. **Implement request batching** for bulk operations 