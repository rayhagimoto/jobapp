"""
YAML processing utilities that preserve formatting for resume optimization.
Extracted and adapted from experiment 04 for JobApp integration.
"""

import yaml
import copy
from pathlib import Path
from typing import Dict, Any, Tuple, List
from collections import OrderedDict
import re


def load_yaml_with_formatting(file_path: Path) -> Tuple[Dict[str, Any], str]:
    """Load YAML file and return both the parsed dict and raw text."""
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_yaml = f.read()
    parsed_yaml = yaml.safe_load(raw_yaml)
    return parsed_yaml, raw_yaml


def escape_latex_chars(text: str) -> str:
    """
    Escape LaTeX special characters in text while preserving LaTeX commands.
    """
    if not isinstance(text, str):
        return text

    # Define special characters and their escaped versions
    latex_special_chars = [
        (r'(?<!\\)%', r'\\%'),  # Unescaped % -> \%
        (r'(?<!\\)_', r'\\_'),  # Unescaped _ -> \_
        (r'(?<!\\)\$', r'\\$'), # Unescaped $ -> \$
        (r'(?<!\\)&', r'\\&'),  # Unescaped & -> \&
        (r'(?<!\\)#', r'\\#'),  # Unescaped # -> \#
    ]
    
    # Apply each replacement
    for pattern, replacement in latex_special_chars:
        text = re.sub(pattern, replacement, text)
    
    return text


def process_yaml_content(content: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively process YAML content to escape LaTeX special characters in values,
    leaving keys untouched.
    """
    if isinstance(content, dict):
        # Process only the values, not the keys
        return {k: process_yaml_content(v) for k, v in content.items()}
    elif isinstance(content, list):
        # Recursively process each item in the list
        return [process_yaml_content(item) for item in content]
    elif isinstance(content, str):
        # Escape only if the item is a string (a value)
        return escape_latex_chars(content)
    else:
        # Return all other types (int, bool, etc.) as is
        return content


def format_yaml_with_quotes(data: Dict[str, Any], exclude_sections: bool = False) -> str:
    """
    Format YAML output with proper quoting and LaTeX escaping.
    Keys remain unquoted, but all string values are quoted and LaTeX-escaped.
    For the 'sections' list, do NOT LaTeX-escape the items (output as plain strings).
    """
    # Custom YAML representer to handle quoting leaf values
    class QuotedYamlDumper(yaml.SafeDumper):
        pass
    
    def quoted_string_representer(dumper, data):
        # Only escape LaTeX characters in values, not keys
        # We can detect if this is a key by checking if it ends with ':'
        if data.endswith(':'):
            # This is a key, don't escape LaTeX characters
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style="'")
        else:
            # This is a value, escape LaTeX characters
            escaped_data = escape_latex_chars(data)
            return dumper.represent_scalar('tag:yaml.org,2002:str', escaped_data, style="'")
    
    QuotedYamlDumper.add_representer(str, quoted_string_representer)
    
    # Define section order
    ordered_sections = [
        "profile", "skills", "education", 
        "experience", "projects", "leadership", "awards"
    ]
    if not exclude_sections:
        ordered_sections.insert(0, "sections")
    
    # Make a deep copy so we don't mutate the original
    data_copy = copy.deepcopy(data)
    
    # For 'sections', ensure no LaTeX escaping is applied to the list items
    if "sections" in data_copy and isinstance(data_copy["sections"], list):
        data_copy["sections"] = [str(s) for s in data_copy["sections"]]
    
    # Create ordered dict
    ordered_data = OrderedDict()
    
    # Add sections in the specified order
    for section in ordered_sections:
        if section in data_copy and (not exclude_sections or section != 'sections'):
            ordered_data[section] = data_copy[section]
    
    # Add any remaining sections
    for key, value in data_copy.items():
        if key not in ordered_data and (not exclude_sections or key != 'sections'):
            ordered_data[key] = value
    
    # Generate YAML with all strings quoted and LaTeX escaped
    yaml_output = yaml.dump(
        dict(ordered_data), 
        Dumper=QuotedYamlDumper,
        default_flow_style=False,
        allow_unicode=True,
        indent=2,
        sort_keys=False
    )
    
    # Post-process to remove quotes from keys and fix any double-escaped backslashes
    lines = yaml_output.split('\n')
    processed_lines = []
    
    for line in lines:
        # Remove quotes from keys: 'key': becomes key:
        processed_line = re.sub(r"'([^']+)'(\s*:)", r'\1\2', line)
        # Remove any LaTeX escaping from keys (in case they got escaped)
        if ':' in processed_line and not processed_line.startswith(' '):
            key = processed_line.split(':', 1)[0]
            value = processed_line.split(':', 1)[1] if ':' in processed_line else ''
            # Remove any LaTeX escaping from the key
            key = key.replace('\\_', '_').replace('\\%', '%').replace('\\$', '$').replace('\\&', '&').replace('\\#', '#')
            processed_line = key + ':' + value
        # Fix any double-escaped backslashes in LaTeX commands
        processed_line = re.sub(r'\\\\(textcolor|textbf|emph|textit)', r'\\\1', processed_line)
        processed_lines.append(processed_line)
    
    return '\n'.join(processed_lines)


def extract_sections_from_raw_yaml(raw_yaml: str, include_paths: List[str] = None) -> str:
    """
    Extract specific sections from raw YAML text while preserving formatting.
    
    This function works with the original YAML text to preserve:
    - Single quotes around strings
    - Original spacing and indentation
    - Section order
    - Comment formatting
    """
    if include_paths is None:
        include_paths = [
            "profile",
            "education[Rice University]", 
            "skills",
            "experience[Susquehanna]",
            "projects[Anomaly]"
        ]
    
    lines = raw_yaml.split('\n')
    extracted_lines = []
    current_section = None
    section_indent = 0
    capturing = False
    
    # Parse the YAML to understand structure while preserving formatting
    parsed = yaml.safe_load(raw_yaml)
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip empty lines and comments at the top level when not capturing
        if not capturing and (not stripped or stripped.startswith('#')):
            continue
            
        # Detect section headers (top-level keys)
        if line and not line.startswith(' ') and ':' in line:
            section_name = line.split(':')[0].strip()
            current_section = section_name
            section_indent = len(line) - len(line.lstrip())
            
            # Check if we should capture this section
            if should_include_section(section_name, include_paths, parsed):
                capturing = True
                extracted_lines.append(line)
            else:
                capturing = False
                
        elif capturing:
            # We're inside a section we want to capture
            current_indent = len(line) - len(line.lstrip()) if line.strip() else 0
            
            # If we hit another top-level section, stop capturing
            if line and current_indent <= section_indent and ':' in line and not line.startswith(' '):
                # Check if this new section should be captured
                section_name = line.split(':')[0].strip()
                current_section = section_name
                if should_include_section(section_name, include_paths, parsed):
                    extracted_lines.append(line)
                else:
                    capturing = False
            else:
                # Add line if we're still in the captured section
                extracted_lines.append(line)
    
    return '\n'.join(extracted_lines)


def should_include_section(section_name: str, include_paths: List[str], parsed_yaml: Dict[str, Any]) -> bool:
    """Helper function to determine if a section should be included based on paths."""
    # Check direct section match
    if section_name in include_paths:
        return True
        
    # Check for section[filter] matches
    for path in include_paths:
        if '[' in path and path.endswith(']'):
            section_path, filter_part = path.split('[', 1)
            filter_value = filter_part.rstrip(']')
            
            if section_name == section_path:
                # Check if filter value appears in any item in this section
                section_data = parsed_yaml.get(section_name, [])
                if isinstance(section_data, list):
                    for item in section_data:
                        if isinstance(item, dict):
                            item_str = ' '.join(str(v) for v in item.values())
                            if filter_value in item_str:
                                return True
                                
    # Check for dot notation paths
    for path in include_paths:
        if '.' in path:
            section, _ = path.split('.', 1)
            if section_name == section:
                return True
                
    return False


def extract_by_path_advanced(data: dict, path: str):
    """
    Extract value from nested dictionary using dot notation and bracket notation.
    Supports e.g. 'profile.description', 'education[Rice]'.
    For bracket notation, returns the first dict in a list where any value contains the filter string.
    """
    cur = data
    for part in re.split(r'\.(?![^\[]*\])', path):
        m = re.match(r'([\w_]+)(\[(.*?)\])?', part)
        if not m:
            return None
        key = m.group(1)
        cur = cur.get(key) if isinstance(cur, dict) else None
        if cur is None:
            return None
        if m.group(3):
            # Bracket notation, e.g., education[Rice]
            idx = m.group(3)
            if isinstance(cur, dict):
                cur = cur.get(idx)
            elif isinstance(cur, list):
                # Return first dict where any value contains idx
                for item in cur:
                    if isinstance(item, dict):
                        if any(idx in str(v) for v in item.values()):
                            cur = item
                            break
                else:
                    return None
            else:
                return None
            if cur is None:
                return None
    return cur


def strip_yaml_code_block(text: str) -> str:
    """
    Remove triple-backtick YAML code block markers from a string, if present.
    """
    if not text:
        return ''
    # Remove ```yaml ... ``` or ``` ... ```
    return re.sub(r'```yaml|```', '', text).strip()


def set_by_path(data: Dict[str, Any], path: str, value: Any):
    """Set value in nested dictionary using dot notation path."""
    if '.' not in path:
        data[path] = value
        return
        
    parts = path.split('.')
    current = data
    
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
        
    current[parts[-1]] = value


def format_current_sections(resume_dict: Dict[str, Any], include_paths: List[str] = None, 
                          raw_yaml: str = None) -> str:
    """
    Format the current sections that need optimization based on specified paths.
    
    Args:
        resume_dict: The full resume dictionary (for backward compatibility)
        include_paths: List of paths to include
        raw_yaml: The original raw YAML text (preserves formatting)
    """
    if raw_yaml:
        # Use the new formatting-preserving approach
        return extract_sections_from_raw_yaml(raw_yaml, include_paths)
    
    # Fallback to the original approach for backward compatibility
    if include_paths is None:
        # Default paths for backward compatibility
        include_paths = [
            "profile",
            "education[Rice University]", 
            "skills",
            "experience[Susquehanna]"
        ]
    
    current_sections = {}
    
    for path in include_paths:
        # Handle array filtering syntax: section[filter_value]
        if '[' in path and path.endswith(']'):
            section_path, filter_part = path.split('[', 1)
            filter_value = filter_part.rstrip(']')
            
            section_data = extract_by_path_advanced(resume_dict, section_path)
            if isinstance(section_data, list):
                # Find matching items in the list
                filtered_items = []
                for item in section_data:
                    if isinstance(item, dict):
                        # Check if filter_value appears in any field of the item
                        item_str = ' '.join(str(v) for v in item.values())
                        if filter_value in item_str:
                            filtered_items.append(item)
                
                if filtered_items:
                    set_by_path(current_sections, section_path, filtered_items)
        
        # Handle dot notation paths
        elif '.' in path:
            section, field = path.split('.', 1)
            value = extract_by_path_advanced(resume_dict, path)
            if value is not None:
                if section not in current_sections:
                    current_sections[section] = {}
                set_by_path(current_sections, path, value)
        
        # Handle top-level sections
        else:
            value = extract_by_path_advanced(resume_dict, path)
            if value is not None:
                current_sections[path] = value
    
    # Convert to YAML format with proper quoting and LaTeX escaping
    return format_yaml_with_quotes(current_sections)


def apply_selective_resume_updates(
    resume_dict: Dict[str, Any], 
    updates: Dict[str, Any],
    allowed_paths: List[str]
) -> None:
    """
    Apply selective updates to the resume dictionary based on allowed paths.
    
    Args:
        resume_dict: The resume dictionary to update
        updates: Dictionary containing updates to apply
        allowed_paths: List of paths that are allowed to be updated
    """
    for path in allowed_paths:
        # Handle array filtering syntax: section[filter_value]
        if '[' in path and path.endswith(']'):
            section_path, filter_part = path.split('[', 1)
            filter_value = filter_part.rstrip(']')
            
            # Get updates for this section
            section_updates = updates.get(section_path, [])
            if not section_updates:
                continue
                
            # Get current section data
            section_data = resume_dict.get(section_path, [])
            if not isinstance(section_data, list):
                continue
                
            # Update matching items
            for i, item in enumerate(section_data):
                if isinstance(item, dict):
                    item_str = ' '.join(str(v) for v in item.values())
                    if filter_value in item_str:
                        # Find matching update
                        for update in section_updates:
                            if isinstance(update, dict):
                                update_str = ' '.join(str(v) for v in update.values())
                                if filter_value in update_str:
                                    # Apply update
                                    section_data[i].update(update)
                                    break
        
        # Handle dot notation paths
        elif '.' in path:
            section, field = path.split('.', 1)
            if section in updates:
                section_updates = updates[section]
                if isinstance(section_updates, dict):
                    if section not in resume_dict:
                        resume_dict[section] = {}
                    if field in section_updates:
                        resume_dict[section][field] = section_updates[field]
        
        # Handle top-level sections
        else:
            if path in updates:
                resume_dict[path] = updates[path]


def extract_allowed_updates_only(
    updates: Dict[str, Any], 
    allowed_paths: List[str]
) -> Dict[str, Any]:
    """
    Extract only the updates that are allowed based on the paths.
    
    Args:
        updates: Dictionary containing all updates
        allowed_paths: List of paths that are allowed to be updated
        
    Returns:
        Dictionary containing only the allowed updates
    """
    allowed_updates = {}
    
    for path in allowed_paths:
        # Handle array filtering syntax: section[filter_value]
        if '[' in path and path.endswith(']'):
            section_path, _ = path.split('[', 1)
            if section_path in updates:
                allowed_updates[section_path] = updates[section_path]
        
        # Handle dot notation paths
        elif '.' in path:
            section, field = path.split('.', 1)
            if section in updates:
                section_updates = updates[section]
                if isinstance(section_updates, dict):
                    if section not in allowed_updates:
                        allowed_updates[section] = {}
                    if field in section_updates:
                        allowed_updates[section][field] = section_updates[field]
        
        # Handle top-level sections
        else:
            if path in updates:
                allowed_updates[path] = updates[path]
    
    return allowed_updates 