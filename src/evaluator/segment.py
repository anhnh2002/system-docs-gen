# Copyright (c) Meta Platforms, Inc. and affiliates
import re

def parse_google_style_docstring(docstring):
    """
    A robust parser for Google-style docstrings that have multiple possible
    labels for each section.

    For example, any of the lines in EXAMPLE_LABELS indicates the start of the "examples" section.
    """

    # Define all recognized sections. The key is the canonical name (lowercase).
    # The value is a set of synonyms (also lowercase).
    SECTION_LABELS = {
        "summary":        {"summary:", "short description:", "brief:", "overview:"},
        "description":    {"description:", "desc:", "details:", "detailed description:", "long description:"},
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

    # -- 2) Partial Fallback for the first line only --
    #    If the first line doesn't match any known label, treat it as summary and then
    #    switch to "description" until an explicit label is found.
    current_section = None  # keep track of which section we're in
    
    first_line = lines[0].strip().lower() if lines else ""
    if not any(first_line.startswith(label) for labels in SECTION_LABELS.values() for label in labels):
        if lines:
            # Save first line as summary
            parsed_content["summary"] = [lines[0]]
            # Make the current section "description"
            current_section = "description"
            lines = lines[1:]  # We'll handle the rest below

    for line in lines:
        # We'll do a trimmed, lowercase version of the line to check for a header
        # but keep original_line if you want to preserve original indentation or case.
        trimmed_line = line.strip().lower()

        # Check if the trimmed line (minus trailing colon, if present) matches a known section
        # We'll also handle any trailing colon, extra spaces, etc.
        # e.g. "  Parameters:  " -> "parameters:"
        # We only match a line if it starts exactly with that label.
        # If you want more flexible matching (like partial lines), you can adapt this.
        matched_section = None
        for canonical_name, synonyms in SECTION_LABELS.items():
            # Each synonym might be "parameters:", "args:", etc.
            # We'll see if the trimmed_line starts exactly with one of them.
            for synonym in synonyms:
                # If line starts with the synonym, we treat it as a new section.
                # Example: "PARAMETERS:" -> synonyms might contain "parameters:" in lowercase
                if trimmed_line.startswith(synonym):
                    matched_section = canonical_name
                    # Extract leftover text on the same line, after the label
                    leftover = line.strip()[len(synonym):].strip()
                    if leftover:
                        parsed_content[matched_section].append(leftover)
                    break

            if matched_section:
                break

        # If matched_section is not None, we found a new section header
        if matched_section is not None:
            # Switch to that section
            current_section = matched_section
            # No need to append the header line to content - we've already handled any content after the label
        else:
            # Otherwise, accumulate this line under the current section if we have one
            if current_section is not None:
                parsed_content[current_section].append(line)

    # Convert list of lines to a single string for each section, 
    # with consistent line breaks, and strip extra whitespace
    for section in parsed_content:
        parsed_content[section] = "\n".join(parsed_content[section]).strip()

    return parsed_content


# ------------------------------ Example Usage ------------------------------
if __name__ == "__main__":
    sample_docstring = """
Summary:
    Provides a utility for processing and managing data through a structured workflow.

Description:
    This class is designed to facilitate data processing tasks by integrating with the `DataProcessor` class.
    It retrieves and manipulates data.

Parameters:
    param1: This is the first parameter.
    param2: This is the second parameter.

Attributes:
    data: Stores the current data.

Example:
    ```python
    helper = HelperClass()
    helper.process_data()
    print(helper.data)
    ```
    """

    result = parse_google_style_docstring(sample_docstring)

    # Print out each section
    for section_name, content in result.items():
        print("SECTION:", section_name.upper())
        print("CONTENT:\n", content)
        print("-" * 40)
