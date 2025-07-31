# Copyright (c) Meta Platforms, Inc. and affiliates
import json
import os
import re
import sys
from typing import List, Dict, Any, Set, Tuple
import google.generativeai as genai
from tqdm import tqdm
import pandas as pd
from collections import defaultdict

# Constants
SYSTEMS = [
    "copy_paste_codellama34b",
    "copy_paste_gpt4o_mini",
    "docassist-codellama34b",
    "docassist-gpt4o_mini",
    "fim-codellama13b",
]

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not set")

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

def extract_components_from_docstring(docstring: str) -> List[str]:
    """
    Extract code components (classes, methods, functions) mentioned in a docstring
    using Gemini API.
    
    Args:
        docstring: The docstring text to analyze
        
    Returns:
        List of code component names mentioned in the docstring
    """
    prompt = f"""
    Please extract all the non-common (very likely to be newly-defined in the repository) code components (classes, methods, functions) mentioned in 
    the following docstring. 

    Ignore the example part of the docstring if it exists (the code component you extract should not come from the example code).
    
    For example, "List" is a very common class, so it should not be included.
    On the other hand, "InMemoryCache" is not a common class, so it should be included.

    Return only a Python list of strings with the exact names.
    If no code components are mentioned, return an empty list.
    
    Docstring:
    ```
    {docstring}
    ```
    
    Format your response as a Python list wrapped in XML tags like this:
    <python_list>["ClassA", "method_b", "function_c"]</python_list>
    """
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Extract list from XML tags
        match = re.search(r'<python_list>(.*?)</python_list>', response_text, re.DOTALL)
        if match:
            list_str = match.group(1)
            try:
                # Safely evaluate the list string
                components = eval(list_str)
                if isinstance(components, list):
                    return components
            except:
                # If evaluation fails, extract strings manually
                components = re.findall(r'"([^"]*)"', list_str)
                return components
        
        # Fallback: try to extract using regex for regular list
        match = re.search(r'\[.*?\]', response_text, re.DOTALL)
        if match:
            list_str = match.group(0)
            try:
                # Safely evaluate the list string
                components = eval(list_str)
                if isinstance(components, list):
                    return components
            except:
                # If evaluation fails, extract strings manually
                components = re.findall(r'"([^"]*)"', list_str)
                return components
        
        # Fallback: try to find any mention of code looking elements
        components = re.findall(r'`([^`]+)`', docstring)
        return [c for c in components if not c.startswith('(') and not c.endswith(')')]
    
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        # Fallback: try to find any mention of code looking elements
        components = re.findall(r'`([^`]+)`', docstring)
        return [c for c in components if not c.startswith('(') and not c.endswith(')')]

def load_dependency_graph(repo_name: str) -> Dict[str, Any]:
    """
    Load the dependency graph for a given repository.
    
    Args:
        repo_name: Repository name
        
    Returns:
        Dependency graph data
    """
    file_path = f"output/dependency_graphs/{repo_name}_dependency_graph.json"
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Dependency graph not found: {file_path}")
        return {}
    
def check_component_existence(
    component_name: str, 
    dependency_graph: Dict[str, Any],
    docstring_path: str
) -> Tuple[bool, bool]:
    """
    Check if a component exists in the dependency graph and if it's a cross-file reference.
    
    Args:
        component_name: Name of the component to check
        dependency_graph: Dependency graph data
        docstring_path: Path of the docstring's component
        
    Returns:
        Tuple of (exists, is_cross_file)
    """
    exists = False
    is_cross_file = False
    
    docstring_relative_path = None
    if "/" in docstring_path:
        # Extract the relative path from the docstring path
        parts = docstring_path.split("/")
        repo_name = parts[1]
        relative_path = "/".join(parts[1:-1])
        docstring_relative_path = relative_path
    
    for comp_id, comp_data in dependency_graph.items():
        # Check if the component name is in the ID
        if component_name in comp_id.split(".")[-1]:
            exists = True
            
            # Check if it's a cross-file reference
            if docstring_relative_path and "relative_path" in comp_data:
                comp_relative_path = comp_data["relative_path"]
                if docstring_relative_path != comp_relative_path:
                    is_cross_file = True
            
            break
    
    return exists, is_cross_file

def main():
    # Load completeness evaluation data
    print("Loading completeness evaluation data...")
    with open("experiments/eval/results/completeness_evaluation_cleaned.json", 'r') as f:
        completeness_data = json.load(f)
    
    results = {}
    
    # Process each component in the completeness data
    for component_path, component_data in tqdm(completeness_data.items()):
        if "docstrings" not in component_data:
            continue
        
        # Extract repo name
        parts = component_path.split("/")
        repo_name = parts[1]
        # replace all - in reponame to _
        repo_name = repo_name.replace("-", "_")
        
        # Load dependency graph for this repo (once)
        if repo_name not in results:
            print(f"Loading dependency graph for {repo_name}...")
            dependency_graph = load_dependency_graph(repo_name)
            results[repo_name] = {}
        
        # For each system, analyze the docstring
        for system in SYSTEMS:
            if system not in component_data["docstrings"]:
                continue
                
            docstring = component_data["docstrings"][system]["docstring"]
            
            # Extract mentioned components from docstring
            components = extract_components_from_docstring(docstring)
            
            # Check existence of each component in the dependency graph
            component_results = []
            for comp in components:
                exists, is_cross_file = check_component_existence(
                    comp, dependency_graph, component_path
                )
                
                component_results.append({
                    "name": comp,
                    "exists": exists,
                    "is_cross_file": is_cross_file
                })
            
            # Store results
            if component_path not in results[repo_name]:
                results[repo_name][component_path] = {}
            
            results[repo_name][component_path][system] = {
                "mentioned_components": component_results,
                "total_mentions": len(components),
                "existing_mentions": sum(1 for c in component_results if c["exists"]),
                "cross_file_mentions": sum(1 for c in component_results if c["is_cross_file"])
            }
    
    # Save detailed results
    with open("experiments/eval/results/docstring_truthfulness_evaluation.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    # Generate summary report
    generate_summary_report(results)

def generate_summary_report(results: Dict[str, Dict[str, Dict[str, Any]]]):
    """
    Generate a summary report comparing the five systems.
    
    Args:
        results: The evaluation results
    """
    # Aggregate statistics
    stats = {
        system: {
            "total_components_mentioned": 0,
            "existing_components": 0,
            "cross_file_mentions": 0,
            "docstrings_analyzed": 0
        }
        for system in SYSTEMS
    }
    
    # Calculate statistics
    for repo_name, repo_data in results.items():
        for component_path, comp_data in repo_data.items():
            for system, system_data in comp_data.items():
                if system in SYSTEMS:
                    stats[system]["total_components_mentioned"] += system_data["total_mentions"]
                    stats[system]["existing_components"] += system_data["existing_mentions"]
                    stats[system]["cross_file_mentions"] += system_data["cross_file_mentions"]
                    stats[system]["docstrings_analyzed"] += 1
    
    # Calculate ratios
    for system in SYSTEMS:
        total = stats[system]["total_components_mentioned"]
        if total > 0:
            stats[system]["existence_ratio"] = stats[system]["existing_components"] / total
        else:
            stats[system]["existence_ratio"] = 0
            
        if stats[system]["existing_components"] > 0:
            stats[system]["cross_file_ratio"] = stats[system]["cross_file_mentions"] / stats[system]["existing_components"]
        else:
            stats[system]["cross_file_ratio"] = 0
            
        if stats[system]["docstrings_analyzed"] > 0:
            stats[system]["avg_mentions_per_doc"] = total / stats[system]["docstrings_analyzed"]
        else:
            stats[system]["avg_mentions_per_doc"] = 0
    
    # Create markdown report
    report = "# Docstring Truthfulness Evaluation Report\n\n"
    
    # Table 1: Component Existence
    report += "## Component Existence Ratio (higher is better)\n\n"
    report += "| System | Components Mentioned | Existing Components | Existence Ratio |\n"
    report += "|--------|---------------------|---------------------|-----------------|\n"
    
    for system in SYSTEMS:
        report += f"| {system} | {stats[system]['total_components_mentioned']} | {stats[system]['existing_components']} | {stats[system]['existence_ratio']:.2%} |\n"
    
    # Table 2: Component Mentions
    report += "\n## Component Mention Frequency (higher is better)\n\n"
    report += "| System | Docstrings Analyzed | Total Components | Avg Mentions Per Doc |\n"
    report += "|--------|---------------------|------------------|-----------------------|\n"
    
    for system in SYSTEMS:
        report += f"| {system} | {stats[system]['docstrings_analyzed']} | {stats[system]['total_components_mentioned']} | {stats[system]['avg_mentions_per_doc']:.2f} |\n"
    
    # Table 3: Cross-file References
    report += "\n## Cross-file References (higher is better)\n\n"
    report += "| System | Existing Components | Cross-file References | Cross-file Ratio |\n"
    report += "|--------|---------------------|----------------------|-----------------|\n"
    
    for system in SYSTEMS:
        report += f"| {system} | {stats[system]['existing_components']} | {stats[system]['cross_file_mentions']} | {stats[system]['cross_file_ratio']:.2%} |\n"
    
    # Save the report
    with open("experiments/eval/results/docstring_truthfulness_report.md", 'w') as f:
        f.write(report)
        
    print("Summary report generated: docstring_truthfulness_report.md")

if __name__ == "__main__":
    main() 