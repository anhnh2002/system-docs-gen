#!/usr/bin/env python
# Copyright (c) Meta Platforms, Inc. and affiliates
# -*- coding: utf-8 -*-
"""Test script for the parse_google_style_docstring function."""

from helpers import parse_google_style_docstring, extract_docstring_component
import json
from typing import Dict, Any, Optional


def test_and_print_result(test_name: str, docstring: str) -> Dict[str, Any]:
    """
    Run a test case and print results in a formatted way.
    
    Args:
        test_name: The name of the test
        docstring: The docstring to parse
        
    Returns:
        The parsed docstring components
    """
    print(f"\n{'=' * 80}")
    print(f"TEST: {test_name}")
    print(f"{'-' * 80}")
    print("INPUT DOCSTRING:")
    print(f"{'-' * 40}")
    print(docstring)
    print(f"{'-' * 40}")
    
    # Parse the docstring
    result = parse_google_style_docstring(docstring)
    
    # Print the result in a formatted way
    print("PARSED RESULT:")
    print(f"{'-' * 40}")
    for section, content in result.items():
        if content:
            print(f"{section.upper()}:")
            print(f"{content!r}")
            print()
    print(f"{'-' * 40}")

    return result


def test_extract_component(docstring: str) -> None:
    """
    Test the extract_docstring_component function with a given docstring.
    
    Args:
        docstring: The docstring to test with
    """
    print(f"\n{'=' * 80}")
    print("TESTING extract_docstring_component")
    print(f"{'-' * 80}")
    print("INPUT DOCSTRING:")
    print(f"{'-' * 40}")
    print(docstring)
    print(f"{'-' * 40}")
    
    # Test extracting different components
    components = ["summary", "description", "parameters", "arguments", "returns", "raises", "examples"]
    
    print("EXTRACTED COMPONENTS:")
    print(f"{'-' * 40}")
    for component in components:
        result = extract_docstring_component(docstring, component)
        print(f"{component.upper()}: {result!r}")
    print(f"{'-' * 40}")


def main():
    """Run all tests for the docstring parser."""
    # Test 1: Standard Google-style docstring
    test_and_print_result(
        "Standard Google-style docstring",
        """This is the summary line.

This is the extended description that spans
multiple lines.

Args:
    param1: Description of param1
    param2: Description of param2

Returns:
    Description of the return value

Raises:
    ValueError: If something goes wrong
    
Examples:
    >>> example_function(1, 2)
    3
"""
    )

    # Test 2: Docstring with Google-style section markers and colons
    test_and_print_result(
        "Docstring with explicit Google-style section markers",
        """Summary: This is a summary on the same line as the marker.

Description:
    This is a multi-line
    description.

Args:
    param1: Description of param1
    param2: Description of param2

Returns:
    Description of the return value

Examples:
    Example 1
    Example 2
"""
    )

    # Test 3: Docstring with content on the same line as section headers
    test_and_print_result(
        "Docstring with content on the same line as section headers",
        """Summary: This is a summary on the same line.

Description: This is a description on the same line.

Args: These are args on the same line.
    param1: Description of param1
    param2: Description of param2

Returns: This is the return value on the same line.

Raises: These are exceptions on the same line.
    ValueError: If something goes wrong
    
Examples: This is an example on the same line.
    >>> example_function(1, 2)
    3
"""
    )

    # Test 4: Docstring with alternative labels
    test_and_print_result(
        "Docstring with alternative section labels",
        """Brief: This is the summary with alternative label.

Detailed Description:
    This is the description.

Arguments:
    param1: Description of param1
    param2: Description of param2

Return Value:
    Description of the return value

Exceptions:
    ValueError: If something goes wrong
    
Usage:
    >>> example_function(1, 2)
    3
"""
    )

    # Test 5: Docstring with no explicit section markers
    test_and_print_result(
        "Docstring with no explicit section markers",
        """This is just a simple docstring with no section markers.

It has a second paragraph, but no explicit Args, Returns, etc.
"""
    )

    # Test 6: Empty docstring
    test_and_print_result(
        "Empty docstring",
        ""
    )

    # Test 7: Single line docstring
    test_and_print_result(
        "Single line docstring",
        "This is a single line docstring."
    )

    # Test 8: Docstring with unusual indentation
    test_and_print_result(
        "Docstring with unusual indentation",
        """
        This is an indented summary.
        
            This description has extra indentation.
        
        Args:
                param1: Indented param
                param2: Indented param
        
        Returns:
                Indented return value
        """
    )

    # Test 9: Incomplete docstring with some sections missing
    test_and_print_result(
        "Incomplete docstring with some sections missing",
        """Summary: This is the summary.

Args:
    param1: First parameter
    param2: Second parameter
"""
    )

    # Test 10: Docstring with uppercase section labels
    test_and_print_result(
        "Docstring with uppercase section labels",
        """SUMMARY: This is the summary.

DESCRIPTION: This is the description.

ARGS:
    param1: First parameter
    param2: Second parameter

RETURNS: The return value.
"""
    )

    # Test 11: Docstring with mixed case section labels
    test_and_print_result(
        "Docstring with mixed case section labels",
        """Summary: This is the summary.

Description: This is the description.

Arguments:
    param1: First parameter
    param2: Second parameter

ReTuRnS: The return value.
"""
    )

    # Test 12: Docstring with complex examples section
    test_and_print_result(
        "Docstring with complex examples section",
        """Summary: This function does something.

Examples:
    >>> example_function(1, 2)
    3
    
    More complex example:
    
    ```python
    result = example_function(
        a=1,
        b=2
    )
    assert result == 3
    ```
"""
    )

    # Test 13: Docstring with parameters that look like section labels
    test_and_print_result(
        "Docstring with parameters that look like section labels",
        """Validates input parameters.

Args:
    summary: A parameter named "summary"
    description: A parameter named "description"
    returns: A parameter named "returns"
    examples: A parameter named "examples"
"""
    )

    # Test 14: Docstring with non-standard sections
    test_and_print_result(
        "Docstring with non-standard sections",
        """Summary: This is the summary.

Description: This is the description.

Note:
    This is an important note.

Warning:
    This is a warning.

Args:
    param1: First parameter
"""
    )

    # Test 15: Docstring with section labels with extra spaces
    test_and_print_result(
        "Docstring with section labels with extra spaces",
        """Summary  :   This is the summary with extra spaces around the colon.

Description   :  
    This is the description.

Args   :  
    param1: First parameter
"""
    )

    # Test 16: Docstring with section label on a line by itself (no colon)
    # This is a tricky case!
    test_and_print_result(
        "Docstring with section label on a line by itself (no colon)",
        """This is the summary.

Description
    This is the description.

Arguments
    param1: First parameter
    param2: Second parameter

Returns
    The return value.
"""
    )

    # Test 17: Docstring with Summary section without a colon
    test_and_print_result(
        "Docstring with Summary section without a colon",
        """Summary
This is a summary without a colon after the section label.

Description:
    This is the description.
"""
    )

    # Test 18: Docstring with multiple colons in the summary line
    test_and_print_result(
        "Docstring with multiple colons in the summary line",
        """Summary: This is a summary: with another colon in it.

Description:
    This is the description with: a colon.
"""
    )

    # Test 19: Docstring with summary containing special characters
    test_and_print_result(
        "Docstring with summary containing special characters",
        """Summary: This summary has *special* characters like: [], (), {}

Args:
    param1: Description with `code` and *formatting*
"""
    )

    # Test 20: Docstring with only a summary section
    test_and_print_result(
        "Docstring with only a summary section",
        """Summary: This is only a summary section without other sections.
"""
    )

    # Test 21: Docstring with summary containing multiple paragraphs
    test_and_print_result(
        "Docstring with summary containing multiple paragraphs",
        """Summary: 
    This is a multi-paragraph summary.
    
    It has more than one paragraph.
    
Description:
    This is the description.
"""
    )

    # Test 22: Docstring with extra spacing between sections
    test_and_print_result(
        "Docstring with extra spacing between sections",
        """Summary: This is the summary.



Description: This is the description.



Args:
    param1: First parameter
"""
    )

    # Test 23: Docstring with no content after section label
    test_and_print_result(
        "Docstring with no content after section label",
        """Summary:

Description:

Args:
    param1: This parameter has a description

Returns:
"""
    )

    # Test 24: Docstring with inconsistent indentation
    test_and_print_result(
        "Docstring with inconsistent indentation",
        """Summary: This is a summary.

    Description: 
        This description has inconsistent indentation.
  Args:
      param1: Indented 6 spaces
   param2: Indented differently
"""
    )

    # Test 25: Real-world complex docstring example
    test_and_print_result(
        "Real-world complex docstring example",
        '''"""
Process and analyze data from multiple sources.

This utility function combines data from different sources,
performs advanced analytics, and returns a processed result.
It handles various edge cases and data inconsistencies.

Args:
    data_source (str or Path): Path to the main data source
    secondary_sources (List[str], optional): Additional data sources to include
    config (Dict[str, Any]): Configuration parameters with the following structure:
        {
            "preprocessing": {
                "normalize": bool,
                "fill_missing": str
            },
            "analysis": {
                "method": str,
                "parameters": Dict[str, Any]
            }
        }
    callback (Callable, optional): Function to call with progress updates

Returns:
    Dict[str, Any]: Processed results with the following structure:
        {
            "summary": {
                "total_records": int,
                "processed_records": int,
                "anomalies": int
            },
            "detailed_results": List[Dict[str, Any]]
        }

Raises:
    FileNotFoundError: If any data source cannot be found
    ValueError: If the configuration is invalid
    ProcessingError: If analysis fails during execution

Examples:
    Basic usage:
    
    >>> result = process_data("data.csv", config={"preprocessing": {"normalize": True}})
    >>> print(result["summary"]["total_records"])
    1000
    
    Advanced usage with multiple sources:
    
    ```python
    sources = ["secondary1.csv", "secondary2.csv"]
    config = {
        "preprocessing": {"normalize": True, "fill_missing": "mean"},
        "analysis": {"method": "advanced", "parameters": {"iterations": 100}}
    }
    
    def progress(percent):
        print(f"Processed: {percent}%")
        
    result = process_data("main.csv", sources, config, callback=progress)
    ```
"""'''
    )

    # New: Test the extract_docstring_component function specifically
    print("\n\n")
    print("*" * 100)
    print("TESTING extract_docstring_component FUNCTION")
    print("*" * 100)
    
    # Test Case 1: Standard docstring
    test_extract_component(
        """This is a standard docstring summary.

This is the description.

Args:
    param1: First parameter
    param2: Second parameter

Returns:
    The return value
"""
    )
    
    # Test Case 2: Google-style docstring with explicit section markers
    test_extract_component(
        """Summary: This is a summary with explicit section marker.

Description: This is a description.

Args:
    param1: First parameter
    param2: Second parameter

Returns:
    The return value
"""
    )
    
    # Test Case 3: Docstring with content on the same line as section headers
    test_extract_component(
        """Summary: This is a summary on the same line.

Description: This is a description on the same line.

Args: These are arguments on the same line.
    param1: First parameter
    param2: Second parameter

Returns: This is the return value on the same line.
"""
    )
    
    # Test Case 4: Real-world docstring that might be causing issues
    test_extract_component(
        """Parses a Google-style docstring into its components.

This function takes a docstring and extracts the summary, description,
parameters, returns, raises, and examples sections.

Args:
    docstring: The docstring to parse

Returns:
    A dictionary containing the parsed components
"""
    )
    
    # Test Case 5: Empty docstring
    test_extract_component("")
    
    # Specific cases reported as problematic
    print("\n\n")
    print("*" * 100)
    print("TESTING SPECIFIC PROBLEM CASES")
    print("*" * 100)
    
    # Problem Case: Summary followed immediately by content
    test_extract_component(
        """Summary:This is a summary with no space after the colon.

Description:
    This is a description.
"""
    )
    
    # Problem Case: Summary with line break before content
    test_extract_component(
        """Summary:
    This is a summary after a line break.

Description:
    This is a description.
"""
    )


if __name__ == "__main__":
    main() 