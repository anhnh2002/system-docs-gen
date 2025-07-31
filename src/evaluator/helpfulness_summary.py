# Copyright (c) Meta Platforms, Inc. and affiliates
from typing import Dict, Any, List, Optional, Tuple
import re
from dataclasses import dataclass
from enum import Enum

from src.evaluator.evaluation_common import ScoreLevel, SummaryEvaluationExample

class DocstringSummaryEvaluator:
    """
    Evaluates the quality of Python docstring summaries using predefined criteria and examples.
    
    This class provides a structured way to assess how well a docstring's summary line conveys
    the purpose and value of a function or class. It includes detailed criteria for different
    quality levels and concrete examples to guide the evaluation process.
    """

    def __init__(self):
        """Initialize the evaluator with predefined criteria and examples."""
        self.criteria = self._initialize_criteria()
        self.examples = self._initialize_examples()

    def _initialize_criteria(self) -> Dict[str, Any]:
        """
        Set up the evaluation criteria for docstring summaries.
        
        The criteria define five quality levels, from mere signature repetition (1) 
        to excellent context and purpose explanation (5).
        
        Returns:
            Dict containing the evaluation criteria and descriptions for each score level.
        """
        return {
                'description': (
                    'Evaluate how effectively the one-line summary conveys '
                    'the purpose and value of the function/class while providing additional '
                    'context beyond what is apparent from the signature. A high-quality '
                    'summary should be concise yet informative, avoiding mere signature '
                    'repetition while adding meaningful context about the "why" or '
                    'higher-level purpose.'
                    ),
                'score_criteria': {
                        ScoreLevel.POOR: (
                            'The summary merely restates the function signature in natural '
                            'language or is completely unrelated to the function purpose. '
                            'The summary provides no additional information beyond what is '
                            'already obvious from the function name and parameters.'
                        ),
                        ScoreLevel.FAIR: (
                            'The summary provides minimal information beyond the signature, '
                            'perhaps adding one minor detail but still failing to convey '
                            'meaningful context or purpose. It may use vague or overly '
                            'technical language that doesn\'t help understanding.'
                        ),
                        ScoreLevel.GOOD: (
                            'The summary provides some useful context beyond the signature, '
                            'touching on either the "why" or a key use case, but could be '
                            'more specific or comprehensive. It gives readers a general idea '
                            'but may leave out important context.'
                        ),
                        ScoreLevel.VERY_GOOD: (
                            'The summary effectively communicates both what the function does '
                            'and its higher-level purpose, using clear language that helps '
                            'readers understand when/why to use it. It avoids technical '
                            'jargon unless necessary.'
                        ),
                        ScoreLevel.EXCELLENT: (
                            'The summary excellently balances conciseness with informativeness, '
                            'clearly conveying the function\'s purpose, value, and context in '
                            'business/practical terms. It helps readers immediately understand '
                            'both what the function does and why it matters.'
                        )
                        }
                }

    def _initialize_examples(self) -> List[SummaryEvaluationExample]:
        """
        Set up concrete examples of docstring summaries at different quality levels.
        
        Each example includes a function signature and corresponding summaries at
        different quality levels, along with explanations of the ratings.
        
        Returns:
            List of SummaryEvaluationExample objects containing the example cases.
        """
        return [
            SummaryEvaluationExample(
                function_signature=(
                    "def calculate_user_metrics(user_id: str, start_date: datetime, "
                    "end_date: datetime) -> Dict[str, float]"
                ),
                summaries={
                    ScoreLevel.POOR: "Calculates metrics for a user between two dates.",
                    ScoreLevel.FAIR: "Processes user metrics data through various calculation methods.",
                    ScoreLevel.GOOD: "Analyzes user engagement patterns by computing daily interaction statistics.",
                    ScoreLevel.VERY_GOOD: (
                        "Generates user engagement insights for quarterly reporting by "
                        "processing daily interaction metrics."
                    ),
                    ScoreLevel.EXCELLENT: (
                        "Identifies at-risk users by analyzing engagement patterns "
                        "against historical churn indicators."
                    )
                },
                explanations={
                    ScoreLevel.POOR: "This summary merely converts the function signature into a sentence, providing no additional value.",
                    ScoreLevel.FAIR: "While this adds slightly more information than the signature, it remains vague and unhelpful.",
                    ScoreLevel.GOOD: (
                        "This provides some context about the purpose (engagement analysis) "
                        "but could be more specific about why we track this."
                    ),
                    ScoreLevel.VERY_GOOD: (
                        "This effectively communicates both what it does and why "
                        "(quarterly reporting), giving clear context for its use."
                    ),
                    ScoreLevel.EXCELLENT: (
                        "This excellently conveys both the technical function and its "
                        "business purpose (preventing churn) in a clear, meaningful way."
                    )
                }
            ),
            SummaryEvaluationExample(
                function_signature=(
                    "class DatasetLoader:"
                ),
                summaries={
                    ScoreLevel.POOR: "A class that loads datasets.",
                    ScoreLevel.FAIR: "Handles loading of data from various sources.",
                    ScoreLevel.GOOD: "Provides unified interface for loading and validating datasets from multiple sources.",
                    ScoreLevel.VERY_GOOD: (
                        "Streamlines dataset ingestion by providing a consistent interface "
                        "for loading and validating data from diverse sources."
                    ),
                    ScoreLevel.EXCELLENT: (
                        "Ensures data quality and consistency by providing a unified interface "
                        "for loading, validating, and preprocessing datasets across multiple "
                        "formats and sources while handling common edge cases."
                    )
                },
                explanations={
                    ScoreLevel.POOR: "Simply restates the class name without adding value.",
                    ScoreLevel.FAIR: "Adds minimal information, remains vague about capabilities.",
                    ScoreLevel.GOOD: (
                        "Provides context about key functionality but could better explain "
                        "benefits and use cases."
                    ),
                    ScoreLevel.VERY_GOOD: (
                        "Clearly communicates purpose and value while highlighting key "
                        "features and benefits."
                    ),
                    ScoreLevel.EXCELLENT: (
                        "Excellently balances technical capabilities with practical benefits, "
                        "while highlighting key differentiators and value proposition."
                    )
                }
            )
        ]

    def get_evaluation_prompt(self, code_component: str, docstring: str, eval_type: str = None) -> str:
        """
        Generates a prompt for LLM evaluation of docstring summaries.
        
        Args:
            code_component: The code implementation (class or function/method)
            docstring: The docstring to evaluate
            eval_type: The type of code component (class, function, method).
                      If not provided, it will be determined from code_component.
        
        Returns:
            Prompt for LLM evaluation
        """
        # Determine eval_type if not provided
        if eval_type is None:
            if code_component.strip().startswith("class "):
                eval_type = "class"
            else:
                eval_type = "function" if "self" not in code_component.split("(")[0] else "method"
        
        # Determine if input is a class or function signature
        is_class = eval_type == "class"
        
        # Select relevant example based on signature type
        relevant_example = next(
            example for example in self.examples 
            if (example.function_signature.startswith('class') == is_class)
        )
        
        prompt = [
            "Please evaluate the summary part of a docstring of a " + eval_type + " based on these criteria:",
        ]
        
        # Add criteria for each score level
        for level in ScoreLevel:
            prompt.append(f"{level.value}. {self.criteria['score_criteria'][level]}")
        prompt.append("</evaluation_criteria>")
        
        # Add single relevant example
        prompt.extend([
            "",
            "<reference_example>",
            "Summaries at different levels:",
        ])
        
        for level in ScoreLevel:
            prompt.extend([
                f"Level {level.value}: {relevant_example.summaries[level]}",
                f"Explanation: {relevant_example.explanations[level]}",
                ""
            ])
        prompt.append("</reference_example>")

        # add the code component and the docstring
        prompt.extend([
            "",
            "<original_code_component>",
            f"{code_component}",
            "</original_code_component>",
        ])

        prompt.extend([
            "",
            "<docstring_to_evaluate>",
            f"{docstring}",
            "</docstring_to_evaluate>",
        ])
        
        prompt.extend([
            "",
            "<analysis_instructions>",
            "IMPORTANT INSTRUCTIONS FOR ANALYSIS:",
            "1. Take your time to analyze the relationship between the focal code component and the summary part of the docstring.",
            "2. Consider how much additional context and value the summary provides beyond the signature.",
            "3. Compare the summary against each score level's criteria methodically.",
            "4. Look for similarities with the provided example at each quality level.",
            "</analysis_instructions>",
            "",
            "<response_format>",
            "Please structure your response as follows:",
            "1. First explain your reasoning by comparing against the criteria",
            "2. If applicable, suggest specific improvements. Include your suggestions in <suggestions></suggestions> tags. No need to provide suggestions for excellent summaries.",
            "3. Finally, provide your score (1-5) enclosed in <score></score> tags",
            "</response_format>",
            "",
            "Remember: Do not rush to assign a score. Take time to analyze thoroughly and justify your reasoning.",
            "The score should reflect your careful analysis and should be the last part of your response."
        ])
        
        return "\n".join(prompt)
    
    def parse_llm_response(self, response: str) -> Tuple[int, str]:
        """
        Extracts the numerical score and suggestions from an LLM's response.
        
        Args:
            response: The complete response text from the LLM.
            
        Returns:
            A tuple containing:
            - The numerical score (1-5)
            - The suggestions for improvement
            
        Raises:
            ValueError: If no valid score is found.
        """
        # Extract score from various patterns
        score_patterns = [
            r'<score>(\d)</score>',  # XML tags
            r'score:\s*(\d)',        # Common format
            r'score\s*=\s*(\d)',     # Alternative format
            r'(\d)\s*/\s*5',         # Rating format
            r'level\s*(\d)',         # Level references
        ]
        
        # Try each pattern
        for pattern in score_patterns:
            score_matches = re.findall(pattern, response, re.IGNORECASE)
            if score_matches:
                score = int(score_matches[0])
                if 1 <= score <= 5:
                    break
        else:
            # If no score found, default to 3
            score = 3
        
        # Extract suggestions - look for several common patterns
        suggestion_patterns = [
            r'<suggestions>(.*?)</suggestions>',    # XML tags
            r'suggestions?:\s*(.+?)(?:\n\n|\Z)',    # Common format
            r'could be improved by:?\s*(.+?)(?:\n\n|\Z)', # Alternative phrasing
            r'improvement:?\s*(.+?)(?:\n\n|\Z)',    # Another alternative
        ]
        
        # Try each pattern
        for pattern in suggestion_patterns:
            suggestion_matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
            if suggestion_matches:
                suggestion = suggestion_matches[0].strip()
                break
        else:
            # If we can't find a suggestion, extract sentences that seem like suggestions
            suggestion_sentences = []
            for sentence in re.split(r'[.!?]\s+', response):
                if any(word in sentence.lower() for word in ['could', 'should', 'might', 'consider', 'suggest', 'improve', 'better']):
                    suggestion_sentences.append(sentence.strip())
            
            if suggestion_sentences:
                suggestion = ' '.join(suggestion_sentences) + '.'
            else:
                # Default suggestion
                suggestion = "Consider adding more context and purpose to the summary."
        
        return score, suggestion

    def get_criteria_description(self) -> str:
        """Returns the main criteria description."""
        return self.criteria['description']

    def get_score_criteria(self, level: ScoreLevel) -> str:
        """Returns the criteria description for a specific score level."""
        return self.criteria['score_criteria'][level]

    def get_examples(self) -> List[SummaryEvaluationExample]:
        """Returns all evaluation examples."""
        return self.examples