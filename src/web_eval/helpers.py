# Copyright (c) Meta Platforms, Inc. and affiliates
"""
Helper functions for the DocAgent web application
"""

import re
from typing import Tuple, Optional, Dict, List

def parse_llm_score_from_text(text: str) -> Tuple[int, str]:
    """
    Parse score and explanation from LLM response text.
    
    Args:
        text: The raw LLM response text
        
    Returns:
        Tuple containing (score, explanation)
    """
    # Try to extract score from <score> tags
    score_match = re.search(r'<score>(\d+)</score>', text)
    if score_match:
        score = int(score_match.group(1))
    else:
        # Try looking for the score in various formats
        score_patterns = [
            r'score:?\s*(\d+)/5',
            r'score:?\s*(\d+)',
            r'rating:?\s*(\d+)/5',
            r'rating:?\s*(\d+)',
            r'(\d+)/5',
            r'I would rate this as a (\d+)',
            r'I would give this a (\d+)'
        ]
        
        for pattern in score_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                score = int(match.group(1))
                break
        else:
            # Default score if we can't find one
            score = 3
    
    # Limit score to 1-5 range
    score = max(1, min(5, score))
    
    # Extract explanation (everything except the score tags)
    explanation = re.sub(r'<score>\d+</score>', '', text).strip()
    
    # If explanation is very long, truncate it
    if len(explanation) > 500:
        explanation = explanation[:497] + "..."
    
    return score, explanation

from typing import Dict

def parse_google_style_docstring(docstring: str) -> Dict[str, str]:
    """
    A robust parser for Google-style docstrings that handles multiple possible
    labels for each section.
    
    Args:
        docstring: The docstring to parse
        
    Returns:
        Dictionary with canonical section names as keys and their content as values
    """
    # If docstring is empty or None, return empty sections
    if not docstring:
        return {key: "" for key in ['summary', 'description', 'parameters', 'attributes', 'returns', 'raises', 'examples']}

    # Define all recognized sections. The key is the canonical name (lowercase).
    # The value is a set of synonyms (also lowercase).
    SECTION_LABELS = {
        "summary":        {"summary:", "brief:", "overview:"},
        "description":    {"description:", "desc:", "details:", "long description:"},
        "parameters":     {"parameters:", "params:", "args:", "arguments:", "keyword args:", "keyword arguments:", "**kwargs:"},
        "attributes":     {"attributes:", "members:", "member variables:", "instance variables:", "properties:", "vars:", "variables:"},
        "returns":        {"returns:", "return:", "return value:", "return values:"},
        "raises":         {"raises:", "exceptions:", "throws:", "raise:", "exception:", "throw:"},
        "examples":       {"example:", "examples:", "usage:", "usage example:", "usage examples:", "example usage:"},
    }

    # Prepare a dictionary to hold the parsed content for each canonical key
    parsed_content = {key: [] for key in SECTION_LABELS.keys()}

    # Split by lines; if docstring uses Windows line endings, .splitlines() handles that gracefully
    lines = docstring.strip().splitlines()

    # -- 1) Fallback: no explicit sections at all in the entire docstring --
    #    If no recognized label appears anywhere, treat the first line as summary, rest as description.
    has_section_labels = False
    for line in lines:
        line_lower = line.strip().lower()
        for labels in SECTION_LABELS.values():
            for label in labels:
                if line_lower.startswith(label):
                    has_section_labels = True
                    break
            if has_section_labels:
                break
        if has_section_labels:
            break
            
    if len(lines) > 0 and not has_section_labels:
        parsed_content["summary"] = [lines[0]]
        if len(lines) > 1:
            parsed_content["description"] = lines[1:]
        # Convert lists to single strings
        return {key: "\n".join(value).strip() for key, value in parsed_content.items()}

    # We'll track the current section as we parse line by line
    current_section = None

    # -- 2) Partial Fallback for the first line only --
    #    If the first line doesn't match any known label, treat it as summary and then
    #    switch to "description" until an explicit label is found.
    first_line = lines[0].strip().lower() if lines else ""
    if not any(first_line.startswith(label) for labels in SECTION_LABELS.values() for label in labels):
        if lines:
            # Save first line as summary
            parsed_content["summary"] = [lines[0]]
            # Make the current section "description"
            current_section = "description"
            lines = lines[1:]  # We'll handle the rest below

    # -- 3) Main Parsing Loop --
    for line in lines:
        trimmed_line = line.strip().lower()
        matched_section = None

        # Check if this line begins with a known label (case-insensitive)
        # If so, we identify that as a new section.
        for canonical_name, synonyms in SECTION_LABELS.items():
            for synonym in synonyms:
                if trimmed_line.startswith(synonym):
                    matched_section = canonical_name
                    # Extract leftover text on the same line, after the label
                    leftover = line.strip()[len(synonym):].strip()
                    if leftover:
                        parsed_content[matched_section].append(leftover)
                    break
            if matched_section:
                break

        if matched_section is not None:
            # We found a new section header on this line
            current_section = matched_section
            # No need to append the header line to content - we've already handled any content after the label
        else:
            # Otherwise, continue appending lines to the current section
            if current_section is not None:
                parsed_content[current_section].append(line)

    # -- 4) Convert list of lines to single string, preserving line breaks --
    for section in parsed_content:
        parsed_content[section] = "\n".join(parsed_content[section]).strip()

    return parsed_content


def extract_docstring_component(docstring: str, component: str) -> Optional[str]:
    """
    Extract a specific component from a docstring using the robust parser.
    
    Args:
        docstring: The full docstring text
        component: The component to extract (summary, description, etc.)
        
    Returns:
        The extracted component text, or None if not found
    """
    if not docstring:
        return None
        
    # Map component name to canonical name used in the parser
    component_map = {
        'summary': 'summary',
        'description': 'description',
        # 'arguments': 'parameters',
        'params': 'parameters',
        'parameters': 'parameters',
        'attributes': 'attributes',
        'returns': 'returns',
        'raises': 'raises',
        'examples': 'examples'
    }
    
    canonical_component = component_map.get(component.lower(), component.lower())
    
    # Parse the docstring
    parsed = parse_google_style_docstring(docstring)
    
    # Return the requested component
    if canonical_component in parsed:
        return parsed[canonical_component] or None
    
    return None 