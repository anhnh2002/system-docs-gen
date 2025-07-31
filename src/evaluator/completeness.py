# Copyright (c) Meta Platforms, Inc. and affiliates
import ast
import re
from typing import Dict, List, Optional

from evaluator.base import BaseEvaluator


class CompletenessEvaluator(BaseEvaluator):
    """
    Base class for evaluating docstring completeness.

    This evaluator examines whether a docstring contains all necessary elements
    according to common documentation standards.

    Attributes:
        score (float): The completeness score from 0 to 1.
        element_scores (Dict[str, bool]): Individual scores for each docstring element.
        element_required (Dict[str, bool]): Whether each element is required.
        weights (List[float]): Weights for each element in scoring.
    """

    def __init__(self, name: str, description: str):
        super().__init__(name=name, description=description)
        self.element_scores: Dict[str, bool] = {}
        self.element_required: Dict[str, bool] = {}
        self.weights: List[float] = []

    def evaluate(self, node: ast.AST) -> float:
        """
        Evaluates the completeness of a docstring.

        This method determines which specific evaluator to use based on the
        AST node type and delegates the evaluation accordingly.

        Args:
            node (ast.AST): The AST node to evaluate.

        Returns:
            float: The completeness score between 0 and 1.

        Raises:
            ValueError: If the node type is not supported.
        """
        if isinstance(node, ast.ClassDef):
            evaluator = ClassCompletenessEvaluator()
            self.score = evaluator.evaluate(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            evaluator = FunctionCompletenessEvaluator()
            self.score = evaluator.evaluate(node)
        else:
            raise ValueError(f"Unsupported node type: {type(node)}")

        return self.score


class ClassCompletenessEvaluator(CompletenessEvaluator):
    """
    Evaluator for class docstring completeness.

    This evaluator checks for the presence of required elements in class
    docstrings including summary, description, attributes, parameters, and examples.

    Attributes:
        score (float): The overall completeness score from 0 to 1.
        element_scores (Dict[str, bool]): Individual scores for each docstring element.
        element_required (Dict[str, bool]): Whether each element is required.
        weights (List[float]): Weights for each element in scoring.
        required_sections (List[str]): List of required sections for the current class.
    """

    # Valid section labels (case-insensitive)
    ATTRIBUTE_LABELS = {
        "attributes:",
        "members:",
        "member variables:",
        "instance variables:",
        "properties:",
    }
    EXAMPLE_LABELS = {
        "example:",
        "examples:",
        "usage:",
        "usage example:",
        "usage examples:",
    }
    PARAMETER_LABELS = {"parameters:", "params:", "args:", "arguments:"}

    def __init__(self):
        super().__init__(
            name="Class Completeness Evaluator",
            description="Evaluates the completeness of class docstrings",
        )

        # Initialize element scores and requirements
        elements = ["summary", "description", "parameters", "attributes", "examples"]

        self.element_scores = {el: False for el in elements}
        self.element_required = {
            el: False for el in elements
        }  # Will be set during evaluation
        self.weights = [0.2] * len(elements)  # Equal weights by default

        # Verify dictionaries have same keys in same order
        assert list(self.element_scores.keys()) == list(self.element_required.keys())
        assert len(self.element_scores) == len(self.weights)

        self.required_sections: List[str] = []

    @staticmethod
    def evaluate_summary(docstring: str) -> bool:
        """
        Evaluates if the docstring has a proper one-liner summary.

        Args:
            docstring (str): The docstring to evaluate.

        Returns:
            bool: True if summary exists, False otherwise.
        """
        lines = docstring.strip().split("\n")
        return bool(lines and lines[0].strip())

    @staticmethod
    def evaluate_description(docstring: str) -> bool:
        """
        Evaluates if the docstring has a proper description.

        Args:
            docstring (str): The docstring to evaluate.

        Returns:
            bool: True if description exists, False otherwise.
        """
        # Split docstring into chunks by empty lines
        chunks = []
        current_chunk = []

        for line in docstring.strip().split("\n"):
            if not line.strip():
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
            else:
                current_chunk.append(line.strip())

        if current_chunk:
            chunks.append(current_chunk)

        # Need at least 2 chunks (summary and description)
        if len(chunks) < 2:
            return False

        # Check if second chunk starts with any other section label
        description_chunk = chunks[1]
        if not description_chunk:
            return False

        first_line = description_chunk[0].lower()
        for labels in [
            ClassCompletenessEvaluator.ATTRIBUTE_LABELS,
            ClassCompletenessEvaluator.PARAMETER_LABELS,
            ClassCompletenessEvaluator.EXAMPLE_LABELS,
        ]:
            if any(first_line.startswith(label.lower()) for label in labels):
                return False

        return True

    @staticmethod
    def evaluate_attributes(docstring: str) -> bool:
        """
        Evaluates if the docstring has attribute documentation.

        Args:
            docstring (str): The docstring to evaluate.

        Returns:
            bool: True if attributes section exists, False otherwise.
        """
        # Check if any attribute label appears anywhere in the docstring
        return any(
            label.lower() in docstring.lower()
            for label in ClassCompletenessEvaluator.ATTRIBUTE_LABELS
        )

    @staticmethod
    def evaluate_parameters(docstring: str) -> bool:
        """
        Evaluates if the docstring has constructor parameter documentation.

        Args:
            docstring (str): The docstring to evaluate.

        Returns:
            bool: True if parameters section exists, False otherwise.
        """
        # Check if any parameter label appears anywhere in the docstring
        return any(
            label.lower() in docstring.lower()
            for label in ClassCompletenessEvaluator.PARAMETER_LABELS
        )

    @staticmethod
    def evaluate_examples(docstring: str) -> bool:
        """
        Evaluates if the docstring has usage examples.

        Args:
            docstring (str): The docstring to evaluate.

        Returns:
            bool: True if examples section exists, False otherwise.
        """
        # Check if any example label appears anywhere in the docstring
        return any(
            label.lower() in docstring.lower()
            for label in ClassCompletenessEvaluator.EXAMPLE_LABELS
        )

    def _has_attributes(self, node: ast.ClassDef) -> bool:
        """
        Checks if the class has attributes by looking for class variables, instance variables in __init__, or enum values.

        Args:
            node (ast.ClassDef): The class definition node.

        Returns:
            bool: True if class has attributes, False otherwise.
        """
        # Check for class variables
        has_class_vars = any(
            isinstance(item, (ast.AnnAssign, ast.Assign)) for item in node.body
        )

        # Check for instance variables in __init__
        has_instance_vars = False
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                has_instance_vars = any(
                    isinstance(stmt, ast.Assign)
                    and isinstance(stmt.targets[0], ast.Attribute)
                    and isinstance(stmt.targets[0].value, ast.Name)
                    and stmt.targets[0].value.id == "self"
                    for stmt in ast.walk(item)
                )
                break

        # Check if it's an Enum
        is_enum = (
            hasattr(node, "bases")
            and node.bases
            and any(
                isinstance(base, ast.Name) and base.id == "Enum" for base in node.bases
            )
        )

        return has_class_vars or has_instance_vars or is_enum

    def _get_required_sections(self, node: ast.ClassDef) -> List[str]:
        """
        Determines which sections are required for the class docstring.

        Args:
            node (ast.ClassDef): The class definition node.

        Returns:
            List[str]: List of required section names.
        """
        required = ["summary", "description"]

        if self._has_attributes(node):
            required.append("attributes")

        # Check if __init__ has parameters beyond self
        if self._has_init_parameters(node):
            required.append("parameters")

        # Examples are required for public classes
        if not node.name.startswith("_"):
            required.append("examples")

        return required

    def _has_init_parameters(self, node: ast.ClassDef) -> bool:
        """
        Checks if the class __init__ method has parameters beyond self.

        Args:
            node (ast.ClassDef): The class definition node.

        Returns:
            bool: True if __init__ has parameters beyond self.
        """
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                args = [arg for arg in item.args.args if arg.arg != "self"]
                return bool(args or item.args.kwonlyargs)
        return False

    def evaluate(self, node: ast.ClassDef) -> float:
        """
        Evaluates the completeness of a class docstring.

        Checks for:
        1. One-liner summary
        2. Description
        3. Attributes documentation
        4. Parameters documentation (if __init__ has parameters beyond self)
        5. Usage examples

        Args:
            node (ast.ClassDef): The class definition node to evaluate.

        Returns:
            float: The completeness score between 0 and 1.
        """
        # Get required sections for this class first
        self.required_sections = self._get_required_sections(node)

        # Reset scores and update requirements
        self.element_scores = {key: False for key in self.element_scores}
        self.element_required = {
            key: key in self.required_sections for key in self.element_scores
        }

        docstring = ast.get_docstring(node)
        if not docstring:
            self.score = 0.0
            return self.score

        # Evaluate each element
        if "summary" in self.required_sections:
            self.element_scores["summary"] = self.evaluate_summary(docstring)
        if "description" in self.required_sections:
            self.element_scores["description"] = self.evaluate_description(docstring)
        if "parameters" in self.required_sections:
            self.element_scores["parameters"] = self.evaluate_parameters(docstring)
        if "attributes" in self.required_sections:
            self.element_scores["attributes"] = self.evaluate_attributes(docstring)
        if "examples" in self.required_sections:
            self.element_scores["examples"] = self.evaluate_examples(docstring)

        # Calculate weighted score considering requirements
        total_weight = 0.0
        weighted_score = 0.0

        for (key, score), weight, required in zip(
            self.element_scores.items(), self.weights, self.element_required.values()
        ):
            if required:
                total_weight += weight
                if score:
                    weighted_score += weight

        self.score = weighted_score / total_weight if total_weight > 0 else 0.0
        return self.score

    def evaluate_using_string(self, docstring: str, element_required: Dict) -> Dict:
        """ """
        # Get required sections for this class first

        # Reset scores and update requirements
        element_scores = {key: False for key in element_required}

        if not docstring:
            score = 0.0
            return element_scores

        # Evaluate each element
        for key in element_required:
            if key == "summary":
                element_scores[key] = self.evaluate_summary(docstring)
            elif key == "description":
                element_scores[key] = self.evaluate_description(docstring)
            elif key == "parameters":
                element_scores[key] = self.evaluate_parameters(docstring)
            elif key == "attributes":
                element_scores[key] = self.evaluate_attributes(docstring)
            elif key == "examples":
                element_scores[key] = self.evaluate_examples(docstring)

        return element_scores


class FunctionCompletenessEvaluator(CompletenessEvaluator):
    """
    Evaluator for function/method docstring completeness.

    This evaluator checks for the presence of required elements in function
    docstrings including summary, description, arguments, returns, raises,
    and examples.

    Attributes:
        score (float): The overall completeness score from 0 to 1.
        element_scores (Dict[str, bool]): Individual scores for each docstring element.
        element_required (Dict[str, bool]): Whether each element is required.
        weights (List[float]): Weights for each element in scoring.
        required_sections (List[str]): List of required sections for the current function.
    """

    # Valid section labels (case-insensitive)
    ARGS_LABELS = {"args:", "arguments:", "parameters:", "params:"}
    RETURNS_LABELS = {
        "returns:",
        "return:",
        "return value:",
        "return type:",
        "yields:",
        "yield:",
    }
    RAISES_LABELS = {"raises:", "exceptions:", "throws:"}
    EXAMPLE_LABELS = {
        "example:",
        "examples:",
        "usage:",
        "usage example:",
        "usage examples:",
    }

    def __init__(self):
        super().__init__(
            name="Function Completeness Evaluator",
            description="Evaluates the completeness of function docstrings",
        )

        # Initialize element scores and requirements
        elements = ["summary", "description", "args", "returns", "raises", "examples"]

        self.element_scores = {el: False for el in elements}
        self.element_required = {
            el: False for el in elements
        }  # Will be set during evaluation
        self.weights = [1 / len(elements)] * len(elements)  # Equal weights by default

        # Verify dictionaries have same keys in same order
        assert list(self.element_scores.keys()) == list(self.element_required.keys())
        assert len(self.element_scores) == len(self.weights)

        self.required_sections: List[str] = []

    @staticmethod
    def evaluate_summary(docstring: str) -> bool:
        """
        Evaluates if the docstring has a proper one-liner summary.

        Args:
            docstring (str): The docstring to evaluate.

        Returns:
            bool: True if summary exists, False otherwise.
        """
        lines = docstring.strip().split("\n")
        return bool(lines and lines[0].strip())

    @staticmethod
    def evaluate_description(docstring: str) -> bool:
        """
        Evaluates if the docstring has a proper description.

        Args:
            docstring (str): The docstring to evaluate.

        Returns:
            bool: True if description exists, False otherwise.
        """
        # Split docstring into chunks by empty lines
        chunks = []
        current_chunk = []

        for line in docstring.strip().split("\n"):
            if not line.strip():
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
            else:
                current_chunk.append(line.strip())

        if current_chunk:
            chunks.append(current_chunk)

        # Need at least 2 chunks (summary and description)
        if len(chunks) < 2:
            return False

        # Check if second chunk starts with any other section label
        description_chunk = chunks[1]
        if not description_chunk:
            return False

        first_line = description_chunk[0].lower()
        for labels in [
            FunctionCompletenessEvaluator.ARGS_LABELS,
            FunctionCompletenessEvaluator.RETURNS_LABELS,
            FunctionCompletenessEvaluator.RAISES_LABELS,
            FunctionCompletenessEvaluator.EXAMPLE_LABELS,
        ]:
            if any(first_line.startswith(label.lower()) for label in labels):
                return False

        return True

    @staticmethod
    def evaluate_args(docstring: str) -> bool:
        """
        Evaluates if the docstring has argument documentation.

        Args:
            docstring (str): The docstring to evaluate.

        Returns:
            bool: True if arguments section exists, False otherwise.
        """
        # Check if any argument label appears anywhere in the docstring
        return any(
            label.lower() in docstring.lower()
            for label in FunctionCompletenessEvaluator.ARGS_LABELS
        )

    @staticmethod
    def evaluate_returns(docstring: str) -> bool:
        """
        Evaluates if the docstring has return value or yield documentation.

        Args:
            docstring (str): The docstring to evaluate.

        Returns:
            bool: True if returns/yields section exists, False otherwise.
        """
        # Check if any return label appears anywhere in the docstring
        return any(
            label.lower() in docstring.lower()
            for label in FunctionCompletenessEvaluator.RETURNS_LABELS
        )

    @staticmethod
    def evaluate_raises(docstring: str) -> bool:
        """
        Evaluates if the docstring has exception documentation.

        Args:
            docstring (str): The docstring to evaluate.

        Returns:
            bool: True if raises section exists, False otherwise.
        """
        # Check if any raise label appears anywhere in the docstring
        return any(
            label.lower() in docstring.lower()
            for label in FunctionCompletenessEvaluator.RAISES_LABELS
        )

    @staticmethod
    def evaluate_examples(docstring: str) -> bool:
        """
        Evaluates if the docstring has usage examples.

        Args:
            docstring (str): The docstring to evaluate.

        Returns:
            bool: True if examples section exists, False otherwise.
        """
        # Check if any example label appears anywhere in the docstring
        return any(
            label.lower() in docstring.lower()
            for label in FunctionCompletenessEvaluator.EXAMPLE_LABELS
        )

    def evaluate(self, node: ast.FunctionDef) -> float:
        """
        Evaluates the completeness of a function docstring.

        Checks for:
        1. One-liner summary
        2. Description
        3. Arguments documentation (if has arguments)
        4. Returns documentation (if has return)
        5. Raises documentation (if has raise statements)
        6. Examples (if not private)

        Args:
            node (ast.FunctionDef): The function definition node to evaluate.

        Returns:
            float: The completeness score between 0 and 1.
        """
        # Skip __init__ methods
        if node.name == "__init__":
            self.score = 1.0
            return self.score

        # Get required sections for this function first
        self.required_sections = self._get_required_sections(node)

        # Reset scores and update requirements
        self.element_scores = {key: False for key in self.element_scores}
        self.element_required = {
            key: key in self.required_sections for key in self.element_scores
        }

        docstring = ast.get_docstring(node)
        if not docstring:
            self.score = 0.0
            return self.score

        # Evaluate each element
        if "summary" in self.required_sections:
            self.element_scores["summary"] = self.evaluate_summary(docstring)
        if "description" in self.required_sections:
            self.element_scores["description"] = self.evaluate_description(docstring)
        if "args" in self.required_sections:
            self.element_scores["args"] = self.evaluate_args(docstring)
        if "returns" in self.required_sections:
            self.element_scores["returns"] = self.evaluate_returns(docstring)
        if "raises" in self.required_sections:
            self.element_scores["raises"] = self.evaluate_raises(docstring)
        if "examples" in self.required_sections:
            self.element_scores["examples"] = self.evaluate_examples(docstring)

        # Calculate weighted score considering requirements
        total_weight = 0.0
        weighted_score = 0.0

        for (key, score), weight, required in zip(
            self.element_scores.items(), self.weights, self.element_required.values()
        ):
            if required:
                total_weight += weight
                if score:
                    weighted_score += weight

        self.score = weighted_score / total_weight if total_weight > 0 else 0.0
        return self.score

    def evaluate_using_string(self, docstring: str, element_required: Dict) -> Dict:
        """ """
        # Get required sections for this class first

        # Reset scores and update requirements
        element_scores = {key: False for key in element_required}

        if not docstring:
            return element_scores

        # Evaluate each element
        for key in element_required:
            if key == "summary":
                element_scores[key] = self.evaluate_summary(docstring)
            elif key == "description":
                element_scores[key] = self.evaluate_description(docstring)
            elif key == "args":
                element_scores[key] = self.evaluate_args(docstring)
            elif key == "returns":
                element_scores[key] = self.evaluate_returns(docstring)
            elif key == "raises":
                element_scores[key] = self.evaluate_raises(docstring)
            elif key == "examples":
                element_scores[key] = self.evaluate_examples(docstring)

        return element_scores

    def _get_required_sections(self, node: ast.FunctionDef) -> List[str]:
        """
        Determines which sections are required for the function docstring.

        Args:
            node (ast.FunctionDef): The function definition node.

        Returns:
            List[str]: List of required section names.
        """
        required = ["summary", "description"]

        # Check if function has arguments beyond just 'self'
        args = [arg for arg in node.args.args if arg.arg != "self"]
        if args or node.args.kwonlyargs:
            required.append("args")

        # Check if function has returns
        if self._has_return_statement(node):
            required.append("returns")

        # Check if function has raise statements
        if self._has_raise_statement(node):
            required.append("raises")

        # Check if function is public (not starting with _)
        if not node.name.startswith("_"):
            required.append("examples")

        return required

    def _has_return_statement(self, node: ast.FunctionDef) -> bool:
        """
        Checks if the function has any meaningful return statements or yields.

        A return statement is considered meaningful if it:
        1. Returns a value other than None
        2. Uses yield or yield from (generator function)
        3. Has an explicit return None statement

        Args:
            node (ast.FunctionDef): The function definition node.

        Returns:
            bool: True if the function has a meaningful return value or is a generator.
        """
        has_explicit_return = False

        for child in ast.walk(node):
            if isinstance(child, ast.Return):
                if child.value is not None:
                    # Return with any value (including None)
                    has_explicit_return = True
                    if (
                        not isinstance(child.value, ast.Constant)
                        or child.value.value is not None
                    ):
                        return True
            elif isinstance(child, (ast.Yield, ast.YieldFrom)):
                # Function is a generator
                return True

        return has_explicit_return

    def _has_raise_statement(self, node: ast.FunctionDef) -> bool:
        """
        Checks if the function has any uncaught raise statements that bubble up to caller.

        Args:
            node (ast.FunctionDef): The function definition node.

        Returns:
            bool: True if the function has any uncaught raise statements.
        """
        for child in ast.walk(node):
            if isinstance(child, ast.Raise):
                # Check if this raise is inside a try-except block
                parent = child
                while parent != node:
                    if isinstance(parent, ast.ExceptHandler):
                        # Exception is caught, skip this raise
                        break
                    parent = next(
                        p
                        for p in ast.walk(node)
                        if any(
                            isinstance(c, type(parent)) and c is parent
                            for c in ast.iter_child_nodes(p)
                        )
                    )
                else:
                    # No except handler found, exception bubbles up
                    return True

        # Also check any function calls that may raise
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                # Here we could recursively check called functions
                # but for now we'll assume any uncaught function call
                # could potentially raise
                try:
                    parent = child
                    while parent != node:
                        if isinstance(parent, ast.ExceptHandler):
                            break
                        parent = next(
                            p
                            for p in ast.walk(node)
                            if any(
                                isinstance(c, type(parent)) and c is parent
                                for c in ast.iter_child_nodes(p)
                            )
                        )
                    else:
                        return True
                except StopIteration:
                    continue

        return False
