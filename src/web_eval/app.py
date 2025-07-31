# Copyright (c) Meta Platforms, Inc. and affiliates
import os
import sys
import ast
import json
import argparse
from flask import Flask, render_template, request, jsonify, redirect, url_for
from typing import Dict, Any, List

# Add parent directory to path to import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import evaluation modules
from evaluator.completeness import ClassCompletenessEvaluator, FunctionCompletenessEvaluator
from evaluator.helpfulness_summary import DocstringSummaryEvaluator
from evaluator.helpfulness_description import DocstringDescriptionEvaluator
# from evaluator.helpfulness_arguments import DocstringArgumentEvaluator
from evaluator.helpfulness_parameters import DocstringParametersEvaluator
from evaluator.helpfulness_attributes import DocstringAttributeEvaluator
# from evaluator.helpfulness_examples import DocstringExampleEvaluator

# Import our helpers
from src.web_eval.helpers import parse_llm_score_from_text, extract_docstring_component

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'DocAgent-evaluation-system'

# Add template filter for extracting docstring components
@app.template_filter('extract_component')
def extract_component_filter(docstring, component):
    """
    Jinja2 template filter for extracting docstring components.
    
    Args:
        docstring: The full docstring
        component: The component to extract (summary, description, etc.)
        
    Returns:
        The extracted component, or empty string if not found
    """
    result = extract_docstring_component(docstring, component)
    return result or ""

# Global variable to store evaluation results
evaluation_results = {}
config = {}

@app.route('/')
def index():
    """
    Renders the configuration page (entry page).
    
    This page allows users to configure LLM settings and repository path.
    """
    return render_template('index.html')

@app.route('/test_api', methods=['POST'])
def test_api():
    """
    Tests the LLM API connection by sending a simple query.
    
    Returns:
        JSON response with success/failure and any error message
    """
    data = request.get_json()
    
    # Save config for later use
    global config
    config = {
        'llm_type': data.get('llm_type'),
        'api_key': data.get('api_key'),
        'model': data.get('model'),
        'temperature': float(data.get('temperature', 0.1)),
        'max_output_tokens': int(data.get('max_output_tokens', 4096))
    }
    
    # Test API connection based on LLM type
    try:
        if config['llm_type'] == 'openai':
            import openai
            openai.api_key = config['api_key']
            response = openai.chat.completions.create(
                model=config['model'],
                messages=[{"role": "user", "content": "Who are you?"}],
                temperature=config['temperature'],
                max_tokens=100
            )
            return jsonify({"success": True, "response": response.choices[0].message.content})
            
        elif config['llm_type'] == 'claude':
            from anthropic import Anthropic
            client = Anthropic(api_key=config['api_key'])
            response = client.messages.create(
                model=config['model'],
                max_tokens=100,
                temperature=config['temperature'],
                messages=[{"role": "user", "content": "Who are you?"}]
            )
            return jsonify({"success": True, "response": response.content[0].text})
            
        else:
            return jsonify({"success": False, "error": f"Unsupported LLM type: {config['llm_type']}"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/evaluate', methods=['POST'])
def evaluate():
    """
    Initiates the evaluation process for the specified repository.
    
    Returns:
        Redirects to the results page
    """
    data = request.get_json()
    repo_path = data.get('repo_path')
    
    if not os.path.exists(repo_path):
        return jsonify({"success": False, "error": f"Repository path does not exist: {repo_path}"})
    
    try:
        # Start evaluation
        global evaluation_results
        evaluation_results = process_directory(repo_path)
        return jsonify({"success": True, "redirect": url_for('results')})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/results')
def results():
    """
    Renders the evaluation results page.
    """
    return render_template('results.html', results=evaluation_results)

@app.route('/evaluate_helpfulness', methods=['POST'])
def evaluate_helpfulness():
    """
    Evaluates the helpfulness of a specific docstring component.
    
    Returns:
        JSON response with the helpfulness score
    """
    data = request.get_json()
    component_type = data.get('component_type')  # class or function
    component_name = data.get('component_name')
    docstring_part = data.get('docstring_part')  # summary, description, etc.
    docstring_content = data.get('docstring_content')
    signature = data.get('signature', '')
    
    try:
        # Select appropriate evaluator based on docstring part
        evaluator = None
        if docstring_part == 'summary':
            evaluator = DocstringSummaryEvaluator()
        elif docstring_part == 'description':
            evaluator = DocstringDescriptionEvaluator()
        # elif docstring_part == 'arguments':
        #     evaluator = DocstringArgumentsEvaluator()
        elif docstring_part == 'parameters':
            evaluator = DocstringParametersEvaluator()
        elif docstring_part == 'attributes':
            evaluator = DocstringAttributesEvaluator()
        elif docstring_part == 'examples':
            evaluator = DocstringExamplesEvaluator()
        else:
            return jsonify({"success": False, "error": f"Unsupported docstring part: {docstring_part}"})
        
        # Generate prompt
        prompt = evaluator.get_evaluation_prompt(signature, docstring_content)
        
        # Call LLM API based on configured type
        if config['llm_type'] == 'openai':
            import openai
            openai.api_key = config['api_key']
            response = openai.chat.completions.create(
                model=config['model'],
                messages=[{"role": "user", "content": prompt}],
                temperature=config['temperature'],
                max_tokens=config['max_output_tokens']
            )
            llm_response = response.choices[0].message.content
            
        elif config['llm_type'] == 'claude':
            from anthropic import Anthropic
            client = Anthropic(api_key=config['api_key'])
            response = client.messages.create(
                model=config['model'],
                max_tokens=config['max_output_tokens'],
                temperature=config['temperature'],
                messages=[{"role": "user", "content": prompt}]
            )
            llm_response = response.content[0].text
            
        else:
            return jsonify({"success": False, "error": f"Unsupported LLM type: {config['llm_type']}"})
        
        # Parse LLM response to get score
        score, explanation = parse_llm_score_from_text(llm_response)
        
        # Update evaluation results with helpfulness score
        if component_type == 'class':
            for cls in evaluation_results['classes']:
                if cls['name'] == component_name:
                    if 'helpfulness_scores' not in cls:
                        cls['helpfulness_scores'] = {}
                    cls['helpfulness_scores'][docstring_part] = {
                        'score': score,
                        'explanation': explanation
                    }
                    break
        else:  # function or method
            for func in evaluation_results['functions']:
                if func['name'] == component_name:
                    if 'helpfulness_scores' not in func:
                        func['helpfulness_scores'] = {}
                    func['helpfulness_scores'][docstring_part] = {
                        'score': score,
                        'explanation': explanation
                    }
                    break
        
        return jsonify({
            "success": True, 
            "score": score, 
            "explanation": explanation
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/refresh', methods=['POST'])
def refresh_evaluation():
    """
    Refreshes the completeness evaluation results.
    
    Returns:
        Redirects to the updated results page
    """
    data = request.get_json()
    repo_path = data.get('repo_path')
    
    try:
        # Re-run evaluation
        global evaluation_results
        evaluation_results = process_directory(repo_path)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

def run_docstring_tests(source_file: str) -> Dict[str, Any]:
    """
    Run comprehensive docstring evaluation tests on a Python source file.
    
    This function reads a Python file and evaluates docstrings for all classes,
    functions, and methods found within. It provides detailed evaluation results.
    
    Args:
        source_file: Path to the Python file to analyze
        
    Returns:
        Dictionary containing evaluation results for each found element
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
            # Get actual docstring content
            class_docstring = ast.get_docstring(node) or ""
            
            class_result = {
                'name': node.name,
                'type': 'class',
                'docstring': class_docstring,
                'signature': f"class {node.name}:",
                'completeness_score': class_evaluator.evaluate(node),
                'completeness_elements': class_evaluator.element_scores.copy(),
                'element_required': class_evaluator.element_required.copy()
            }
            results['classes'].append(class_result)
            
            # Evaluate methods within the class
            for method in [n for n in ast.iter_child_nodes(node) if isinstance(n, ast.FunctionDef)]:
                # Skip __init__ methods for display purposes
                if method.name == '__init__':
                    continue
                
                # Get actual method docstring content
                method_docstring = ast.get_docstring(method) or ""
                
                method_result = {
                    'name': f"{node.name}.{method.name}",
                    'type': 'method',
                    'docstring': method_docstring,
                    'signature': f"def {method.name}():",  # Simplified signature
                    'completeness_score': func_evaluator.evaluate(method),
                    'completeness_elements': func_evaluator.element_scores.copy(),
                    'element_required': func_evaluator.element_required.copy()
                }
                results['functions'].append(method_result)
                
        elif isinstance(node, ast.FunctionDef):
            # Get actual function docstring content
            func_docstring = ast.get_docstring(node) or ""
            
            # Only process top-level functions
            func_result = {
                'name': node.name,
                'type': 'function',
                'docstring': func_docstring,
                'signature': f"def {node.name}():",  # Simplified signature
                'completeness_score': func_evaluator.evaluate(node),
                'completeness_elements': func_evaluator.element_scores.copy(),
                'element_required': func_evaluator.element_required.copy()
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
    # Initialize aggregate results
    aggregate_results = {
        'status': 'success',
        'directory': directory_path,
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
    for root, _, files in os.walk(directory_path):
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
            aggregate_results['statistics']['successful_files'] = aggregate_results['statistics'].get('successful_files', 0) + 1
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
            aggregate_results['statistics']['failed_files'] = aggregate_results['statistics'].get('failed_files', 0) + 1
    
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

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Docstring Evaluation Web App')
    parser.add_argument('--host', type=str, default='0.0.0.0', 
                        help='Host address to bind to (default: 0.0.0.0 - accessible from outside)')
    parser.add_argument('--port', type=int, default=5000, 
                        help='Port to run the server on (default: 5000)')
    parser.add_argument('--debug', action='store_true', 
                        help='Run in debug mode (default: False)')
    
    args = parser.parse_args()
    
    # Print access information
    if args.host == '0.0.0.0':
        print(f"\n🚀 DocAgent web server starting!")
        print(f"💻 Local access: http://localhost:{args.port}")
        print(f"🌐 Network access: http://<server-ip>:{args.port}")
        print(f"   (Replace <server-ip> with your server's IP address)")
        if args.debug:
            print(f"⚠️  Running in debug mode - not recommended for production use")
        print("\nPress CTRL+C to stop the server\n")
    
    # Run the Flask app
    app.run(host=args.host, port=args.port, debug=args.debug) 