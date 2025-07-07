import re
import unicodedata

def to_pascal_case_preserve_acronyms(text):
    """
    Converts a string to PascalCase, preserving acronyms and existing PascalCase words.
    Also sanitizes the text for safe filename usage by removing problematic characters.
    Handles all Unicode characters, symbols, and edge cases robustly.
    
    Example: 'senior ML engineer' -> 'SeniorMLEngineer'
    Example: 'DataAnnotation' -> 'DataAnnotation'
    Example: 'myGwork - LGBTQ+ Business Community' -> 'MyGworkLGBTQBusinessCommunity'
    Example: 'AT&T Corporation' -> 'ATTCorporation'
    Example: "L'Oréal Paris" -> 'LOrealParis'
    Example: 'Microsoft Corporation [MSFT]' -> 'MicrosoftCorporation'
    Example: 'π Industries' -> 'PiIndustries'
    """
    if not text:
        return ""
    
    # Special symbol mappings for common symbols that should be preserved as words
    symbol_mappings = {
        'π': 'Pi',
        '∞': 'Infinity', 
        'Δ': 'Delta',
        'Σ': 'Sigma',
        'Α': 'Alpha',
        'Β': 'Beta', 
        'Γ': 'Gamma',
        'Θ': 'Theta',
        'Λ': 'Lambda',
        'Μ': 'Mu',
        'Ν': 'Nu',
        'Ξ': 'Xi',
        'Ο': 'Omicron',
        'Π': 'Pi',
        'Ρ': 'Rho',
        'Τ': 'Tau',
        'Υ': 'Upsilon',
        'Φ': 'Phi',
        'Χ': 'Chi',
        'Ψ': 'Psi',
        'Ω': 'Omega',
        '€': 'Euro',
        '¥': 'Yen',
        '£': 'Pound',
        '$': 'Dollar',
        '©': 'Copyright',
        '®': 'Registered',
        '™': 'Trademark',
        '°': 'Degree',
    }
    
    # Special handling for phone numbers - preserve all digits better
    # Convert patterns like "+1 (555) 123-4567" to "15551234567"
    text = re.sub(r'\+(\d+)\s*\((\d+)\)\s*(\d+)-(\d+)', r'\1\2\3\4', text)
    
    # Apply symbol mappings more carefully to avoid duplication
    # Handle symbol + word combinations first (these take priority)
    text = re.sub(r'\$\s*Dollar\b', 'Dollar', text, flags=re.IGNORECASE)
    text = re.sub(r'€\s*uro\b', 'Euro', text, flags=re.IGNORECASE)
    text = re.sub(r'¥\s*en\b', 'Yen', text, flags=re.IGNORECASE)
    text = re.sub(r'Α\s*lpha\b', 'Alpha', text, flags=re.IGNORECASE)
    text = re.sub(r'£\s*ound\b', 'Pound', text, flags=re.IGNORECASE)
    
    # Handle symbols at the end of numbers (e.g., "360°" -> "Degree")
    text = re.sub(r'\d+°\s*', 'Degree ', text)
    
    # Now handle remaining standalone symbols (only if not already processed)
    if '$' in text and 'Dollar' not in text:
        text = text.replace('$', ' Dollar ')
    if '°' in text:
        text = text.replace('°', ' Degree ')
    
    # Handle other symbols normally
    remaining_symbols = {'π', '∞', 'Δ', 'Σ', 'Β', 'Γ', 'Θ', 'Λ', 'Μ', 'Ν', 'Ξ', 'Ο', 'Π', 'Ρ', 'Τ', 'Υ', 'Φ', 'Χ', 'Ψ', 'Ω', '©', '®', '™'}
    for symbol in remaining_symbols:
        if symbol in text:
            text = text.replace(symbol, f' {symbol_mappings[symbol]} ')
    
    # Special handling for Cyrillic and non-Latin scripts within parentheses
    # Extract Latin content from parentheses if the main text is non-Latin
    paren_content = re.search(r'\(([^)]*[A-Za-z][^)]*)\)', text)
    if paren_content:
        # Check if the text outside parentheses is mostly non-Latin
        text_outside = re.sub(r'\([^)]*\)', '', text).strip()
        if text_outside and not re.search(r'[A-Za-z]', text_outside):
            # If outside text has no Latin letters, use content from parentheses
            text = paren_content.group(1)
        else:
            # Normal case: remove parentheses content
            text = re.sub(r"\([^)]*\)", "", text)
    else:
        # Remove parentheses and their contents
        text = re.sub(r"\([^)]*\)", "", text)
    
    # Remove square brackets and their contents  
    text = re.sub(r"\[[^\]]*\]", "", text)
    
    # Remove apostrophes entirely (don't replace with space to avoid word splitting)
    text = re.sub(r"[''`]", "", text)
    
    # Replace problematic filename characters with spaces
    # Handle @ symbol in email addresses specially 
    text = re.sub(r'@([a-z]+)\.', r' \1 ', text)  # "@corp.com" -> " corp "
    text = re.sub(r"[&+/\\:*?<>|\"@]+", " ", text)
    
    # Replace hyphens, commas, periods, and other separators with spaces
    # But handle special cases like "C3.ai" 
    # First protect patterns like "word.ai" from period replacement
    text = re.sub(r'(\w)\.([a-z]{2,3})\b', r'\1\2', text)  # C3.ai -> C3ai
    text = re.sub(r"[-,.;]+", " ", text)
    
    # Convert accented characters to ASCII equivalents (e.g., é -> e, ñ -> n)
    # But preserve the special symbols we mapped above
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    
    # Remove any remaining non-alphanumeric characters except spaces
    # This will remove emojis, non-Latin scripts, etc. while preserving our mapped symbols
    text = re.sub(r"[^A-Za-z0-9 ]+", "", text)
    
    # Normalize whitespace - replace multiple spaces, tabs, newlines with single space
    text = re.sub(r"\s+", " ", text)
    
    # Split into words and process
    words = text.strip().split()
    result = []
    for word in words:
        if word.islower():
            result.append(word.capitalize())
        else:
            result.append(word)
    
    # Join and ensure first character is uppercase for PascalCase
    final_result = ''.join(result)
    if final_result and final_result[0].islower():
        final_result = final_result[0].upper() + final_result[1:]
    
    return final_result


def clean_location(location):
    """
    Cleans a location string for use in filenames, handling international locations,
    accented characters, remote work patterns, and complex location formatting.
    
    Examples:
    'San Francisco, CA' -> 'SanFranciscoCA'
    'São Paulo, Brazil' -> 'SaoPauloBrazil'
    'Washington, D.C.' -> 'WashingtonDC'
    'Remote - US' -> 'RemoteUS'
    'München, Germany' -> 'MunchenGermany'
    'Seattle, WA / San Francisco, CA' -> 'SeattleWASanFranciscoCA'
    """
    if not location or location.strip() == "":
        return "UnknownLocation"
    
    text = location.strip()
    
    # Handle common location abbreviations and normalizations first
    location_mappings = {
        # Washington D.C. variants
        'D.C.': 'DC',
        'D C': 'DC',
        'District of Columbia': 'DistrictOfColumbia',
        
        # Common abbreviations
        'St.': 'St',
        'Mt.': 'Mt', 
        'Ft.': 'Ft',
        'N.Y.': 'NY',
        'L.A.': 'LA',
        
        # Remote work patterns  
        'Work from Home': 'WorkFromHome',
        'WFH': 'WFH',
        'Fully Remote': 'FullyRemote',
        '100%': '100Percent',
        
        # Direction abbreviations
        'N.': 'North',
        'S.': 'South', 
        'E.': 'East',
        'W.': 'West',
    }
    
    # Apply location-specific mappings
    for old, new in location_mappings.items():
        text = text.replace(old, new)
    
    # Handle accented characters properly - map specific characters that commonly cause issues
    accent_mappings = {
        'ã': 'a', 'à': 'a', 'á': 'a', 'â': 'a', 'ä': 'a', 'å': 'a',
        'ẽ': 'e', 'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
        'ĩ': 'i', 'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
        'õ': 'o', 'ò': 'o', 'ó': 'o', 'ô': 'o', 'ö': 'o', 'ø': 'o',
        'ũ': 'u', 'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
        'ñ': 'n', 'ç': 'c',
        'ł': 'l', 'ß': 'ss',
        # Capital versions
        'Ã': 'A', 'À': 'A', 'Á': 'A', 'Â': 'A', 'Ä': 'A', 'Å': 'A',
        'È': 'E', 'É': 'E', 'Ê': 'E', 'Ë': 'E',
        'Ì': 'I', 'Í': 'I', 'Î': 'I', 'Ï': 'I',
        'Ò': 'O', 'Ó': 'O', 'Ô': 'O', 'Ö': 'O', 'Ø': 'O',
        'Ù': 'U', 'Ú': 'U', 'Û': 'U', 'Ü': 'U',
        'Ñ': 'N', 'Ç': 'C', 'Ł': 'L',
    }
    
    # Apply accent mappings character by character
    for accented, plain in accent_mappings.items():
        text = text.replace(accented, plain)
    
    # Handle non-Latin scripts by extracting Latin text from mixed content
    # Look for Latin text within parentheses or after commas
    non_latin_extraction_done = False
    if re.search(r'[^\x00-\x7F]', text):  # Contains non-ASCII characters
        # Try to extract Latin parts
        latin_parts = []
        
        # Extract parenthetical Latin content
        paren_matches = re.findall(r'\(([^)]*[A-Za-z][^)]*)\)', text)
        for match in paren_matches:
            if re.search(r'[A-Za-z]', match):  # Contains Latin letters
                latin_parts.append(match.strip())
        
        # Extract Latin content after commas (e.g., "北京, China" -> "China")
        comma_parts = [part.strip() for part in text.split(',')]
        for part in comma_parts:
            if re.search(r'^[A-Za-z\s]+$', part.strip()):  # Only Latin letters and spaces
                latin_parts.append(part.strip())
        
        # If we found Latin parts, use them
        if latin_parts:
            text = ' '.join(latin_parts)
            non_latin_extraction_done = True
        else:
            # Remove non-Latin characters entirely
            text = re.sub(r'[^\x00-\x7F]+', '', text).strip()
            if not text:
                return "InternationalLocation"
    
    # Only remove parentheses if we didn't already extract content from non-Latin text
    if not non_latin_extraction_done:
        # For normal locations, preserve parenthetical content but remove the parentheses
        # e.g., "New York (Remote/Hybrid)" -> "New York Remote/Hybrid"
        text = re.sub(r'\(([^)]*)\)', r' \1 ', text)
    else:
        # Remove parentheses and their contents since we already extracted what we need
        text = re.sub(r'\([^)]*\)', '', text)
    
    # Handle multi-location separators (/, or, and, ;, +)
    text = re.sub(r'\s*[/;+]\s*', ' ', text)  # Replace separators with spaces
    text = re.sub(r'\s+(or|and)\s+', ' ', text)  # Replace "or"/"and" with spaces
    
    # Remove square brackets and their contents  
    text = re.sub(r"\[[^\]]*\]", "", text)
    
    # Remove apostrophes entirely (don't replace with space)
    text = re.sub(r"[''`]", "", text)
    
    # Replace problematic filename characters with spaces
    text = re.sub(r"[&+\\:*?<>|\"]+", " ", text)
    
    # Replace commas, periods, hyphens with spaces 
    text = re.sub(r"[-,.;]+", " ", text)
    
    # Remove any remaining non-alphanumeric characters except spaces
    text = re.sub(r"[^A-Za-z0-9 ]+", "", text)
    
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    
    # Convert to PascalCase
    if not text:
        return "UnknownLocation"
    
    # Split into words and capitalize each
    words = text.split()
    result = []
    for word in words:
        if word.islower():
            result.append(word.capitalize())
        else:
            result.append(word)
    
    # Join without spaces for PascalCase
    final_result = ''.join(result)
    
    # Ensure first character is uppercase
    if final_result and final_result[0].islower():
        final_result = final_result[0].upper() + final_result[1:]
    
    return final_result if final_result else "UnknownLocation"


def generate_base_filename(job_title, company, location):
    """
    Generates the base filename: Company_JobTitle_Location (PascalCase, underscores).
    """
    company_part = to_pascal_case_preserve_acronyms(company) if company else "NoCompany"
    title_part = to_pascal_case_preserve_acronyms(job_title) if job_title else "NoJobTitle"
    location_part = clean_location(location) if location else "NoLocation"
    return f"{company_part}_{title_part}_{location_part}"


def get_resume_filenames(your_name, job_title, company, location, match_score=None):
    """
    Generates a consistent set of filenames for a resume and its related files
    based on job details. The directory includes the match score for sorting,
    but the final PDF/YAML filenames do not.

    Returns:
        A dictionary containing the base filename, directory name, and full paths
        for the PDF and YAML files.
    """
    base_name = generate_base_filename(job_title, company, location)
    your_name_sanitized = your_name.replace(' ', '_')

    # Filename for the actual resume files (PDF, YAML) - without the score
    resume_filename_base = f"{your_name_sanitized}_{base_name}"

    # Directory name - includes the score for sorting purposes
    if match_score is not None:
        try:
            score = int(match_score)
            directory_name = f"{score}_{base_name}"
        except (ValueError, TypeError):
            directory_name = base_name
    else:
        directory_name = base_name

    return {
        'base': resume_filename_base,
        'dir': directory_name,
        'pdf': f"{directory_name}/{resume_filename_base}.pdf",
        'yaml': f"{directory_name}/{resume_filename_base}.yaml"
    }
