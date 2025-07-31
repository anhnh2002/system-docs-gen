# Copyright (c) Meta Platforms, Inc. and affiliates
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
import re

from src.evaluator.evaluation_common import ScoreLevel

class DescriptionAspect(Enum):
    """Defines the different aspects of docstring description evaluation."""
    MOTIVATION = "motivation"
    USAGE_SCENARIOS = "usage_scenarios"
    INTEGRATION = "integration"
    FUNCTIONALITY = "functionality"

@dataclass
class AspectCriteria:
    """Stores criteria for a single evaluation aspect."""
    description: str
    score_criteria: Dict[ScoreLevel, str]
    example_good: str
    example_poor: str

class DocstringDescriptionEvaluator:
    """
    Evaluates the quality of Python docstring descriptions across multiple aspects.
    
    This evaluator analyzes docstring descriptions based on four key aspects:
    1. Motivation/Purpose explanation
    2. Usage scenarios and conditions
    3. System integration and interactions
    4. Functionality overview
    
    Each aspect is scored independently on a scale of 1-5, providing a comprehensive
    assessment of the description's effectiveness.
    """

    def __init__(self):
        """Initialize the evaluator with predefined criteria for each aspect."""
        self.criteria = self._initialize_criteria()

    def _initialize_criteria(self) -> Dict[DescriptionAspect, AspectCriteria]:
        """
        Set up the evaluation criteria for each aspect of docstring descriptions.
        
        Returns:
            Dictionary mapping aspects to their evaluation criteria.
        """
        return {
            DescriptionAspect.MOTIVATION: AspectCriteria(
                description="How well does the description explain the reason or motivation behind the code?",
                score_criteria={
                    ScoreLevel.POOR: "No explanation of why the code exists or its purpose",
                    ScoreLevel.FAIR: "Basic purpose stated but without context or reasoning",
                    ScoreLevel.GOOD: "Clear explanation of purpose with some context",
                    ScoreLevel.VERY_GOOD: "Thorough explanation of purpose with business/technical context",
                    ScoreLevel.EXCELLENT: "Comprehensive explanation of purpose, context, and value proposition"
                },
                example_good=(
                    "This cache manager addresses the performance bottleneck in our API "
                    "responses by reducing database load during peak hours, while ensuring "
                    "data freshness for critical operations."
                ),
                example_poor="This is a cache manager for storing data."
            ),
            
            DescriptionAspect.USAGE_SCENARIOS: AspectCriteria(
                description="How effectively does it describe when and how to use the code?",
                score_criteria={
                    ScoreLevel.POOR: "No information about usage scenarios",
                    ScoreLevel.FAIR: "Basic usage information without specific scenarios",
                    ScoreLevel.GOOD: "Some key usage scenarios described",
                    ScoreLevel.VERY_GOOD: "Detailed usage scenarios with common cases",
                    ScoreLevel.EXCELLENT: "Comprehensive coverage of use cases, including edge cases"
                },
                example_good=(
                    "Use this validator when processing user-submitted data, especially "
                    "for high-stakes operations like financial transactions. It handles "
                    "various edge cases including partial submissions and legacy formats."
                ),
                example_poor="Validates data according to rules."
            ),
            
            DescriptionAspect.INTEGRATION: AspectCriteria(
                description="How well does it explain integration with other system components?",
                score_criteria={
                    ScoreLevel.POOR: "No mention of system integration",
                    ScoreLevel.FAIR: "Minimal reference to other components",
                    ScoreLevel.GOOD: "Basic explanation of main interactions",
                    ScoreLevel.VERY_GOOD: "Clear description of integration points and dependencies",
                    ScoreLevel.EXCELLENT: "Comprehensive overview of system interactions and data flow"
                },
                example_good=(
                    "This service interfaces with the UserAuth system for validation, "
                    "writes logs to CloudWatch, and triggers notifications through SNS. "
                    "It serves as a crucial link between the frontend and payment processor."
                ),
                example_poor="Processes data and sends it to other services."
            ),
            
            DescriptionAspect.FUNCTIONALITY: AspectCriteria(
                description="How clearly does it explain the functionality without excessive technical detail?",
                score_criteria={
                    ScoreLevel.POOR: "No explanation of functionality",
                    ScoreLevel.FAIR: "Overly technical or vague explanation",
                    ScoreLevel.GOOD: "Basic explanation of main functionality",
                    ScoreLevel.VERY_GOOD: "Clear, balanced explanation of functionality",
                    ScoreLevel.EXCELLENT: "Perfect balance of clarity and technical detail"
                },
                example_good=(
                    "Processes incoming customer data by first validating format and required fields, "
                    "then enriching with relevant historical data, and finally "
                    "generating risk scores using configurable criteria."
                ),
                example_poor="Processes data using various functions and algorithms."
            )
        }

    def get_evaluation_prompt(self, code_implementation: str, docstring: str, eval_type: str = None) -> str:
        """
        Generates a prompt for LLM evaluation of docstring descriptions.
        
        Args:
            code_implementation: The function or class implementation
            docstring: The docstring to evaluate
            eval_type: The type of code component (class, function, method). 
                       If not provided, it will be determined from code_implementation.
            
        Returns:
            Prompt for LLM evaluation
        """
        # Determine eval_type if not provided
        if eval_type is None:
            if code_implementation.strip().startswith("class "):
                eval_type = "class"
            else:
                eval_type = "function" if "self" not in code_implementation.split("(")[0] else "method"
        
        # Extract description from docstring (everything after the summary)
        description = self._extract_description(docstring)
        
        if not description:
            return "The docstring does not have a description section to evaluate."
        
        prompt = ["# Docstring Description Evaluation", ""]
        
        prompt.extend([
            "## Code Component",
            f"```python",
            f"{code_implementation}",
            f"```",
            "",
        ])
        
        prompt.extend([
            "## Docstring Description to Evaluate",
            f"```",
            f"{description}",
            f"```",
            "",
        ])
        
        # Add evaluation criteria
        prompt.extend([
            "## Evaluation Criteria",
            "Please evaluate the above docstring description across these four aspects:",
            ""
        ])
        
        for aspect in DescriptionAspect:
            criteria = self.criteria[aspect]
            prompt.extend([
                f"### {aspect.value.title()}",
                f"{criteria.description}",
                "",
                "Score levels:",
                "",
            ])
            
            for level in ScoreLevel:
                prompt.append(f"{level.value}. {criteria.score_criteria[level]}")
            
            prompt.extend([
                "",
                "Examples:",
                f"Good: \"{criteria.example_good}\"",
                f"Poor: \"{criteria.example_poor}\"",
                "",
            ])
        
        # Add output format instructions
        prompt.extend([
            "## Output Format",
            "Please evaluate the description and provide your assessment in this format:",
            "",
            "```",
            "Motivation: [score 1-5]",
            "Usage Scenarios: [score 1-5]",
            "Integration: [score 1-5]",
            "Functionality: [score 1-5]",
            "",
            "Overall: [average of the scores, rounded to nearest integer]",
            "",
            "Suggestions: [2-3 concrete suggestions for improvement focusing on the weakest aspects]",
            "```",
        ])
        
        return "\n".join(prompt)

    def parse_llm_response(self, response: str) -> Tuple[int, str]:
        """
        Extracts scores and suggestions from an LLM's response.
        
        Args:
            response: The complete response text from the LLM.
            
        Returns:
            Tuple of (overall_score, suggestions)
            
        Raises:
            ValueError: If required information is missing or invalid.
        """
        # Default score if we can't find explicit scores
        default_score = 3
        
        # If the response indicates no description section
        if "docstring does not have a description section" in response:
            return default_score, "Add a description section to the docstring."
        
        # Try to extract an overall score first (easiest)
        overall_pattern = r"Overall:\s*\[?(\d)\.?\d*\]?"
        overall_matches = re.findall(overall_pattern, response, re.IGNORECASE)
        
        if overall_matches:
            overall_score = int(overall_matches[0])
        else:
            # If we can't find an explicit overall score, use a default
            overall_score = default_score
        
        # Extract suggestions
        # Look for several common patterns
        suggestion_patterns = [
            r"Suggestions:\s*(.+?)(?:\n\n|\Z)",  # Format in prompt
            r"<suggestions>(.*?)</suggestions>",  # XML tags
            r"suggestions?:?\s*\n\s*(.+?)(?:\n\n|\Z)",  # Common formats
        ]
        
        for pattern in suggestion_patterns:
            suggestion_matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
            if suggestion_matches:
                suggestion = suggestion_matches[0].strip()
                break
        else:
            # Default suggestion if none found
            suggestion = "Consider adding more detail to the description section."
        
        return overall_score, suggestion

    def _extract_description(self, docstring: str) -> str:
        """
        Extract the description part from a docstring.
        
        The description is everything after the summary line (first line)
        and before any parameter sections, return sections, etc.
        
        Args:
            docstring: The complete docstring
            
        Returns:
            The extracted description, or empty string if none found
        """
        if not docstring:
            return ""
            
        # Split into lines and remove empty lines at start/end
        lines = [line.strip() for line in docstring.strip().split('\n')]
        if not lines:
            return ""
            
        # Skip the first line (summary)
        lines = lines[1:]
        
        # Find where the parameters section or other sections begin
        section_markers = ['Args:', 'Parameters:', 'Arguments:', 'Returns:', 'Raises:', 'Yields:', 'Examples:']
        
        description_lines = []
        for line in lines:
            # Stop if we hit a section marker
            if any(line.strip().startswith(marker) for marker in section_markers):
                break
            description_lines.append(line)
        
        # Join and strip to get the description
        description = '\n'.join(description_lines).strip()
        return description