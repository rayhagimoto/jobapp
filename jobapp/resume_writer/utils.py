"""Utility functions for resume writer module."""

from dataclasses import dataclass
from typing import List, Optional, Dict
import re

@dataclass
class KeywordAnalysis:
    """Class to hold keyword analysis data."""
    skill: str
    job_relevance: int
    evidence: str
    quote: str
    confidence: int
    priority: float
    method: str
    implementation: str
    target: Optional[str] = None

def parse_keyword_analysis(analysis_text: str) -> List[KeywordAnalysis]:
    """Parse the keyword analysis text into a list of KeywordAnalysis objects."""
    analyses = []
    current_analysis = {}

    # Split the text into blocks separated by blank lines
    blocks = analysis_text.strip().split('\n\n')

    for block in blocks:
        if not block.strip():
            continue

        # Parse each line in the block
        lines = block.strip().split('\n')
        current_analysis = {}

        for line in lines:
            if not line.strip():
                continue

            # Robustly handle lines with and without a colon
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().strip('"')

                if key == 'JOB_RELEVANCE':
                    current_analysis[key.lower()] = int(value)
                elif key == 'CONFIDENCE':
                    current_analysis[key.lower()] = int(value)
                elif key == 'PRIORITY':
                    current_analysis[key.lower()] = float(value)
                else:
                    current_analysis[key.lower()] = value

        # Create KeywordAnalysis object
        if current_analysis:
            analyses.append(KeywordAnalysis(
                skill=current_analysis.get('skill', ''),
                job_relevance=current_analysis.get('job_relevance', 0),
                evidence=current_analysis.get('evidence', ''),
                quote=current_analysis.get('quote', ''),
                confidence=current_analysis.get('confidence', 0),
                priority=current_analysis.get('priority', 0.0),
                method=current_analysis.get('method', ''),
                implementation=current_analysis.get('implementation', ''),
                target=current_analysis.get('target', None)
            ))

    return analyses

def get_unique_keywords(analysis_text: str) -> set:
    """Extract unique keywords from the analysis text."""
    analyses = parse_keyword_analysis(analysis_text)
    return {analysis.skill for analysis in analyses}

def parse_bullet_changes(response_text: str) -> List[Dict]:
    """Parse bullet point changes from EditorPrompt4 response.
    Returns list of dicts with keys:
    - original: str
    - proposed: str
    - change: bool
    """
    changes = []
    blocks = response_text.split("BULLET_")

    for block in blocks:
        if not block.strip():
            continue

        # Extract the relevant fields using basic string parsing
        original_match = re.search(r"ORIGINAL:\s*(.+?)(?=PROPOSED:|$)", block, re.DOTALL)
        proposed_match = re.search(r"PROPOSED:\s*(.+?)(?=CHANGE:|$)", block, re.DOTALL)
        change_match = re.search(r"CHANGE:\s*(true|false)", block, re.IGNORECASE)

        if original_match and proposed_match and change_match:
            changes.append({
                "original": original_match.group(1).strip(),
                "proposed": proposed_match.group(1).strip(),
                "change": change_match.group(1).lower() == "true"
            })

    return changes

def clean_yaml_from_llm(raw_string: str) -> str:
    """
    Extracts a YAML block from a raw string, cleaning it of common LLM artifacts.
    Handles YAML wrapped in ```yaml ... ``` or just raw YAML.
    """
    # Find the start of the YAML content
    match = re.search(r'```yaml\n(.*?)\n```', raw_string, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Fallback for raw YAML without backticks, find the first likely key
    potential_starts = [
        'PROFILE_OPTIMIZATION_PLAN:', 'FINAL_RESUME_YAML:', 'YAML_MARKDOWN:',
        'version:', 'sections:', 'metadata:', 'changelog:'
    ]
    
    cleaned_string = raw_string
    for start in potential_starts:
        if start in cleaned_string:
            cleaned_string = cleaned_string[cleaned_string.find(start):]
            break
            
    # Remove any leading/trailing conversational text that might have been missed
    return cleaned_string.strip()

def parse_llm_yaml_to_dict(raw_string: str) -> dict:
    """
    Cleans and parses a YAML string from an LLM response into a dictionary.
    Returns an empty dict if parsing fails.
    """
    import yaml
    cleaned_yaml = clean_yaml_from_llm(raw_string)
    try:
        return yaml.safe_load(cleaned_yaml)
    except yaml.YAMLError:
        return {} # Return empty dict on failure

def parse_refinement_response(raw_string: str):
    """
    Parses the two-block response from the refinement agent.
    
    Returns a tuple containing (final_resume_dict, changelog_dict).
    Returns (None, None) if parsing fails.
    """
    import yaml
    
    # Use regex to find all YAML blocks
    yaml_blocks = re.findall(r'```yaml\n(.*?)\n```', raw_string, re.DOTALL)
    
    if len(yaml_blocks) < 2:
        return None, None # Not enough blocks found

    final_resume_str = yaml_blocks[0]
    changelog_str = yaml_blocks[1]
    
    try:
        final_resume_dict = yaml.safe_load(final_resume_str)
        changelog_dict = yaml.safe_load(changelog_str)
        return final_resume_dict, changelog_dict
    except yaml.YAMLError:
        return None, None

def format_changelog_to_markdown(changelog_dict: Dict) -> str:
    """Generates a markdown changelog from the structured changelog dictionary."""
    content = ["# Changelog"]
    if not isinstance(changelog_dict, dict):
        return ""

    # Handle feedback changes from validator
    changes = changelog_dict.get('CHANGES_MADE', {})
    if changes:
        content.append("\n## Validator Feedback Changes")
        # The keys are SECTION_1, SECTION_2 etc., so we should sort them
        sorted_keys = sorted(changes.keys())
        for section_key in sorted_keys:
            change_data = changes[section_key]
            if 'LOCATION' in change_data:
                content.append(f"\n### {change_data.get('LOCATION')}")
                content.append(f"**ORIGINAL:**\n```\n{change_data.get('ORIGINAL', '')}\n```")
                content.append(f"**FINAL:**\n```\n{change_data.get('NEW', '')}\n```")
                rationale = change_data.get('RATIONALE', {})
                concern = rationale.get('VALIDATOR_CONCERN', 'N/A')
                fix = rationale.get('PROPOSED_FIX', 'N/A')
                content.append(f"**REASON:** {concern} - **FIX:** {fix}")
    
    return "\n".join(content)

def format_keywords_to_markdown(analysis_text: str) -> str:
    """Formats the keyword analysis into a readable markdown file content."""
    # This function is being renamed from format_keyword_analysis for clarity
    analyses = parse_keyword_analysis(analysis_text)

    # De-duplicate analyses, keeping the one with the highest priority for each skill
    unique_analyses = {}
    for analysis in analyses:
        if analysis.skill not in unique_analyses or analysis.priority > unique_analyses[analysis.skill].priority:
            unique_analyses[analysis.skill] = analysis

    # Sort unique analyses by priority
    sorted_analyses = sorted(unique_analyses.values(), key=lambda x: x.priority, reverse=True)

    # Build the output string
    output = []

    # Header
    output.append("# Job Description Keywords\n")

    # Keywords section with relevance scores
    output.append("## Keywords by Priority")
    for analysis in sorted_analyses:
        if analysis.skill: # Ensure skill is not empty
            output.append(f"- {analysis.skill}\t\tRelevance: {analysis.job_relevance}/10")

    output.append("\n## Detailed Analysis\n")

    # Add detailed analysis for each keyword
    for analysis in sorted_analyses:
        if not analysis.skill: # Skip empty analysis blocks
            continue
        output.append(f"### {analysis.skill}")
        output.append(f"- **Job Relevance**: {analysis.job_relevance}/10")
        output.append(f"- **Evidence**: {analysis.evidence}")
        output.append(f"- **Supporting Quote**: {analysis.quote}")  # No extra quotes - use as-is
        output.append(f"- **Confidence**: {analysis.confidence}/10")
        output.append(f"- **Priority**: {int(analysis.priority)}")  # Format as integer here too
        output.append(f"- **Implementation Method**: {analysis.method}")
        # For implementation suggestions, strip any existing quotes and don't add new ones
        implementation = analysis.implementation.strip('"')
        output.append(f"- **Suggested Implementation**: {implementation}")
        if analysis != sorted_analyses[-1]:  # Only add blank line if not the last analysis
            output.append("")  # Add blank line between sections

    return "\n".join(output).rstrip()

def parse_formatting_response(response_content: str) -> str:
    """
    General-purpose utility to extract YAML content from an LLM response, handling code blocks.
    Returns the YAML string, or the whole response as fallback.
    """
    import re
    if not isinstance(response_content, str):
        return ""
    # Pattern to find yaml code blocks, accounts for optional 'yaml' language specifier
    pattern = r"```(?:yaml)?\s*\n(.*?)\n```"
    match = re.search(pattern, response_content, re.DOTALL)
    if match:
        # If a yaml code block is found, return its content
        return match.group(1).strip()
    # Fallback: assume the whole response is yaml
    return response_content.strip()