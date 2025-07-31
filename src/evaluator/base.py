# Copyright (c) Meta Platforms, Inc. and affiliates
from abc import ABC, abstractmethod
import ast
from typing import Optional, Dict, Any

class BaseEvaluator(ABC):
    """
    Base class for all docstring evaluators.
    
    This class provides the foundation for implementing various docstring quality 
    evaluators. Each evaluator should focus on a specific aspect of docstring 
    quality such as completeness, helpfulness, or redundancy.
    
    Attributes:
        score (float): The evaluation score, ranging from 0 to 1.
        name (str): The name of the evaluator.
        description (str): A description of what this evaluator checks.
    """
    
    def __init__(self, name: str, description: str):
        self._score: float = 0.0
        self._name = name
        self._description = description
    
    @property
    def score(self) -> float:
        """
        Returns the current evaluation score.
        
        Returns:
            float: A score between 0 and 1 indicating the quality measure.
        """
        return self._score
    
    @score.setter
    def score(self, value: float) -> None:
        """
        Sets the evaluation score.
        
        Args:
            value (float): The score to set, must be between 0 and 1.
            
        Raises:
            ValueError: If the score is not between 0 and 1.
        """
        if not 0 <= value <= 1:
            raise ValueError("Score must be between 0 and 1")
        self._score = value
    
    @abstractmethod
    def evaluate(self, node: ast.AST) -> float:
        """
        Evaluates the quality of a docstring based on specific criteria.
        
        Args:
            node (ast.AST): The AST node containing the docstring to evaluate.
            
        Returns:
            float: The evaluation score between 0 and 1.
        """
        pass