"""
Fuzzy finding utilities for JobApp.

This module provides fuzzy matching capabilities for jobs and interactive selection
using fzf when available.
"""

import subprocess
from typing import List, Dict, Any, Tuple, Optional, Callable


def fuzzy_match_jobs(jobs: List[Dict[str, Any]], query: str) -> List[Tuple[int, Dict[str, Any]]]:
    """
    Returns a list of (index, job) tuples where the query matches job title, company, or location.
    Uses simple case-insensitive substring matching.
    
    Args:
        jobs: List of job dictionaries from Google Sheets
        query: Search query string
        
    Returns:
        List of (index, job) tuples matching the query
    """
    q = query.lower()
    results = []
    for i, job in enumerate(jobs):
        haystack = f"{job.get('JobTitle','')} {job.get('Company','')} {job.get('Location','')}".lower()
        if all(word in haystack for word in q.split()):
            results.append((i, job))
    return results


def select_with_fzf(options: List[Any], display_fn: Callable[[Any], str]) -> Optional[Any]:
    """
    Use fzf for interactive selection if available, otherwise return None.
    
    Args:
        options: List of options to select from
        display_fn: Function to convert each option to a display string
        
    Returns:
        Selected option or None if fzf is not available or user cancelled
    """
    try:
        fzf = subprocess.Popen(['fzf', '--ansi'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    except FileNotFoundError:
        return None
    
    input_str = '\n'.join([display_fn(opt) for opt in options])
    out, _ = fzf.communicate(input_str.encode('utf-8'))
    
    if not out:
        return None
    
    selected = out.decode('utf-8').strip()
    for opt in options:
        if display_fn(opt) == selected:
            return opt
    return None


def interactive_job_selection(matches: List[Tuple[int, Dict[str, Any]]]) -> Optional[Tuple[int, Dict[str, Any]]]:
    """
    Interactive job selection using fzf if available, fallback to numbered menu.
    
    Args:
        matches: List of (index, job) tuples to select from
        
    Returns:
        Selected (index, job) tuple or None if cancelled
    """
    if not matches:
        return None
    
    if len(matches) == 1:
        return matches[0]
    
    print(f"[INFO] Found {len(matches)} matching jobs:")
    
    # Try fzf first
    def display_job(opt):
        i, job = opt
        match_score = job.get('MatchScore', 'N/A')
        applied = job.get('Applied', '').lower()
        status_icon = "✅" if applied == "true" else "⏳"
        return f"{status_icon} [{match_score:>3}] {job.get('JobTitle','')} at {job.get('Company','')} ({job.get('Location','')})"
    
    selected = select_with_fzf(matches, display_job)
    
    if selected is not None:
        return selected
    
    # Fallback: print numbered menu
    for i, (idx, job) in enumerate(matches):
        match_score = job.get('MatchScore', 'N/A')
        applied = job.get('Applied', '').lower()
        status_icon = "✅" if applied == "true" else "⏳"
        print(f"  {i+1}. {status_icon} [{match_score:>3}] {job.get('JobTitle','')} at {job.get('Company','')} ({job.get('Location','')})")
    
    try:
        choice = int(input(f"Select a job [1-{len(matches)}]: ")) - 1
        if 0 <= choice < len(matches):
            return matches[choice]
        else:
            print("[ERROR] Invalid selection.")
            return None
    except (ValueError, KeyboardInterrupt):
        print("[ERROR] Invalid selection or cancelled by user.")
        return None


def fuzzy_find_job(jobs: List[Dict[str, Any]], query: str) -> Optional[Dict[str, Any]]:
    """
    Complete fuzzy find workflow: search, match, and interactively select a job.
    
    Args:
        jobs: List of job dictionaries from Google Sheets
        query: Search query string
        
    Returns:
        Selected job dictionary or None if no match/cancelled
    """
    matches = fuzzy_match_jobs(jobs, query)
    
    if not matches:
        print(f"[ERROR] No jobs found matching query: '{query}'")
        return None
    
    selection = interactive_job_selection(matches)
    if selection is None:
        return None
    
    idx, selected_job = selection
    print(f"[INFO] Selected job: {selected_job.get('JobTitle','')} at {selected_job.get('Company','')}")
    return selected_job 