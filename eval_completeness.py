# Copyright (c) Meta Platforms, Inc. and affiliates
import ast
import os
from typing import Dict, Any, List, Union
from pathlib import Path
from evaluator.completeness import ClassCompletenessEvaluator, FunctionCompletenessEvaluator
from tabulate import tabulate

def run_docstring_tests(source_file: str) -> Dict[str, Any]:
    """
    Run comprehensive docstring evaluation tests on a Python source file.
    
    This function reads a Python file and evaluates docstrings for all classes,
    functions, and methods found within. It provides detailed evaluation results
    using different evaluators.
    
    Args:
        source_file: Path to the Python file to analyze
        
    Returns:
        Dictionary containing evaluation results for each found element
        
    Example:
        >>> results = run_docstring_tests('my_module.py')
        >>> print(results['functions'][0])
        1.0
    """
    with open(source_file, 'r', encoding='utf-8') as f:
        source = f.read()
    
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {
            'status': 'error',
            'message': f'Failed to parse {source_file}: {str(e)}'
        }
    
    results = {
        'status': 'success',
        'file': source_file,
        'classes': [],
        'functions': [],
        'debug_info': {}
    }
    
    # Instantiate evaluators
    class_evaluator = ClassCompletenessEvaluator()
    func_evaluator = FunctionCompletenessEvaluator()
    
    # Process all nodes in the AST
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            class_result = {
                'name': node.name,
                'type': 'class',
                'completeness_score': class_evaluator.evaluate(node),
                'completeness_elements': class_evaluator.element_scores,
                'element_required': class_evaluator.element_required
            }
            results['classes'].append(class_result)
            
            # Evaluate methods within the class
            for method in [n for n in ast.iter_child_nodes(node) if isinstance(n, ast.FunctionDef)]:
                # Skip __init__ methods
                if method.name == '__init__':
                    continue
                    
                method_result = {
                    'name': f"{node.name}.{method.name}",
                    'type': 'method',
                    'completeness_score': func_evaluator.evaluate(method),
                    'completeness_elements': func_evaluator.element_scores,
                    'element_required': func_evaluator.element_required
                }
                results['functions'].append(method_result)
                
        elif isinstance(node, ast.FunctionDef):
            # Only process top-level functions
            func_result = {
                'name': node.name,
                'type': 'function',
                'completeness_score': func_evaluator.evaluate(node),
                'completeness_elements': func_evaluator.element_scores,
                'element_required': func_evaluator.element_required
            }
            results['functions'].append(func_result)
    
    # Add overall statistics
    results['statistics'] = {
        'total_classes': len(results['classes']),
        'total_functions': len(results['functions']),
        'average_class_score': sum(r['completeness_score'] for r in results['classes']) / 
                             max(1, len(results['classes'])),
        'average_function_score': sum(r['completeness_score'] for r in results['functions']) / 
                                max(1, len(results['functions']))
    }
    
    return results

def process_directory(directory_path: str) -> Dict[str, Any]:
    """
    Process all Python files in a directory and its subdirectories.
    
    Args:
        directory_path: Path to the directory to analyze
        
    Returns:
        Dictionary containing aggregated evaluation results for all files
    """
    directory = Path(directory_path)
    
    # Initialize aggregate results
    aggregate_results = {
        'status': 'success',
        'directory': str(directory),
        'files': [],
        'file_results': [],
        'classes': [],
        'functions': [],
        'statistics': {
            'total_files': 0,
            'successful_files': 0,
            'failed_files': 0,
            'total_classes': 0,
            'total_functions': 0,
            'average_class_score': 0.0,
            'average_function_score': 0.0,
            'overall_average_score': 0.0
        }
    }
    
    # Find all Python files recursively
    python_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    if not python_files:
        aggregate_results['status'] = 'error'
        aggregate_results['message'] = f'No Python files found in {directory_path}'
        return aggregate_results
    
    aggregate_results['statistics']['total_files'] = len(python_files)
    
    # Process each Python file
    all_class_scores = []
    all_function_scores = []
    
    for py_file in python_files:
        file_result = run_docstring_tests(py_file)
        
        if file_result['status'] == 'success':
            aggregate_results['successful_files'] = aggregate_results['statistics']['successful_files'] + 1
            aggregate_results['file_results'].append(file_result)
            aggregate_results['files'].append(py_file)
            
            # Accumulate classes and functions with file path context
            for class_result in file_result['classes']:
                class_result['file'] = py_file
                aggregate_results['classes'].append(class_result)
                all_class_scores.append(class_result['completeness_score'])
            
            for func_result in file_result['functions']:
                func_result['file'] = py_file
                aggregate_results['functions'].append(func_result)
                all_function_scores.append(func_result['completeness_score'])
                
            # Update statistics
            aggregate_results['statistics']['total_classes'] += file_result['statistics']['total_classes']
            aggregate_results['statistics']['total_functions'] += file_result['statistics']['total_functions']
        else:
            aggregate_results['statistics']['failed_files'] += 1
    
    # Calculate average scores
    if all_class_scores:
        aggregate_results['statistics']['average_class_score'] = sum(all_class_scores) / len(all_class_scores)
    
    if all_function_scores:
        aggregate_results['statistics']['average_function_score'] = sum(all_function_scores) / len(all_function_scores)
    
    # Calculate overall average score (classes and functions combined)
    all_scores = all_class_scores + all_function_scores
    if all_scores:
        aggregate_results['statistics']['overall_average_score'] = sum(all_scores) / len(all_scores)
    
    return aggregate_results

def print_evaluation_results(results: Dict[str, Any]) -> None:
    """
    Pretty print the evaluation results in a readable format with colors.
    
    Args:
        results: Dictionary containing evaluation results from run_docstring_tests
    """
    # ANSI color codes
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'
    
    # Check if this is a directory result or a file result
    is_directory = 'directory' in results
    
    if is_directory:
        # Print directory path
        print(f"\n{BOLD}Evaluating Python files in directory: {results['directory']}{ENDC}")
        print("=" * 80)
        
        # Print file summary
        print(f"\n{BLUE}{BOLD}FILE SUMMARY:{ENDC}")
        stats_data = [
            ['Total Files', results['statistics']['total_files']],
            ['Successfully Processed Files', results['statistics']['successful_files']],
            ['Failed Files', results['statistics']['failed_files']]
        ]
        print(tabulate(stats_data, tablefmt='simple'))
        
        # Print overall statistics
        print(f"\n{BLUE}{BOLD}OVERALL STATISTICS:{ENDC}")
        
        # Add colored statistics
        class_score = results['statistics']['average_class_score']
        if class_score >= 0.8:
            class_score_str = f"{GREEN}{class_score:.2f}{ENDC}"
        elif class_score >= 0.5:
            class_score_str = f"{YELLOW}{class_score:.2f}{ENDC}"
        else:
            class_score_str = f"{RED}{class_score:.2f}{ENDC}"
            
        func_score = results['statistics']['average_function_score']
        if func_score >= 0.8:
            func_score_str = f"{GREEN}{func_score:.2f}{ENDC}"
        elif func_score >= 0.5:
            func_score_str = f"{YELLOW}{func_score:.2f}{ENDC}"
        else:
            func_score_str = f"{RED}{func_score:.2f}{ENDC}"
            
        overall_score = results['statistics']['overall_average_score']
        if overall_score >= 0.8:
            overall_score_str = f"{GREEN}{overall_score:.2f}{ENDC}"
        elif overall_score >= 0.5:
            overall_score_str = f"{YELLOW}{overall_score:.2f}{ENDC}"
        else:
            overall_score_str = f"{RED}{overall_score:.2f}{ENDC}"
        
        stats_data = [
            ['Total Classes', results['statistics']['total_classes']],
            ['Total Functions/Methods', results['statistics']['total_functions']],
            ['Average Class Score', class_score_str],
            ['Average Function Score', func_score_str],
            ['Overall Average Score', overall_score_str]
        ]
        print(tabulate(stats_data, tablefmt='simple'))
        
        # Ask if the user wants to see details for individual files
        print(f"\nUse python {os.path.basename(__file__)} <specific_file_path> to see detailed results for a specific file.")
        
    else:
        # Original single file display logic
        # Print file path
        print(f"\n{BOLD}Evaluating Python file: {results['file']}{ENDC}")
        print("=" * 80)
        
        # Print class results table
        if results['classes']:
            print(f"\n{BLUE}{BOLD}CLASSES:{ENDC}")
            
            headers = ['Class Name', 'Score']
            elements = list(results['classes'][0]['completeness_elements'].keys())
            headers.extend(elements)
            
            table_data = []
            for class_result in results['classes']:
                row = [class_result['name']]
                score = class_result['completeness_score']
                # Color the score based on value
                if score >= 0.8:
                    score_str = f"{GREEN}{score:.2f}{ENDC}"
                elif score >= 0.5:
                    score_str = f"{YELLOW}{score:.2f}{ENDC}"
                else:
                    score_str = f"{RED}{score:.2f}{ENDC}"
                row.append(score_str)
                
                for element in elements:
                    required = class_result['element_required'][element]
                    has_element = class_result['completeness_elements'][element]
                    if has_element:
                        check = f"{GREEN}✓{ENDC}"
                    else:
                        check = f"{RED}✗{ENDC}"
                    cell = f"{YELLOW if required else '-'}{'R' if required else ''}{ENDC if required else ''} | {check}"
                    row.append(cell)
                
                table_data.append(row)
                
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        # Print function/method results table
        if results['functions']:
            print(f"\n{BLUE}{BOLD}FUNCTIONS/METHODS:{ENDC}")
            
            headers = ['Function Name', 'Type', 'Score']
            elements = list(results['functions'][0]['completeness_elements'].keys())
            headers.extend(elements)
            
            table_data = []
            for func_result in results['functions']:
                row = [func_result['name'], func_result['type']]
                score = func_result['completeness_score']
                # Color the score based on value
                if score >= 0.8:
                    score_str = f"{GREEN}{score:.2f}{ENDC}"
                elif score >= 0.5:
                    score_str = f"{YELLOW}{score:.2f}{ENDC}"
                else:
                    score_str = f"{RED}{score:.2f}{ENDC}"
                row.append(score_str)
                
                for element in elements:
                    required = func_result['element_required'][element]
                    has_element = func_result['completeness_elements'][element]
                    if has_element:
                        check = f"{GREEN}✓{ENDC}"
                    else:
                        check = f"{RED}✗{ENDC}"
                    cell = f"{YELLOW if required else '-'}{'R' if required else ''}{ENDC if required else ''} | {check}"
                    row.append(cell)
                
                table_data.append(row)
                
            print(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        # Print overall statistics
        print(f"\n{BLUE}{BOLD}OVERALL STATISTICS:{ENDC}")
        stats_data = []
        
        # Add colored statistics
        class_score = results['statistics']['average_class_score']
        if class_score >= 0.8:
            class_score_str = f"{GREEN}{class_score:.2f}{ENDC}"
        elif class_score >= 0.5:
            class_score_str = f"{YELLOW}{class_score:.2f}{ENDC}"
        else:
            class_score_str = f"{RED}{class_score:.2f}{ENDC}"
            
        func_score = results['statistics']['average_function_score']
        if func_score >= 0.8:
            func_score_str = f"{GREEN}{func_score:.2f}{ENDC}"
        elif func_score >= 0.5:
            func_score_str = f"{YELLOW}{func_score:.2f}{ENDC}"
        else:
            func_score_str = f"{RED}{func_score:.2f}{ENDC}"
            
        stats_data = [
            ['Total Classes', results['statistics']['total_classes']],
            ['Total Functions/Methods', results['statistics']['total_functions']],
            ['Average Class Score', class_score_str],
            ['Average Function Score', func_score_str]
        ]
        print(tabulate(stats_data, tablefmt='simple'))

if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python eval_completeness.py <path_to_python_file_or_directory>")
        sys.exit(1)
    
    path = sys.argv[1]
    if not Path(path).exists():
        print(f"Error: Path not found: {path}")
        sys.exit(1)
    
    if Path(path).is_dir():
        # Process directory
        results = process_directory(path)
        if results['status'] == 'success':
            print_evaluation_results(results)
        else:
            print(f"Error: {results['message']}")
    else:
        # Process single file
        results = run_docstring_tests(path)
        if results['status'] == 'success':
            print_evaluation_results(results)
        else:
            print(f"Error: {results['message']}")