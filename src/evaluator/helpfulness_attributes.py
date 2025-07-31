# Copyright (c) Meta Platforms, Inc. and affiliates
from typing import Dict, Any, List, Optional, Tuple
import re
from dataclasses import dataclass
from enum import Enum

class ScoreLevel(Enum):
    """Defines the possible score levels for docstring evaluation."""
    POOR = 1
    FAIR = 2
    GOOD = 3
    VERY_GOOD = 4
    EXCELLENT = 5

@dataclass
class EvaluationExample:
    """Stores an example of docstring attribute evaluation with different quality levels."""
    class_signature: str
    init_function: str
    attributes: Dict[str, str]
    quality_examples: Dict[ScoreLevel, Dict[str, str]]
    explanations: Dict[ScoreLevel, str]

class DocstringAttributeEvaluator:
    """
    Evaluates the quality of Python docstring attribute descriptions using predefined criteria.
    
    This class assesses how well attribute descriptions in docstrings convey the purpose,
    lifecycle, and usage context of class attributes, going beyond mere type information
    to provide meaningful guidance about attribute roles and behaviors.
    """

    def __init__(self):
        """Initialize the evaluator with predefined criteria and examples."""
        self.criteria = self._initialize_criteria()
        self.examples = self._initialize_examples()

    def _initialize_criteria(self) -> Dict[str, Any]:
        """
        Set up the evaluation criteria for attribute descriptions.
        
        The criteria define five quality levels, from mere type repetition (1) 
        to excellent usage guidance and context (5).
        
        Returns:
            Dict containing the evaluation criteria and descriptions for each score level.
        """
        return {
            'description': (
                'Evaluate how effectively the attribute descriptions convey the purpose, '
                'lifecycle, and usage context of class attributes. High-quality descriptions '
                'should go beyond type information to provide meaningful guidance about '
                'attribute roles, initialization, modification patterns, and relationships '
                'with class behavior.'
            ),
            'score_criteria': {
                ScoreLevel.POOR: (
                    'The attribute descriptions merely restate the attribute types or '
                    'convert the type hints to natural language without adding any '
                    'meaningful information about purpose or lifecycle.'
                ),
                ScoreLevel.FAIR: (
                    'The descriptions provide basic information about attribute purpose '
                    'but lack details about initialization, modification, or usage patterns. '
                    'They may use vague language or miss important details.'
                ),
                ScoreLevel.GOOD: (
                    'The descriptions explain attribute purpose and include some key '
                    'information about initialization or usage patterns, but might miss '
                    'important lifecycle details or relationships with class behavior.'
                ),
                ScoreLevel.VERY_GOOD: (
                    'The descriptions clearly explain purpose, initialization, and common '
                    'usage patterns. They may note important relationships with class '
                    'methods and document any special handling or constraints.'
                ),
                ScoreLevel.EXCELLENT: (
                    'The descriptions provide comprehensive guidance including purpose, '
                    'initialization, modification patterns, relationships with class '
                    'behavior, and any special considerations. They help users understand '
                    'both how and when to interact with the attributes.'
                )
            }
        }

    def _initialize_examples(self) -> List[EvaluationExample]:
        """
        Set up concrete examples of attribute descriptions at different quality levels.
        
        Each example includes class and __init__ signatures with corresponding attribute
        descriptions at different quality levels, along with explanations of the ratings.
        
        Returns:
            List of EvaluationExample objects containing the example cases.
        """
        return [
            EvaluationExample(
                class_signature="class DataProcessor:",
                init_function='''def __init__(self, config: Dict[str, Any]):
    """Initialize the data processor.
    
    Args:
        config: Configuration dictionary for the processor
    """
    self.config = config
    self.data_cache = {}
    self.is_initialized = False
    self.stats = defaultdict(int)
    self._lock = threading.Lock()''',
                attributes={
                    "config": "Configuration settings for the processor",
                    "data_cache": "Cache for processed data",
                    "is_initialized": "Whether the processor is initialized",
                    "stats": "Processing statistics",
                    "_lock": "Thread synchronization lock"
                },
                quality_examples={
                    ScoreLevel.POOR: {
                        "config": "Dictionary of configuration",
                        "data_cache": "Dictionary for cache",
                        "is_initialized": "Boolean flag",
                        "stats": "Dictionary of statistics",
                        "_lock": "Threading lock object"
                    },
                    ScoreLevel.FAIR: {
                        "config": "Configuration settings for processing",
                        "data_cache": "Cache storage for processed items",
                        "is_initialized": "Tracks initialization status",
                        "stats": "Counts of processed items",
                        "_lock": "Lock for thread safety"
                    },
                    ScoreLevel.GOOD: {
                        "config": "Configuration dictionary controlling processing behavior. Set at initialization",
                        "data_cache": "Cache of processed items to avoid recomputation. Cleared with reset()",
                        "is_initialized": "Flag indicating if setup() has been called successfully",
                        "stats": "Counters tracking number of items processed, errors, cache hits etc",
                        "_lock": "Thread lock ensuring thread-safe access to shared resources"
                    },
                    ScoreLevel.VERY_GOOD: {
                        "config": "Configuration dictionary controlling processing behavior. Set at initialization and accessed by all processing methods. Read-only after initialization",
                        "data_cache": "Cache of processed items to avoid recomputation. Cleared with reset(). Keys are item IDs, values are processed results",
                        "is_initialized": "Flag indicating if setup() has been called successfully. Methods will raise RuntimeError if called before initialization",
                        "stats": "Counters tracking processing metrics (items processed, errors, cache hits etc). Updated by process() and reset by clear_stats()",
                        "_lock": "Thread lock ensuring thread-safe access to cache and stats. Used internally by all public methods"
                    },
                    ScoreLevel.EXCELLENT: {
                        "config": "Configuration dictionary controlling processing behavior. Set at initialization and accessed by all processing methods. Read-only after initialization. Must contain 'batch_size' and 'max_cache_size' keys. See CONFIG_SCHEMA for full specification",
                        "data_cache": "Cache of processed items to avoid recomputation. Cleared with reset(). Keys are item IDs, values are processed results. Limited to max_cache_size items with LRU eviction. Thread-safe access via _lock",
                        "is_initialized": "Flag indicating if setup() has been called successfully. Methods will raise RuntimeError if called before initialization. Set to True by setup() and False by reset(). Thread-safe access via _lock",
                        "stats": "Counters tracking processing metrics (items processed, errors, cache hits etc). Updated by process() and reset by clear_stats(). Access via get_stats() for thread-safe snapshot. Used for monitoring and auto-scaling decisions",
                        "_lock": "Thread lock ensuring thread-safe access to cache and stats. Used internally by all public methods. Reentrant lock allowing nested acquisition by same thread. Consider using async methods for high-concurrency scenarios"
                    }
                },
                explanations={
                    ScoreLevel.POOR: "These descriptions merely restate the attribute types without adding value",
                    ScoreLevel.FAIR: "Provides basic purpose but lacks lifecycle and usage guidance",
                    ScoreLevel.GOOD: "Includes initialization context and some usage patterns but could be more comprehensive",
                    ScoreLevel.VERY_GOOD: "Clear purpose, initialization, and usage patterns with thread-safety context",
                    ScoreLevel.EXCELLENT: "Comprehensive guidance including constraints, thread-safety, and practical usage tips"
                }
            )
        ]

    def get_evaluation_prompt(self, class_signature: str, init_function: str,
                            attribute_descriptions: Dict[str, str]) -> str:
        """
        Generates a prompt for LLM evaluation of attribute descriptions.
        
        Args:
            class_signature: The complete class signature.
            init_function: The complete __init__ function including docstring.
            attribute_descriptions: Dict mapping attribute names to their descriptions.
            
        Returns:
            A formatted prompt string that can be sent to an LLM for evaluation.
        """
        example = self.examples[0]  # Use first example as reference
        
        prompt = [
            "Please evaluate the following Python docstring attribute descriptions based on these criteria:",
            "",
            "<class_info>",
            f"Class signature:\n{class_signature}",
            "",
            f"Init function:\n{init_function}",
            "</class_info>",
            "",
            "<attributes_to_evaluate>",
            "Attribute descriptions to evaluate:",
        ]
        
        for attr, desc in attribute_descriptions.items():
            prompt.append(f"{attr}: {desc}")
        prompt.append("</attributes_to_evaluate>")
        
        prompt.extend([
            "",
            "<evaluation_criteria>",
            "Evaluation criteria:",
            self.criteria['description'],
            "",
            "Score levels:",
        ])
        
        # Add criteria for each score level
        for level in ScoreLevel:
            prompt.append(f"{level.value}. {self.criteria['score_criteria'][level]}")
        prompt.append("</evaluation_criteria>")
        
        # Add example
        prompt.extend([
            "",
            "<reference_example>",
            "Example for reference:",
            f"Class: {example.class_signature}",
            f"Init:\n{example.init_function}",
            "",
            "Attribute descriptions at different quality levels:",
        ])
        
        for level in ScoreLevel:
            prompt.extend([
                f"Level {level.value}:",
                *[f"{attr}: {desc}" for attr, desc in example.quality_examples[level].items()],
                f"Explanation: {example.explanations[level]}",
                ""
            ])
        prompt.append("</reference_example>")
        
        prompt.extend([
            "",
            "<analysis_instructions>",
            "IMPORTANT INSTRUCTIONS FOR ANALYSIS:",
            "1. Analyze how well each attribute description provides meaningful information beyond type hints",
            "2. Consider completeness of lifecycle documentation (initialization, modification, access patterns)",
            "3. Look for helpful context about relationships with class behavior",
            "4. Check for thread-safety and special handling documentation where relevant",
            "</analysis_instructions>",
            "",
            "<response_format>",
            "Please structure your response as follows:",
            "1. Analyze each attribute description's strengths and weaknesses",
            "2. Compare against the criteria and example quality levels",
            "3. Suggest specific improvements for weaker descriptions",
            "4. Provide your score (1-5) enclosed in <score></score> tags",
            "</response_format>",
            "",
            "Remember: Do not rush to assign a score. Take time to analyze thoroughly and justify your reasoning.",            
            "No need to provide Suggestions for Improvement",
            "The score should reflect your careful analysis and should be the last part of your response."
        ])
        
        return "\n".join(prompt)
    
    def parse_llm_response(self, response: str) -> Tuple[int, str]:
        """
        Extracts the numerical score and full analysis from an LLM's response.
        
        Args:
            response: The complete response text from the LLM.
            
        Returns:
            A tuple containing:
            - The numerical score (1-5)
            - The full analysis text
            
        Raises:
            ValueError: If no valid score is found or if multiple scores are found.
        """
        # Extract score from XML tags
        score_matches = re.findall(r'<score>(\d)</score>', response)
        
        if not score_matches:
            raise ValueError("No valid score found in LLM response. Response must include a score in <score></score> tags.")
        
        if len(score_matches) > 1:
            raise ValueError("Multiple scores found in LLM response. Expected exactly one score.")
            
        score = int(score_matches[0])
        if score < 1 or score > 5:
            raise ValueError(f"Invalid score value: {score}. Score must be between 1 and 5.")
        
        # Remove the score tags from the analysis text
        analysis = re.sub(r'<score>\d</score>', '', response).strip()
        
        return score, analysis

    def get_criteria_description(self) -> str:
        """Returns the main criteria description."""
        return self.criteria['description']

    def get_score_criteria(self, level: ScoreLevel) -> str:
        """Returns the criteria description for a specific score level."""
        return self.criteria['score_criteria'][level]

    def get_examples(self) -> List[EvaluationExample]:
        """Returns all evaluation examples."""
        return self.examples 