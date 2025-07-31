# Copyright (c) Meta Platforms, Inc. and affiliates
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
import ast
import re



def get_callable_name(node: Union[ast.Name, ast.Attribute]) -> str:
    """
    Extract the name of a callable whether it's an ast.Name or ast.Attribute.
    """
    if isinstance(node, ast.Name):
        # e.g., "my_function"
        return node.id
    elif isinstance(node, ast.Attribute):
        # e.g., "some_module.my_function"
        # node.value.id -> "some_module", node.attr -> "my_function"
        return node.attr
    else:
        raise ValueError(f"Unsupported node type for function/class: {type(node)}")


@dataclass
class FunctionCallExample:
    """Stores an example of function usage with context and expected output."""
    context_code: str  # Code leading up to the function call
    function_signature: str  # The complete function signature
    docstring_example: str  # Only the example part of the docstring
    expected_call: str  # The expected function call line(s)

@dataclass
class ClassCallExample:
    """Stores an example of class instantiation with context and expected output."""
    context_code: str  # Code leading up to class instantiation
    class_signature: str  # The class signature
    init_signature: str  # The __init__ method signature
    docstring_example: str  # Only the example part of the docstring
    expected_call: str  # The expected instantiation line(s)

@dataclass
class MethodCallExample:
    """Stores an example of method usage with context and expected output."""
    context_code: str  # Code leading up to method call
    method_signature: str  # The method signature
    docstring_example: str  # Only the example part of the docstring
    expected_call: str  # The expected method call line(s)

class BaseExampleEvaluator(ABC):
    """
    Base class for evaluating docstring examples.
    
    This class provides the foundation for evaluating how well docstring examples
    enable users to correctly use the code without needing to understand its implementation.
    """
    
    @abstractmethod
    def get_evaluation_prompt(self, context_code: str, signature: str, example: str) -> str:
        """
        Generates a prompt for LLM to predict the next line(s) of code.
        
        Args:
            context_code: The code leading up to where the prediction should be made
            signature: The complete signature of the function/class/method
            example: The example part of the docstring
            
        Returns:
            A formatted prompt string for the LLM
        """
        pass
    
    @abstractmethod
    def evaluate_prediction(self, prediction: str, ground_truth: str) -> Tuple[bool, str]:
        """
        Evaluates if the predicted usage matches the ground truth.
        
        Args:
            prediction: The LLM's predicted line(s) of code
            ground_truth: The expected line(s) of code
            
        Returns:
            A tuple containing:
            - Boolean indicating if the prediction is correct
            - String explaining the evaluation result
        """
        pass

class FunctionExampleEvaluator(BaseExampleEvaluator):
    """
    Evaluates the quality of function docstring examples by testing if they enable
    correct function usage prediction.
    """
    
    def get_evaluation_prompt(self, context_code: str, signature: str, example: str) -> str:
        """
        Generates a prompt for LLM to predict the next line of function usage.
        
        Args:
            context_code: The code leading up to the function call
            signature: The complete function signature
            example: The example part of the docstring
            
        Returns:
            A formatted prompt string that can be sent to an LLM for prediction
        """
        prompt = [
            "Given the following context, predict ONLY the next line of code that calls the function.",
            "Your prediction should be based solely on the function signature and example provided.",
            "",
            "Function signature:",
            signature,
            "",
            "Example from docstring:",
            example,
            "",
            "Context code leading up to function call:",
            context_code,
            "",
            "IMPORTANT INSTRUCTIONS:",
            "1. Predict ONLY the next line(s) that calls the function",
            "2. Base your prediction solely on the signature and example",
            "3. Include ONLY the function call, no additional explanation",
            "4. If the function call spans multiple lines, include all necessary lines",
            "5. Ensure the prediction is valid Python syntax",
            "",
            "Your prediction should be enclosed in <prediction></prediction> tags",
        ]
        
        return "\n".join(prompt)
    
    def evaluate_prediction(self, prediction: str, ground_truth: str) -> Tuple[bool, str]:
        """
        Evaluates if the predicted function call matches the ground truth.
        
        Performs robust parsing of both prediction and ground truth to compare:
        1. Function name
        2. Argument names and their order
        3. Argument values (when they are literals)
        
        Args:
            prediction: The LLM's predicted function call
            ground_truth: The expected function call
            
        Returns:
            Tuple containing:
            - Boolean indicating if the prediction is correct
            - String explaining why the prediction was correct or incorrect
        """
        # Parse both prediction and ground truth into AST
        pred_ast = ast.parse(prediction.strip()).body[0].value
        truth_ast = ast.parse(ground_truth.strip()).body[0].value
        
        # Verify it's a function call
        if not isinstance(pred_ast, ast.Call) or not isinstance(truth_ast, ast.Call):
            return False, "Not a valid function call"
        
        # Check function name
        pred_name = get_callable_name(pred_ast.func)
        truth_name = get_callable_name(truth_ast.func)

        if pred_name != truth_name:
            return False, f"Mismatch: expected '{truth_name}', got '{pred_name}'"
        
        # Get argument information
        pred_args = {
            kw.arg: kw.value for kw in pred_ast.keywords
        }
        truth_args = {
            kw.arg: kw.value for kw in truth_ast.keywords
        }
        
        # Check positional arguments
        if len(pred_ast.args) != len(truth_ast.args):
            return False, "Mismatched number of positional arguments"
        
        # Check keyword arguments
        if set(pred_args.keys()) != set(truth_args.keys()):
            return False, "Mismatched keyword argument names"
        
        # Check argument order for positional args
        for i, (p_arg, t_arg) in enumerate(zip(pred_ast.args, truth_ast.args)):
            if not self._compare_ast_nodes(p_arg, t_arg):
                return False, f"Positional argument {i+1} mismatch"
        
        # Check keyword argument values
        for arg_name, t_value in truth_args.items():
            p_value = pred_args[arg_name]
            if not self._compare_ast_nodes(p_value, t_value):
                return False, f"Keyword argument '{arg_name}' value mismatch"
        
        return True, "Function call matches expected usage"
    
    def _compare_ast_nodes(self, node1: ast.AST, node2: ast.AST) -> bool:
        """
        Helper method to compare two AST nodes.
        
        Args:
            node1: First AST node
            node2: Second AST node
            
        Returns:
            Boolean indicating if the nodes are equivalent
        """
        # For literals (strings, numbers, etc.)
        if isinstance(node1, (ast.Str, ast.Num, ast.NameConstant)):
            return isinstance(node2, type(node1)) and node1.value == node2.value
        
        # For variable names
        if isinstance(node1, ast.Name) and isinstance(node2, ast.Name):
            return node1.id == node2.id
        
        # For attribute access (e.g., obj.attr)
        if isinstance(node1, ast.Attribute) and isinstance(node2, ast.Attribute):
            return node1.attr == node2.attr and self._compare_ast_nodes(node1.value, node2.value)
        
        # For lists/tuples
        if isinstance(node1, (ast.List, ast.Tuple)) and isinstance(node2, type(node1)):
            if len(node1.elts) != len(node2.elts):
                return False
            return all(self._compare_ast_nodes(e1, e2) for e1, e2 in zip(node1.elts, node2.elts))
        
        return False

class ClassExampleEvaluator(BaseExampleEvaluator):
    """
    Evaluates the quality of class docstring examples by testing if they enable
    correct class instantiation prediction.
    """
    
    def get_evaluation_prompt(self, context_code: str, signature: str, example: str) -> str:
        """
        Generates a prompt for LLM to predict the class instantiation line.
        
        Args:
            context_code: The code leading up to class instantiation
            signature: Combined class and __init__ signatures
            example: The example part of the docstring
            
        Returns:
            A formatted prompt string that can be sent to an LLM for prediction
        """
        prompt = [
            "Given the following context, predict ONLY the next line of code that creates a class instance.",
            "Your prediction should be based solely on the class signature and example provided.",
            "",
            "Class and __init__ signatures:",
            signature,
            "",
            "Example from docstring:",
            example,
            "",
            "Context code leading up to class instantiation:",
            context_code,
            "",
            "IMPORTANT INSTRUCTIONS:",
            "1. Predict ONLY the next line(s) that creates the class instance",
            "2. Base your prediction solely on the signatures and example",
            "3. Include ONLY the instantiation code, no additional explanation",
            "4. If the instantiation spans multiple lines, include all necessary lines",
            "5. Ensure the prediction is valid Python syntax",
            "",
            "Your prediction should be enclosed in <prediction></prediction> tags",
        ]
        
        return "\n".join(prompt)
    
    def _compare_ast_nodes(self, node1: ast.AST, node2: ast.AST) -> bool:
        """
        Example placeholder comparison method. 
        You should implement your logic based on how you want 
        to compare constant values, variable references, etc.
        """
        if isinstance(node1, ast.Constant) and isinstance(node2, ast.Constant):
            return node1.value == node2.value
        # Extend your comparison logic here (e.g., for lists, dicts, names, etc.)
        return ast.dump(node1) == ast.dump(node2)

    def _get_func_name(self, node: Union[ast.Name, ast.Attribute]) -> str:
        """
        Extract the function/class name whether it's `Name` or `Attribute`.
        - ast.Name: directly has `node.id`
        - ast.Attribute: the class name is in `node.attr` (e.g. `some_module.MyClass`)
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        else:
            # If your code can handle more node types, add logic here
            raise ValueError(f"Unsupported node type for function/class: {type(node)}")

    def evaluate_prediction(self, prediction: str, ground_truth: str) -> Tuple[bool, str]:
        """
        Evaluates if the predicted class instantiation matches the ground truth.

        Performs robust parsing of both prediction and ground truth to compare:
        1. Class name
        2. Constructor argument names and order
        3. Argument values (when literals)
        
        Args:
            prediction: The LLM's predicted instantiation code
            ground_truth: The expected instantiation code
            
        Returns:
            Tuple containing:
            - Boolean indicating if the prediction is correct
            - String explaining why the prediction was correct or incorrect
        """
        # Parse both prediction and ground truth into AST
        pred_ast = ast.parse(prediction.strip()).body[0].value
        truth_ast = ast.parse(ground_truth.strip()).body[0].value
        
        # Verify it's a class instantiation
        if not isinstance(pred_ast, ast.Call) or not isinstance(truth_ast, ast.Call):
            return False, "Not a valid class instantiation"
        
        # Safely extract the class name from both
        pred_func_name = self._get_func_name(pred_ast.func)
        truth_func_name = self._get_func_name(truth_ast.func)
        
        # Check class name
        if pred_func_name != truth_func_name:
            return False, f"Class name mismatch: expected {truth_func_name}, got {pred_func_name}"
        
        # Get argument information (keyword args)
        pred_args = {kw.arg: kw.value for kw in pred_ast.keywords}
        truth_args = {kw.arg: kw.value for kw in truth_ast.keywords}
        
        # Check positional arguments
        if len(pred_ast.args) != len(truth_ast.args):
            return False, "Mismatched number of positional arguments"
        
        # Check keyword arguments
        if set(pred_args.keys()) != set(truth_args.keys()):
            return False, "Mismatched keyword argument names"
        
        # Check argument order and values for positional args
        for i, (p_arg, t_arg) in enumerate(zip(pred_ast.args, truth_ast.args)):
            if not self._compare_ast_nodes(p_arg, t_arg):
                return False, f"Positional argument {i+1} mismatch"
        
        # Check keyword argument values
        for arg_name, t_value in truth_args.items():
            p_value = pred_args[arg_name]
            if not self._compare_ast_nodes(p_value, t_value):
                return False, f"Keyword argument '{arg_name}' value mismatch"
        
        return True, "Class instantiation matches expected usage"
    
    def _compare_ast_nodes(self, node1: ast.AST, node2: ast.AST) -> bool:
        """Helper method to compare two AST nodes."""
        # Reuse the same implementation as FunctionExampleEvaluator
        return FunctionExampleEvaluator._compare_ast_nodes(self, node1, node2)

class MethodExampleEvaluator(BaseExampleEvaluator):
    """
    Evaluates the quality of class method docstring examples by testing if they enable
    correct method call prediction.
    """
    
    def get_evaluation_prompt(self, context_code: str, signature: str, example: str) -> str:
        """
        Generates a prompt for LLM to predict the method call line.
        
        Args:
            context_code: The code leading up to method call
            signature: The method signature
            example: The example part of the docstring
            
        Returns:
            A formatted prompt string that can be sent to an LLM for prediction
        """
        prompt = [
            "Given the following context, predict ONLY the next line of code that calls the class method.",
            "Your prediction should be based solely on the method signature and example provided.",
            "",
            "Method signature:",
            "<method_signature>",
            signature,
            "</method_signature>",
            "",
            "Example from docstring:", 
            "<docstring_example>",
            example,
            "</docstring_example>",
            "",
            "Context code leading up to method call:",
            "<context_code>",
            context_code,
            "</context_code>",
            "",
            "IMPORTANT INSTRUCTIONS:",
            "1. Predict ONLY the next line(s) that calls the method",
            "2. Base your prediction solely on the signature and example",
            "3. Include ONLY the method call, no additional explanation", 
            "4. If the method call spans multiple lines, include all necessary lines",
            "5. Ensure the prediction is valid Python syntax",
            "",
            "Your prediction should be enclosed in <prediction></prediction> tags",
        ]
        
        return "\n".join(prompt)
    
    def evaluate_prediction(self, prediction: str, ground_truth: str) -> Tuple[bool, str]:
        """
        Evaluates if the predicted method call matches the ground truth.
        
        Performs robust parsing of both prediction and ground truth to compare:
        1. Object and method names
        2. Argument names and order
        3. Argument values (when literals)
        
        Args:
            prediction: The LLM's predicted method call
            ground_truth: The expected method call
            
        Returns:
            Tuple containing:
            - Boolean indicating if the prediction is correct
            - String explaining why the prediction was correct or incorrect
        """
        # Parse both prediction and ground truth into AST
        pred_ast = ast.parse(prediction.strip()).body[0].value
        truth_ast = ast.parse(ground_truth.strip()).body[0].value
        
        # Verify it's a method call
        if not isinstance(pred_ast, ast.Call) or not isinstance(truth_ast, ast.Call):
            return False, "Not a valid method call"
        
        # For method calls, we need to check both object and method names
        if not isinstance(pred_ast.func, ast.Attribute) or not isinstance(truth_ast.func, ast.Attribute):
            return False, "Not a valid method call (missing object reference)"
        
        # Check object name
        if not self._compare_ast_nodes(pred_ast.func.value, truth_ast.func.value):
            return False, "Object reference mismatch"
        
        # Check method name
        if pred_ast.func.attr != truth_ast.func.attr:
            return False, f"Method name mismatch: expected {truth_ast.func.attr}, got {pred_ast.func.attr}"
        
        # Get argument information
        pred_args = {
            kw.arg: kw.value for kw in pred_ast.keywords
        }
        truth_args = {
            kw.arg: kw.value for kw in truth_ast.keywords
        }
        
        # Check positional arguments
        if len(pred_ast.args) != len(truth_ast.args):
            return False, "Mismatched number of positional arguments"
        
        # Check keyword arguments
        if set(pred_args.keys()) != set(truth_args.keys()):
            return False, "Mismatched keyword argument names"
        
        # Check argument order for positional args
        for i, (p_arg, t_arg) in enumerate(zip(pred_ast.args, truth_ast.args)):
            if not self._compare_ast_nodes(p_arg, t_arg):
                return False, f"Positional argument {i+1} mismatch"
        
        # Check keyword argument values
        for arg_name, t_value in truth_args.items():
            p_value = pred_args[arg_name]
            if not self._compare_ast_nodes(p_value, t_value):
                return False, f"Keyword argument '{arg_name}' value mismatch"
        
        return True, "Method call matches expected usage"
    
    def _compare_ast_nodes(self, node1: ast.AST, node2: ast.AST) -> bool:
        """Helper method to compare two AST nodes."""
        # Reuse the same implementation as FunctionExampleEvaluator
        return FunctionExampleEvaluator._compare_ast_nodes(self, node1, node2) 