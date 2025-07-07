import os
from dotenv import load_dotenv
import yaml
from pathlib import Path
from platformdirs import user_config_dir, user_data_dir
import inspect
from typing import Optional, Dict, Any

class ConfigManager:
    """
    Central configuration manager for JobApp.

    Responsibilities:
    - Loads configuration from environment variables, user config files (~/.config/jobapp/config/*.yaml), and project config files (JobApp/configs/*.yaml), with proper precedence.
    - Detects the calling module (search, resume_writer, apply) to load module-specific config.
    - Provides standardized methods for resolving paths (user data, auth, cache, etc.) with environment variable and OS expansion.
    - Merges default, module, and CLI/constructor overrides into a single config.
    - Exposes helpers for model config, user name, and section path resolution for pipelines.
    """
    def __init__(self, env_path=None):
        # Default to secrets directory if no path specified
        if env_path is None:
            secrets_dir = Path(user_config_dir("jobapp")) / "secrets"
            env_path = secrets_dir / ".env"
        print(f"[ConfigManager] Loading environment variables from: {env_path}")
        load_dotenv(env_path)
        self.env = os.environ
        self._yaml_configs = {}
        
        # Detect module from caller's file path
        self.module = self._detect_module()
        
        # Load default config first
        self.default_config = self.get_yaml_config('default', default={})
        
        # Load module-specific config if we're in a module
        self.module_config = self.get_yaml_config(self.module, default={}) if self.module != 'core' else {}

        self.merged_config = self._get_merged_config()

    def _detect_module(self) -> str:
        """
        Detects which module (search, resume_writer) is using this ConfigManager
        by examining the caller's file path.
        """
        # Get the file path of the caller
        frame = inspect.stack()[2]  # Go up 2 frames to get the actual caller
        caller_path = Path(frame.filename)
        
        # Find 'jobapp' in the path parts and get the next directory
        try:
            jobapp_index = caller_path.parts.index('jobapp')
            if len(caller_path.parts) > jobapp_index + 1:
                module = caller_path.parts[jobapp_index + 1]
                if module in ['search', 'resume_writer', 'apply']:
                    return module
        except ValueError:
            pass
            
        return 'core'  # Default to core if not in a specific module

    def get(self, key, default=None):
        """Get an environment variable value."""
        return self.env.get(key, default)

    def get_gspread_credentials_path(self):
        paths_config = self.get_yaml_config('default', {}).get('paths', {})
        auth_paths = paths_config.get('auth', {})
        yaml_path = auth_paths.get('gspread_creds', '~/.config/jobapp/auth/gspread_credentials.json')
        if isinstance(yaml_path, dict):
            yaml_path = yaml_path.get('path', '~/.config/jobapp/auth/gspread_credentials.json')
        if not isinstance(yaml_path, str):
            raise ValueError(f'gspread_creds path in config must be a string, got {type(yaml_path)}: {yaml_path}')
        path = os.path.expanduser(os.path.expandvars(yaml_path))
        return path

    def get_linkedin_auth_state_path(self):
        paths_config = self.get_yaml_config('default', {}).get('paths', {})
        auth_paths = paths_config.get('auth', {})
        yaml_path = auth_paths.get('linkedin_auth', '~/.config/jobapp/auth/linkedin_auth.json')
        if isinstance(yaml_path, dict):
            yaml_path = yaml_path.get('path', '~/.config/jobapp/auth/linkedin_auth.json')
        if not isinstance(yaml_path, str):
            raise ValueError(f'linkedin_auth path in config must be a string, got {type(yaml_path)}: {yaml_path}')
        path = os.path.expanduser(os.path.expandvars(yaml_path))
        return path

    def get_user_data_path(self):
        """Get the user data directory path from config, with env/OS expansion."""
        paths_config = self.get_yaml_config('default', {}).get('paths', {})
        yaml_path = paths_config.get('user_data', '~/.config/jobapp/data/user')
        if isinstance(yaml_path, dict):
            yaml_path = yaml_path.get('path', '~/.config/jobapp/data/user')
        if not isinstance(yaml_path, str):
            raise ValueError(f'user_data path in config must be a string, got {type(yaml_path)}: {yaml_path}')
        path = os.path.expanduser(os.path.expandvars(yaml_path))
        return path

    def get_experiences_path(self):
        """Get the user experiences file path from config (user_data/experiences.md)."""
        user_data_path = self.get_user_data_path()
        return os.path.join(user_data_path, 'experiences.md')

    def get_user_resume_path(self):
        """Get the user's master resume file path from config (user_data/resume.yaml)."""
        user_data_path = self.get_user_data_path()
        return os.path.join(user_data_path, 'resume.yaml')

    def get_cache_path(self):
        """Get the cache directory path from config, with env/OS expansion and fallback."""
        # Load from default.yaml paths.cache if it exists, otherwise use data/cache pattern
        paths_config = self.get_yaml_config('default', {}).get('paths', {})
        
        # Use platformdirs for the fallback default instead of hardcoded path
        fallback_default = str(Path(user_data_dir("jobapp")) / "cache")
        yaml_path = paths_config.get('cache', fallback_default)
        path = os.path.expanduser(os.path.expandvars(yaml_path))
        
        # Check if environment variables were expanded, if not fall back to OS-appropriate default
        if '${' in path:
            fallback_path = Path(user_data_dir("jobapp")) / "cache"
            path = str(fallback_path)
        
        return path

    def get_yaml_config(self, config_name: str, default: dict = None) -> dict:
        """
        Loads and returns configuration data from a YAML file in the user config directory.
        Caches the loaded config for subsequent calls.
        """
        if config_name in self._yaml_configs:
            return self._yaml_configs[config_name]

        # Look in OS-appropriate user config directory first
        user_config_path = Path(user_config_dir("jobapp")) / "config" / f"{config_name}.yaml"
        
        # Fallback to project configs directory
        project_config_path = Path(__file__).parent.parent.parent / "configs" / f"{config_name}.yaml"
        
        for config_path in [user_config_path, project_config_path]:
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                    self._yaml_configs[config_name] = config_data if config_data is not None else {}
                    print(f"[INFO] Loaded config: {config_path}")
                    return self._yaml_configs[config_name]
            except FileNotFoundError:
                continue
            except yaml.YAMLError as e:
                print(f"[ERROR] Error parsing YAML file {config_path}: {e}")
                return default if default is not None else {}
        
        print(f"[WARNING] Config file '{config_name}.yaml' not found in user config or project directory. Returning default.")
        return default if default is not None else {}

    def get_model_config(self, task_name: str = None, is_fallback: bool = False) -> Dict[str, str]:
        """
        Get the model configuration for a specific task, with fallback support.
        
        Args:
            task_name: The name of the task as shown as fields in the module's config.yaml (e.g., 'match_score')
            is_fallback: Whether to get the fallback configuration
            
        Returns:
            Dict containing 'provider', 'model', and optionally 'key' fields
        """
        # Get the base configuration (either default or fallback)
        base_key = 'fallback' if is_fallback else 'default'
        base_config = self.default_config.get('models', {}).get(base_key, {})
        
        if not task_name or self.module == 'core':
            return base_config
        
        # Get module-specific configuration if it exists
        module_models = self.module_config.get('models', {})
        task_config = module_models.get(task_name, {})
        
        # If the module config specifies None for provider/model/key, use the base config
        result = {
            'provider': task_config.get('provider') or base_config.get('provider'),
            'model': task_config.get('model') or base_config.get('model'),
        }
        
        # Only include key if it's specified in either config
        key = task_config.get('key') or base_config.get('key')
        if key:
            result['key'] = key
        
        return result

    def get_user_name(self) -> str:
        """
        Returns the user's name from their resume YAML. Raises ValueError if not set.
        """
        resume_path = self.get_user_resume_path()
        try:
            with open(resume_path, 'r', encoding='utf-8') as f:
                resume_data = yaml.safe_load(f)
        except FileNotFoundError:
            raise ValueError(
                f"Resume file not found at {resume_path}. Please ensure your resume YAML exists."
            )
        except yaml.YAMLError as e:
            raise ValueError(
                f"Error parsing resume YAML at {resume_path}: {e}"
            )
        profile = resume_data.get('profile', {}) if resume_data else {}
        name = profile.get('name')
        if not name or not isinstance(name, str) or not name.strip():
            raise ValueError(
                "Your name is not set in your resume YAML. Please add:\n\n"
                "profile:\n  name: 'First Last'\n"
            )
        return name

    def _get_merged_config(self, cli_overrides: Optional[dict] = None) -> dict:
        """
        Returns a merged config dictionary:
        - default config (lowest priority)
        - updated with module config (overrides defaults)
        - updated with CLI/constructor overrides (highest priority)
        Performs a recursive (deep) merge for nested dictionaries.
        """
        def deep_update(d, u):
            for k, v in u.items():
                if isinstance(v, dict) and isinstance(d.get(k), dict):
                    d[k] = deep_update(d.get(k, {}), v)
                else:
                    d[k] = v
            return d

        merged = deep_update(dict(self.default_config), self.module_config or {})
        if cli_overrides:
            merged = deep_update(merged, cli_overrides)
        return merged
    
    def get_section_paths(self) -> list:
        """
        Returns the list of section paths to optimize for the resume pipeline.
        Order of precedence:
        1. 'sections_to_optimize' from merged config (preferred)
        2. 'resume_sections' from merged config (fallback)
        3. If neither is present or is empty, infer all top-level sections from the YAML config (excluding 'sections' key if present)
        Always returns a list (may be empty if nothing found).
        """
        merged = self.merged_config
        section_paths = merged['content']['sections_to_optimize']
        if not section_paths or not isinstance(section_paths, list) or len(section_paths) == 0:
            print("[DEBUG] ConfigManager.get_section_paths: Couldn't find section_paths, defaulting to getting it from yaml")
            # Try to infer from YAML config (e.g., the structure of the resume)
            yaml_config = self.get_yaml_config('resume')
            # Try 'content' key if present (common in your config structure)
            resume_content = yaml_config.get('content', yaml_config)
            # Exclude 'sections' key if present
            section_paths = [k for k in resume_content.keys() if k != 'sections'] if isinstance(resume_content, dict) else []
        # Always return a list
        print(f"[DEBUG] ConfigManager.get_section_paths: {section_paths}")
        return section_paths
