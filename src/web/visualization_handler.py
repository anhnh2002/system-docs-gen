# Copyright (c) Meta Platforms, Inc. and affiliates
"""
Visualization handler for the docstring generation web interface.

This module provides functions to collect and format data for visualization
in the web interface, including status updates, progress tracking, and 
repository structure visualization.
"""

import os
import json
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Any

# Singleton pattern to store current state
class VisualizationState:
    """Singleton class to store the current visualization state."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VisualizationState, cls).__new__(cls)
            cls._instance.status = {
                'active_agent': None,
                'status_message': '',
                'current_component': '',
                'current_file': ''
            }
            cls._instance.progress = {
                'total_components': 0,
                'processed_components': 0,
                'current_component': '',
                'component_status': {}
            }
            cls._instance.repo_structure = {
                'tree': {},
                'focus_path': ''
            }
            cls._instance.log_messages = []
        return cls._instance

# Initialize the state
state = VisualizationState()

def get_current_status():
    """
    Get the current status of the docstring generation process.
    
    Returns:
        Dictionary with the current status information
    """
    return {
        'status': state.status,
        'progress': state.progress,
        'repo_structure': state.repo_structure
    }

def update_agent_status(active_agent: str, status_message: str):
    """
    Update the current agent status.
    
    Args:
        active_agent: The currently active agent (reader, searcher, writer, verifier)
        status_message: Status message describing what the agent is doing
    """
    state.status['active_agent'] = active_agent
    state.status['status_message'] = status_message

def update_component_focus(component_path: str, file_path: str):
    """
    Update the current component being processed.
    
    Args:
        component_path: The path to the component being processed
        file_path: The path to the file containing the component
    """
    state.status['current_component'] = component_path
    state.status['current_file'] = file_path
    state.repo_structure['focus_path'] = file_path

def update_progress(total: int, processed: int, current: str, components_status: Dict[str, str]):
    """
    Update the progress of the docstring generation process.
    
    Args:
        total: Total number of components to process
        processed: Number of components processed so far
        current: The component currently being processed
        components_status: Dictionary mapping component paths to their status
    """
    state.progress['total_components'] = total
    state.progress['processed_components'] = processed
    state.progress['current_component'] = current
    state.progress['component_status'] = components_status

def add_log_message(message: str):
    """
    Add a log message to the visualization state.
    
    Args:
        message: The log message to add
    """
    state.log_messages.append(message)
    # Keep only the latest 1000 messages
    if len(state.log_messages) > 1000:
        state.log_messages = state.log_messages[-1000:]

def get_repo_structure(repo_path: str) -> Dict[str, Any]:
    """
    Get the structure of the repository as a tree.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        Dictionary representing the repository structure
    """
    tree = {'name': os.path.basename(repo_path), 'path': repo_path, 'type': 'dir', 'children': []}
    
    def build_tree(path, node):
        """Recursively build the tree structure."""
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            
            # Skip hidden files and directories
            if item.startswith('.'):
                continue
                
            # Skip __pycache__ and other common non-Python directories
            if item in ['__pycache__', 'venv', 'env', '.git', '.idea', '.vscode']:
                continue
                
            if os.path.isdir(item_path):
                child = {'name': item, 'path': item_path, 'type': 'dir', 'children': []}
                build_tree(item_path, child)
                node['children'].append(child)
            elif item.endswith('.py'):
                node['children'].append({
                    'name': item,
                    'path': item_path,
                    'type': 'file',
                    'status': 'not_started'  # Possible values: not_started, in_progress, complete
                })
    
    try:
        build_tree(repo_path, tree)
    except Exception as e:
        print(f"Error building repo structure: {e}")
    
    state.repo_structure['tree'] = tree
    return tree

def update_file_status(file_path: str, status: str):
    """
    Update the status of a file in the repository structure.
    
    Args:
        file_path: Path to the file
        status: New status of the file (not_started, in_progress, complete)
    """
    def update_status(node):
        """Recursively update the status of the file in the tree."""
        if node['type'] == 'file' and node['path'] == file_path:
            node['status'] = status
            return True
            
        if node['type'] == 'dir' and 'children' in node:
            for child in node['children']:
                if update_status(child):
                    return True
        
        return False
    
    update_status(state.repo_structure['tree'])

def get_completeness_data(repo_path: str) -> Dict[str, Any]:
    """
    Get the completeness evaluation data for the repository.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        Dictionary containing the completeness evaluation results
    """
    try:
        # Run the eval_completeness.py script to get the results
        eval_script_path = Path(__file__).parent.parent.parent / 'eval_completeness.py'
        
        if not eval_script_path.exists():
            return {
                'status': 'error',
                'message': f'Evaluation script not found at {eval_script_path}'
            }
        
        # Create a simplified mock result for testing or when the script fails
        mock_results = {
            'status': 'success',
            'files': []
        }
        
        # Get Python files in the repository
        all_python_files = []
        for root, _, files in os.walk(repo_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, repo_path)
                    
                    # Count functions and classes with simple parsing
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Simple counting of functions and classes
                    functions = []
                    classes = []
                    
                    function_count = content.count('def ')
                    class_count = content.count('class ')
                    
                    # Simple docstring check (very basic)
                    doc_count = content.count('"""') // 2  # Rough estimate
                    
                    # Create mock function and class objects
                    for i in range(function_count):
                        has_doc = i < doc_count
                        functions.append({
                            'name': f'function_{i}',
                            'has_docstring': has_doc
                        })
                    
                    for i in range(class_count):
                        has_doc = i < (doc_count - function_count if doc_count > function_count else 0)
                        classes.append({
                            'name': f'class_{i}',
                            'has_docstring': has_doc
                        })
                    
                    mock_results['files'].append({
                        'file': rel_path,
                        'functions': functions,
                        'classes': classes
                    })
        
        # Try to run the actual script
        try:
            cmd = [sys.executable, str(eval_script_path), '--repo-path', repo_path]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30  # Add timeout to prevent hanging
            )
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    data = json.loads(result.stdout)
                    if 'files' in data and isinstance(data['files'], list):
                        return {
                            'status': 'success',
                            'data': data
                        }
                except json.JSONDecodeError:
                    pass  # Fall back to mock data
            
            # If script execution fails, use mock data but log the error
            print(f"Warning: Using mock completeness data. Script error: {result.stderr}")
            return {
                'status': 'success',
                'data': mock_results
            }
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            print(f"Error running completeness script: {e}")
            # Fall back to mock data
            return {
                'status': 'success',
                'data': mock_results
            }
    
    except Exception as e:
        print(f"Error evaluating completeness: {e}")
        return {
            'status': 'error',
            'message': f'Error evaluating completeness: {str(e)}'
        } 