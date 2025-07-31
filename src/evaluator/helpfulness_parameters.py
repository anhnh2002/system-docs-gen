# Copyright (c) Meta Platforms, Inc. and affiliates
from typing import Dict, Any, List, Optional, Tuple
import re
from dataclasses import dataclass
from enum import Enum

from src.evaluator.evaluation_common import ScoreLevel, ParameterEvaluationExample

class DocstringParametersEvaluator:
    """
    Evaluates the quality of Python docstring parameter descriptions using predefined criteria.
    
    This class assesses how well parameter descriptions in docstrings convey the purpose,
    constraints, and usage context of class initialization parameters, going beyond mere
    type information to provide meaningful guidance to users.
    """

    def __init__(self):
        """Initialize the evaluator with predefined criteria and examples."""
        self.criteria = self._initialize_criteria()
        self.examples = self._initialize_examples()

    def _initialize_criteria(self) -> Dict[str, Any]:
        """
        Set up the evaluation criteria for parameter descriptions.
        
        The criteria define five quality levels, from mere type repetition (1) 
        to excellent usage guidance and context (5).
        
        Returns:
            Dict containing the evaluation criteria and descriptions for each score level.
        """
        return {
            'description': (
                'Evaluate how effectively the parameter descriptions convey the purpose, '
                'constraints, and usage context of class initialization parameters. '
                'High-quality descriptions should go beyond type information to provide '
                'meaningful guidance about parameter usage, valid values, and impact '
                'on class behavior.'
            ),
            'score_criteria': {
                ScoreLevel.POOR: (
                    'The parameter descriptions merely restate the parameter types or '
                    'convert the type hints to natural language without adding any '
                    'meaningful information about usage or purpose.'
                ),
                ScoreLevel.FAIR: (
                    'The descriptions provide basic information about parameter purpose '
                    'but lack details about constraints, valid values, or usage context. '
                    'They may use vague language or miss important details.'
                ),
                ScoreLevel.GOOD: (
                    'The descriptions explain parameter purpose and include some key '
                    'constraints or valid value ranges, but might miss edge cases or '
                    'lack examples where helpful.'
                ),
                ScoreLevel.VERY_GOOD: (
                    'The descriptions clearly explain purpose, constraints, and common '
                    'usage patterns. They may include examples for complex parameters '
                    'and note important edge cases or default behaviors.'
                ),
                ScoreLevel.EXCELLENT: (
                    'The descriptions provide comprehensive guidance including purpose, '
                    'constraints, examples, edge cases, and impact on class behavior. But still keep it concise and focus on the most important information.'
                    'They help users make informed decisions about parameter values.'
                )
            }
        }
    
    def _initialize_examples(self) -> List[ParameterEvaluationExample]:
        """
        Set up concrete examples of parameter descriptions at different quality levels.
        
        Each example includes class and __init__ signatures with corresponding parameter
        descriptions at different quality levels, along with explanations of the ratings.
        
        Returns:
            List of ParameterEvaluationExample objects containing the example cases.
        """
        return [
            ParameterEvaluationExample(
                parameters={
                    "Model_entity_id": "Numeric identifier for the model entity",
                    "Dist_pg": "Distributed process group for coordination",
                    "Checkpoint_config": "Defines checkpoint saving intervals and retention",
                    "Runtime_config": "Specifies resource or environmental constraints",
                    "Train_module": "Orchestrates training steps and interfaces with checkpoints"
                },
                quality_examples={
                    ScoreLevel.POOR: {
                        "Model_entity_id": "the model entity ID",
                        "Dist_pg": "The Process group",
                        "Checkpoint_config": "The checkpoint Configuration",
                        "Runtime_config": "The Runtime configuration",
                        "Train_module": "The Training module"
                    },
                    ScoreLevel.FAIR: {
                        "Model_entity_id": "A number that identifies the model",
                        "Dist_pg": "Process group for distributed operations",
                        "Checkpoint_config": "Settings for checkpoint management",
                        "Runtime_config": "Configuration for runtime behavior",
                        "Train_module": "Module that manages the training process"
                    },
                    ScoreLevel.GOOD: {
                        "Model_entity_id": "identifier for the model entity.",
                        "Dist_pg": "PyTorch distributed process group that handles communication between processes",
                        "Checkpoint_config": "Configuration that determines when checkpoints are saved and how many are kept",
                        "Runtime_config": "Specifies runtime parameters like memory limits and timeout settings",
                        "Train_module": "Module that implements training logic and interacts with the checkpoint system"
                    },
                    ScoreLevel.VERY_GOOD: {
                        "Model_entity_id": "Unique numeric identifier for the model entity in the registry. Must be a valid registered model ID",
                        "Dist_pg": "PyTorch distributed process group that coordinates operations across GPUs/nodes during training. Should match your distributed setup",
                        "Checkpoint_config": "Controls checkpoint frequency, storage locations, and retention policies. Important for balancing disk usage with recovery capabilities",
                        "Runtime_config": "Defines resource constraints and operational parameters. Must be configured appropriately for your hardware to avoid performance issues",
                        "Train_module": "Orchestrates the training workflow, manages state transitions, and defines what model components get checkpointed"
                    },
                    ScoreLevel.EXCELLENT: {
                        "Model_entity_id": "Unique integer ID for the model entity (e.g., 1014925). Should always be a 7 digits number. Must exist in the model registry before checkpointing, otherwise will hit CheckpointNotFoundError and fail to load the checkpoint.",
                        "Dist_pg": "Distributed process group that handles collective operations for multi-GPU or multi-node setups. This setup must be consistent with the training configuration 'distributed_training_config'.",
                        "Checkpoint_config": "Specifies saving intervals, naming formats, and retention. Supports advanced features like asynchronous checkpointing. See examples in 'https://fb.workplace.com/groups/652446422242/preview'.",
                        "Runtime_config": "Contains environment constraints (e.g., memory, disk I/O) and concurrency policies. Ensures checkpointing does not stall training under restricted resources, otherwise will hit CheckpointAccessError and fail to load the checkpoint.",
                        "Train_module": "Manages end-to-end training flow, triggers checkpoint saving at appropriate intervals, and provides context on what states/parameters to store."
                    },
                },
                explanations={
                    ScoreLevel.POOR: "Descriptions recite minimal type info, lacking usage or constraints",
                    ScoreLevel.FAIR: "Provides a basic sense of the purpose for each parameter, but lacks detail",
                    ScoreLevel.GOOD: "Covers core constraints and a bit of context, but some usage details are still missing",
                    ScoreLevel.VERY_GOOD: "Explains relevant usage patterns, constraints, and environment needs",
                    ScoreLevel.EXCELLENT: "Comprehensive coverage including resource impact, advanced usage scenarios, and constraints"
                }
            )
        ]

    def get_evaluation_prompt(self, code_component: str, docstring: str, eval_type: str = None) -> str:
        """
        Generates a prompt for LLM evaluation of parameter descriptions.

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
        
        assert eval_type in ["class", "function", "method"], "eval_type must be one of 'class', 'function', or 'method'"

        example = self.examples[0]  # Use first example as reference

        # system prompt    
        prompt = [
            "Please evaluate the parameter description section for a docstring of a " + eval_type + " based on these criteria:"]

        # second part, the evaluation criteria
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
            "Parameter descriptions at different quality levels:",
        ])
        
        for level in ScoreLevel:
            prompt.extend([
                f"Level {level.value}:",
                *[f"{param}: {desc}" for param, desc in example.quality_examples[level].items()],
                f"Explanation: {example.explanations[level]}",
                ""
            ])
        prompt.append("</reference_example>")
        

        # add focal code component and docstring
        prompt.extend([
            "",
            "<original_code_component>",
            f"{code_component}",
            "</original_code_component>",
            "",
            "<parameters_to_evaluate>",
            "Parameter descriptions to evaluate:",
            f"{docstring}",
            "</parameters_to_evaluate>"
        ])

        prompt.extend([
            "",
            "<analysis_instructions>",
            "IMPORTANT INSTRUCTIONS FOR ANALYSIS:",
            "1. Analyze how well each parameter description provides meaningful information beyond type hints",
            "2. Consider completeness of constraint and valid value documentation",
            "3. Look for helpful context about parameter impact on code component's behavior",
            "4. Check for clear examples or guidance where appropriate",
            "</analysis_instructions>",
            "",
            "<response_format>",
            "Please structure your response as follows:",
            "1. Compare against the criteria and example quality levels",
            "2. Suggest specific improvements for weaker descriptions. Include your suggestions in <suggestions></suggestions> tags. No need to provide suggestions for excellent descriptions.",
            "3. Provide your score (1-5) enclosed in <score></score> tags",
            "</response_format>",
            "",
            "Remember: Do not rush to assign a score. Take time to analyze thoroughly and justify your reasoning.",
            "The score should reflect your careful analysis and should be the last part of your response.",
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
        # Extract score from XML tags
        score_patterns = [
            r'<score>(\d)</score>',  # XML tags
            r'score:\s*(\d)',  # Common format
            r'score\s*=\s*(\d)',  # Alternative format
            r'(\d)\s*/\s*5',  # Rating format
        ]
        
        # Try each pattern
        for pattern in score_patterns:
            score_matches = re.findall(pattern, response, re.IGNORECASE)
            if score_matches:
                score = int(score_matches[0])
                if 1 <= score <= 5:
                    break
        else:
            # If no score found, use a default
            score = 3
        
        # Extract suggestions - look for several common patterns
        suggestion_patterns = [
            r'<suggestions>(.*?)</suggestions>',  # XML tags
            r'suggestions?:\s*(.+?)(?:\n\n|\Z)',  # Common format
            r'improve?:?\s*(.+?)(?:\n\n|\Z)',     # Alternative format
        ]
        
        # Try each pattern
        for pattern in suggestion_patterns:
            suggestion_matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
            if suggestion_matches:
                suggestion = suggestion_matches[0].strip()
                break
        else:
            # Try to find any text that looks like suggestions
            lines = response.split('\n')
            for i, line in enumerate(lines):
                if "suggest" in line.lower() and i < len(lines) - 1:
                    suggestion = lines[i+1].strip()
                    break
            else:
                suggestion = "Consider adding more detailed parameter descriptions."
        
        return score, suggestion

    def get_criteria_description(self) -> str:
        """Returns the main criteria description."""
        return self.criteria['description']

    def get_score_criteria(self, level: ScoreLevel) -> str:
        """Returns the criteria description for a specific score level."""
        return self.criteria['score_criteria'][level]

    def get_examples(self) -> List[ParameterEvaluationExample]:
        """Returns all evaluation examples."""
        return self.examples 