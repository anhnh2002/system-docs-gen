# AST Call Graph Analysis Tool

This tool provides functionality to analyze Python codebases by building and querying call graphs using Abstract Syntax Tree (AST) parsing. It helps in understanding code relationships and dependencies between functions, methods, and classes.

## Features

### Call Graph Building
- Automatically builds a complete call graph for a Python repository
- Tracks relationships between functions, methods, and classes
- Handles cross-file dependencies
- Caches AST parsing results for better performance

### Code Component Analysis

The tool provides six main functionalities for analyzing code relationships:

1. **Child Function Analysis** (`get_child_function`)
   - Input: Component signature, file path, and child function name
   - Output: Full code of the function being called
   - Use case: Finding implementation of functions called within your code

2. **Child Method Analysis** (`get_child_method`)
   - Input: Component signature, file path, and child method name
   - Output: Full code of the method being called
   - Use case: Finding implementation of methods called on objects

3. **Child Class Analysis** (`get_child_class`)
   - Input: Component signature, file path, and child class name
   - Output: Class signature and initialization code
   - Use case: Finding class definitions for instantiated objects

4. **Parent Function Analysis** (`get_parent_function`)
   - Input: Component signature, file path, and parent function name
   - Output: Full code of the function that calls the component
   - Use case: Finding where a function is being used

5. **Parent Method Analysis** (`get_parent_method`)
   - Input: Component signature, file path, and parent method name
   - Output: Full code of the method that calls the component
   - Use case: Finding where a method is being called

6. **Parent Class Analysis** (`get_parent_class`)
   - Input: Component signature, file path, and parent class name
   - Output: Full code of the class that uses the component
   - Use case: Finding classes that depend on other classes

## Usage Example

```python
from agent.tool.ast import CallGraphBuilder

# Initialize the builder with repository path
builder = CallGraphBuilder("/path/to/repo")

# Find where a function is called
parent_code = builder.get_parent_function(
    "def process_data(self):",
    "src/data/processor.py",
    "main_function"
)

# Find what methods a class uses
child_code = builder.get_child_method(
    "class DataProcessor:",
    "src/data/processor.py",
    "transform_data"
)
```

## Implementation Details

- Uses Python's built-in `ast` module for code parsing
- Maintains parent-child relationships in AST nodes
- Handles various Python constructs:
  - Function definitions and calls
  - Class definitions and instantiations
  - Method calls (both direct and through objects)
  - Static methods
  - Internal methods
  - Cross-file dependencies

## Limitations

- Currently only supports Python files
- Requires valid Python syntax in source files
- Does not handle dynamic code execution (eval, exec)
- Method resolution is name-based (doesn't handle complex inheritance)
- Doesn't track calls through variables or complex expressions 