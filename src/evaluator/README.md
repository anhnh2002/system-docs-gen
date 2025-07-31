# Docstring Quality Evaluator

provides a robust framework for evaluating the quality of Python docstrings. It uses static analysis through the Abstract Syntax Tree (AST) to examine docstrings in Python code and assess their completeness based on established documentation standards.

## Architecture Overview

The project follows a hierarchical design with clear separation of concerns:

### Base Evaluator

The foundation of the evaluation system is the `BaseEvaluator` abstract class. This class establishes the core interface that all evaluators must implement:

```python
class BaseEvaluator(ABC):
    def __init__(self, name: str, description: str):
        self._score: float = 0.0
        self._name = name
        self._description = description
```

Every evaluator derives from this base class, ensuring consistent scoring behavior and interface across the system. The base evaluator enforces score validation (must be between 0 and 1) and provides the abstract `evaluate` method that all concrete evaluators must implement.

### Completeness Evaluation

The completeness evaluation system is structured in three layers:

1. `CompletenessEvaluator`: The base class for completeness evaluation
2. `ClassCompletenessEvaluator`: Specializes in evaluating class docstrings
3. `FunctionCompletenessEvaluator`: Specializes in evaluating function/method docstrings

#### Class Docstring Evaluation

The `ClassCompletenessEvaluator` examines four essential elements of class documentation:

1. **Summary** (required)
   - A one-line description at the start of the docstring
   - Must be the first non-empty line
   - Should provide a quick overview of the class's purpose

2. **Description** (required)
   - Detailed explanation following the summary
   - Multiple lines describing the class's functionality
   - Appears before any special sections (Attributes, Examples, etc.)
   
3. **Attributes** (required if class has attributes)
   - Documentation of class attributes
   - Must start with "Attributes:" section
   - Lists each attribute with type information and description
   - Required if class has class variables, instance variables in __init__, or enum values

4. **Parameters** (required if class has __init__ parameters)
   - Documentation of constructor parameters
   - Must start with "Parameters:" section
   - Lists each parameter with type information and description
   - Required if __init__ has parameters beyond self

5. **Examples** (required for public classes)
   - Usage examples showing how to use the class
   - Must start with "Example:" or "Examples:" section
   - Should include executable code snippets
   - Only required for classes not starting with underscore (_)

Each element is evaluated independently through dedicated methods:
```python
@staticmethod
def evaluate_summary(docstring: str) -> float:
    """Evaluates if a proper one-liner summary exists."""

@staticmethod
def evaluate_description(docstring: str) -> float:
    """Evaluates if a proper description section exists."""

@staticmethod
def evaluate_attributes(docstring: str) -> float:
    """Evaluates if attribute documentation exists."""

@staticmethod
def evaluate_examples(docstring: str) -> float:
    """Evaluates if usage examples exist."""
```

#### Function Docstring Evaluation

The `FunctionCompletenessEvaluator` examines up to six elements, with required elements determined dynamically based on the function's characteristics:

1. **Summary** (required for all functions)
   - One-line description at the start
   - Concise explanation of function's purpose

2. **Description** (required for all functions)
   - Detailed explanation of functionality
   - Implementation details and usage notes

3. **Arguments** (required if function has parameters)
   - Documentation for each parameter
   - Must start with "Args:" or "Arguments:"
   - Includes type information and description

4. **Returns** (required if function has return statement)
   - Documentation of return value
   - Must start with "Returns:"
   - Includes type information and description

5. **Raises** (required if function has raise statements)
   - Documentation of exceptions
   - Must start with "Raises:"
   - Lists each exception type and trigger condition

6. **Examples** (required for public functions)
   - Usage examples
   - Must start with "Example:" or "Examples:"
   - Not required for private methods (starting with underscore)

The evaluator automatically determines required sections through AST analysis:
```python
def _get_required_sections(self, node: ast.FunctionDef) -> List[str]:
    """Determines which sections are required based on function characteristics."""
```

### Scoring System

Both evaluators use a normalized scoring system:

1. Each required element contributes equally to the final score
2. Scores are always between 0.0 and 1.0
3. Individual element scores are stored in `element_scores` dictionary
4. Final score is the average of all required element scores

For example, if a class docstring has all elements except examples:
```python
element_scores = {
    'summary': 1.0,
    'description': 1.0,
    'attributes': 1.0,
    'examples': 0.0
}
final_score = 0.75  # (1.0 + 1.0 + 1.0 + 0.0) / 4
```

## Usage Examples

### Evaluating a Class Docstring

```python
from docstring_evaluator import ClassCompletenessEvaluator
import ast

# Create evaluator
evaluator = ClassCompletenessEvaluator()

# Define class with docstring
class_code = '''
class MyClass:
    """
    A demonstration class.

    This class shows proper docstring formatting.

    Attributes:
        name (str): The class name.

    Example:
        >>> obj = MyClass()
    """
    pass
'''

# Parse and evaluate
node = ast.parse(class_code).body[0]
score = evaluator.evaluate(node)
print(f"Overall score: {score}")
print("Element scores:", evaluator.element_scores)
```

### Evaluating a Function Docstring

```python
from docstring_evaluator import FunctionCompletenessEvaluator
import ast

# Create evaluator
evaluator = FunctionCompletenessEvaluator()

# Define function with docstring
function_code = '''
def process_data(data: List[str]) -> Dict[str, int]:
    """
    Process a list of strings and return word frequencies.

    This function takes a list of strings and returns a dictionary
    containing the frequency of each word.

    Args:
        data (List[str]): List of strings to process.

    Returns:
        Dict[str, int]: Dictionary mapping words to their frequencies.

    Raises:
        ValueError: If input list is empty.

    Example:
        >>> process_data(["hello", "world", "hello"])
        {'hello': 2, 'world': 1}
    """
    if not data:
        raise ValueError("Empty input list")
    return Counter(data)
'''

# Parse and evaluate
node = ast.parse(function_code).body[0]
score = evaluator.evaluate(node)
print(f"Overall score: {score}")
print("Element scores:", evaluator.element_scores)
```

### Exception Handling Guidelines

The evaluator checks for uncaught exceptions in two ways:

1. Direct raise statements:
   - Walks through all raise statements in the function
   - Checks if each raise is inside a try-except block
   - If a raise is not caught by any except handler, it's considered to bubble up

2. Function calls:
   - Walks through all function call nodes
   - Assumes any uncaught function call could potentially raise
   - Checks if the call is inside a try-except block
   - If not caught, considers it as a potential exception source

The evaluator uses AST traversal to track parent-child relationships and determine if exceptions are properly handled within the function scope.

### Function Analysis Limitations

- Nested functions (functions defined inside other functions) are not evaluated by the tool. These inner functions are skipped during analysis.


### Other Notes

- __init__ function is not evaluated. (will be considered during the evaluation of the class)


## Best Practices for Documentation

To achieve high scores, follow these guidelines:

1. Always start with a clear, one-line summary
2. Provide detailed description in subsequent paragraphs
3. Document all attributes for classes
4. Include practical usage examples
5. For functions:
   - Document all parameters under "Args:"
   - Specify return type and value under "Returns:"
   - List all possible exceptions under "Raises:"
   - Provide examples for public functions

## Development

### Adding New Evaluators

To create new evaluators:

1. Inherit from `BaseEvaluator`
2. Implement the `evaluate` method
3. Define specific evaluation criteria
4. Add unit tests

Example:
```python
class StyleEvaluator(BaseEvaluator):
    """Evaluates docstring style consistency."""
    
    def evaluate(self, node: ast.AST) -> float:
        # Implementation here
        pass
```

# Limitations

- the elements must start with the included labels. (see definition of evaluators) Otherwise, the evaluator will not be able to detect the element.
    - except summary and description. (which is detected by the first and second non-empty line)
- each element must seperate by at least one empty line.