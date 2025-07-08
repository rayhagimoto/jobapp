from jobapp.core.config_manager import ConfigManager
from jobapp.core.api_key_manager import APIKeyManager
from jobapp.core.logger import get_logger
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables.base import Runnable
import yaml
from string import Template
import time
import os
from typing import List, Tuple, Union, Optional, Any

class LLMInterface(Runnable):
    """
    Modern interface for sending prompts to LLM providers using langchain's init_chat_model.
    Includes smart API key management with quota tracking and automatic rotation.
    Now a LangChain Runnable: you can use it in chains, e.g., prompt | llm
    Usage:
        llm = LLMInterface()
        response = llm.send_prompt("Hello!", task_name="match_score")
        # or, for LangChain chains:
        response = prompt | llm
    """
    def __init__(self, config: ConfigManager = None):
        self.config = config or ConfigManager()
        self.logger = get_logger(__name__)
        self._api_key_managers = {}  # Cache managers per provider

    def _get_api_key_manager(self, provider: str, primary_key_env: str) -> Optional[APIKeyManager]:
        """Get or create an API key manager for a specific provider."""
        if provider not in self._api_key_managers:
            # Get backup keys from the model configuration
            # Check both default and fallback model configs for backup_keys
            default_model_config = self.config.get_model_config(is_fallback=False)
            fallback_model_config = self.config.get_model_config(is_fallback=True)
            
            # Look for backup_keys in either config
            backup_keys = (default_model_config.get('backup_keys', []) or 
                          fallback_model_config.get('backup_keys', []))
            
            if backup_keys:
                self.logger.info(f"Found {len(backup_keys)} backup keys for {provider}: {backup_keys}")
                self._api_key_managers[provider] = APIKeyManager(
                    primary_key_env=primary_key_env,
                    backup_key_envs=backup_keys,
                    config_manager=self.config
                )
            else:
                self.logger.debug(f"No backup keys configured for {provider}, skipping key manager")
                # No backup keys configured, don't use key manager
                return None
        
        return self._api_key_managers[provider]

    def _is_openrouter_model(self, model: str) -> bool:
        """Check if a model is from OpenRouter based on the model name pattern."""
        # OpenRouter models typically have provider/model format like "deepseek/deepseek-chat"
        # or contain specific OpenRouter model identifiers
        openrouter_patterns = [
            'deepseek/', 'anthropic/', 'meta-llama/', 'google/', 'mistral/',
            'openai/', 'cohere/', 'perplexity/', 'qwen/', 'nvidia/'
        ]
        return any(pattern in model for pattern in openrouter_patterns) and '/' in model

    def _setup_openrouter_env(self):
        """Set up environment variables for OpenRouter if needed."""
        openrouter_api_key = self.config.get('OPENROUTER_API_KEY')
        openrouter_base_url = self.config.get('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
        
        if openrouter_api_key:
            os.environ['OPENAI_API_KEY'] = openrouter_api_key
            os.environ['OPENAI_API_BASE'] = openrouter_base_url

    def _get_llm(self, task_name: str = None, provider: str = None, model: str = None, is_fallback: bool = False, api_key_env: str = None, **kwargs):
        """
        Get the appropriate LLM using the modern init_chat_model API.
        """
        base_url = None
        
        if provider and model:
            # Direct provider:model specification
            actual_model = model
            actual_provider = provider
            if api_key_env is None:
                api_key_env = None  # Will be determined later
        else:
            # Get from config
            model_config = self.config.get_model_config(
                task_name=task_name,
                is_fallback=is_fallback
            )
            actual_provider = model_config.get('provider')
            actual_model = model_config.get('model')
            api_key_env = api_key_env or model_config.get('key')
            base_url = model_config.get('base_url')  # Get base_url from config
            
            if not actual_provider or not actual_model:
                raise ValueError(f"Missing provider or model in configuration: {model_config}")
            
            provider = actual_provider

        # Handle OpenRouter - treat as OpenAI-compatible with custom base_url
        if actual_provider == 'openrouter':
            model_identifier = f"openai:{actual_model}"
            # Set up OpenRouter environment
            openrouter_api_key = self.config.get('OPENROUTER_API_KEY')
            if openrouter_api_key:
                os.environ['OPENAI_API_KEY'] = openrouter_api_key
            if not base_url:
                base_url = 'https://openrouter.ai/api/v1'
            os.environ['OPENAI_API_BASE'] = base_url
        elif self._is_openrouter_model(actual_model):
            # Legacy detection for OpenRouter models
            model_identifier = f"openai:{actual_model}"
            self._setup_openrouter_env()
        else:
            model_identifier = f"{actual_provider}:{actual_model}"

        # Handle custom API key if specified
        original_api_key = None
        original_base_url = None
        if api_key_env:
            provider_key_map = {
                'google_genai': 'GOOGLE_API_KEY',
                'anthropic': 'ANTHROPIC_API_KEY',
                'openai': 'OPENAI_API_KEY',
                'azure': 'AZURE_OPENAI_API_KEY',
                'openrouter': 'OPENROUTER_API_KEY',
                'cohere': 'COHERE_API_KEY'
            }
            
            # For OpenRouter, we use the openai provider but with OPENROUTER_API_KEY
            effective_provider = 'openai' if actual_provider == 'openrouter' else actual_provider
            
            if effective_provider in provider_key_map:
                env_key = provider_key_map[effective_provider]
                # Save original key if it exists
                if env_key in os.environ:
                    original_api_key = os.environ[env_key]
                # Set the custom key
                custom_key = self.config.get(api_key_env)
                if custom_key:
                    os.environ[env_key] = custom_key
                else:
                    print(f"[WARNING] Custom API key env var '{api_key_env}' not found")
        
        # Handle custom base_url for providers that support it
        if base_url and actual_provider in ['openai', 'openrouter']:
            if 'OPENAI_API_BASE' in os.environ:
                original_base_url = os.environ['OPENAI_API_BASE']
            os.environ['OPENAI_API_BASE'] = base_url

        # Add info logging for which LLM is being loaded
        # self.logger.info(f"[LLMInterface] Loading model for task '{task_name}': provider={actual_provider}, model={actual_model}, key={model_config.get('key')}, base_url={model_config.get('base_url')}")
        try:
            # Pass through kwargs to init_chat_model, with temperature as default
            model_kwargs = {'temperature': 0.3}
            if actual_provider == 'google_genai':
                model_kwargs['thinking_budget'] = 0
                self.logger.debug(f"Added thinking_budget=0 for Google Gemini model: {actual_model}")
            model_kwargs.update(kwargs)
            self.logger.debug(f"Final model_kwargs for {model_identifier}: {model_kwargs}")
            return init_chat_model(model_identifier, **model_kwargs)
        except Exception as e:
            raise ValueError(f"Failed to initialize model '{model_identifier}': {e}")
        finally:
            # Restore original API key if we changed it
            if original_api_key is not None and api_key_env and effective_provider in provider_key_map:
                os.environ[provider_key_map[effective_provider]] = original_api_key
            # Restore original base URL if we changed it
            if original_base_url is not None:
                os.environ['OPENAI_API_BASE'] = original_base_url
            elif base_url and 'OPENAI_API_BASE' in os.environ:
                # Remove the base URL we set if there was no original
                del os.environ['OPENAI_API_BASE']

    def _handle_llm_call_with_key_management(self, llm_call_func, task_name: str = None, provider: str = None, model: str = None, is_fallback: bool = False, max_retries: int = 3, retry_delay: float = 1.0, **kwargs):
        """
        Handle LLM calls with smart API key management, quota tracking, and appropriate retry logic.
        
        Args:
            llm_call_func: Function that makes the actual LLM call (takes llm as parameter)
            task_name: Task configuration to use
            provider: Override provider
            model: Override model
            is_fallback: Whether this is a fallback call
            max_retries: Max retries for rate limiting
            retry_delay: Base delay for rate limiting retries
            
        Returns:
            LLM response content
        """
        # Get model config to determine provider and API key
        if provider and model:
            model_config = {'provider': provider, 'model': model}
            primary_key_env = None  # Will need to be determined
        else:
            model_config = self.config.get_model_config(task_name=task_name, is_fallback=is_fallback)
            primary_key_env = model_config.get('key')
        
        provider_name = model_config.get('provider')
        
        # Get API key manager if we have backup keys configured
        api_key_manager = None
        if primary_key_env and provider_name:
            api_key_manager = self._get_api_key_manager(provider_name, primary_key_env)
        
        current_key_env = primary_key_env
        rpm_retry_count = 0
        
        while True:
            try:
                # If using key manager, get the current key
                if api_key_manager:
                    current_key_env = api_key_manager.get_next_key_env()
                    if current_key_env is None:
                        raise Exception("All API keys are exhausted or failed")
                
                # --- ADDED LOGGING ---
                self.logger.debug(f"Attempting to initialize model with task '{task_name}', fallback: {is_fallback}, key_env: '{current_key_env}'")
                
                # Create LLM with current key and pass through kwargs
                llm = self._get_llm(
                    task_name=task_name if not (provider or model) else None,
                    provider=provider if not is_fallback else None,
                    model=model if not is_fallback else None,
                    is_fallback=is_fallback,
                    api_key_env=current_key_env,
                    **kwargs
                )
                
                # Make the actual LLM call
                result = llm_call_func(llm)
                return result.content if hasattr(result, 'content') else str(result)
                
            except Exception as e:
                # --- ADDED LOGGING ---
                self.logger.error(f"LLM call failed with key {current_key_env}. Error: {e}", exc_info=True)
                
                error_type = 'unknown'
                
                # Handle error with API key manager if available
                if api_key_manager and current_key_env:
                    error_type = api_key_manager.handle_api_error(e, current_key_env)
                
                if error_type == 'rate_limited':
                    # RPM limit hit - retry with exponential backoff
                    if rpm_retry_count < max_retries:
                        backoff_delay = retry_delay * (2 ** rpm_retry_count)
                        print(f"[INFO] Rate limit hit (RPM), retrying in {backoff_delay:.1f}s (attempt {rpm_retry_count + 1}/{max_retries})")
                        time.sleep(backoff_delay)
                        rpm_retry_count += 1
                        continue
                    else:
                        print(f"[ERROR] Rate limit exceeded max retries: {e}")
                        raise e
                        
                elif error_type == 'quota_exhausted':
                    # RPD limit hit - try next key if available
                    if api_key_manager:
                        next_key = api_key_manager.get_next_key_env()
                        if next_key and next_key != current_key_env:
                            print(f"[INFO] Daily quota exhausted for {current_key_env}, rotating to {next_key}")
                            current_key_env = next_key
                            rpm_retry_count = 0  # Reset RPM retry count for new key
                            continue
                    
                    print(f"[ERROR] Daily quota exhausted and no more keys available: {e}")
                    raise e
                    
                else:
                    # Other error (failed key or unknown) - try next key if available
                    if api_key_manager:
                        next_key = api_key_manager.get_next_key_env()
                        if next_key and next_key != current_key_env:
                            print(f"[WARNING] Key {current_key_env} failed, rotating to {next_key}")
                            current_key_env = next_key
                            rpm_retry_count = 0  # Reset RPM retry count for new key
                            continue
                    
                    print(f"[ERROR] LLM call failed: {e}")
                    raise e

    def send_prompt(self, prompt, task_name: str = None, provider: str = None, model: str = None, retry: bool = True, fallback: bool = True, max_retries: int = 3, retry_delay: float = 1.0, **kwargs):
        """
        Send a prompt to the LLM with smart key management, retry and fallback logic.
        """
        def llm_call(llm):
            return llm.invoke(prompt)
        # Try primary model with key management
        try:
            return self._handle_llm_call_with_key_management(
                llm_call, task_name, provider, model, is_fallback=False, max_retries=max_retries, retry_delay=retry_delay, **kwargs
            )
        except Exception as e:
            if fallback:
                print(f"[WARNING] Primary model failed ({e}), attempting fallback...")
                try:
                    return self._handle_llm_call_with_key_management(
                        llm_call, task_name, None, None, is_fallback=True, max_retries=max_retries, retry_delay=retry_delay, **kwargs
                    )
                except Exception as fallback_error:
                    print(f"[ERROR] Fallback model also failed: {fallback_error}")
                    return f"[LLM Error: Primary failed ({e}), Fallback failed ({fallback_error})]"
            else:
                return f"[LLM Error: {e}]"

    def prepare_prompt_with_context(self, template_str, context_data):
        """
        Loads a prompt template string and injects context data using string.Template.
        """
        template = Template(template_str)
        return template.safe_substitute(context_data)

    def invoke(self, input: Any, config: Optional[dict] = None, **kwargs) -> Any:
        """
        LangChain Runnable protocol: invoke(input, config=None, **kwargs)
        Allows piping: response = prompt | llm
        Input: prompt string or messages. Kwargs are passed to send_prompt.
        Config is ignored unless needed for advanced features.
        Returns: LLM response string.
        """
        return self.send_prompt(input, **kwargs)

    def __call__(self, input: Any, config: Optional[dict] = None, **kwargs) -> Any:
        """
        Alias for invoke, for compatibility with LangChain usages.
        """
        return self.invoke(input, config, **kwargs) 