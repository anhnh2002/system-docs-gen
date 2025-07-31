# Copyright (c) Meta Platforms, Inc. and affiliates
import os
import ast
import json
from tqdm import tqdm
import argparse
import re
from langdetect import detect

def is_english(text):
    """Check if text contains only English using langdetect."""
    try:
        return detect(text) == 'en' and text.isascii()
    except:
        return False

def is_high_quality_file_docstring(docstring):
    """Heuristic for file-level docstrings: 
    - At least one meaningful sentence and length ≥ 10 chars."""
    if not docstring or len(docstring.strip()) < 10:
        return False
    else:
        return True

    # Check if it seems like a sentenc

def is_high_quality_class_docstring(docstring):
    """Heuristic for class docstrings:
    - At least 2 lines
    - Possibly mentions common docstring sections (Attributes, Args, Returns)"""
    if not docstring:
        return False
    lines = docstring.strip().split('\n')
    if len(lines) < 2:
        return False
    keywords = ["Attributes", "Args", "Returns", "Example", "Methods", "Param", "arguments", "Parameters"]
    if any(kw in docstring for kw in keywords):
        return True
    # If at least moderately long, consider it acceptable
    if len(docstring.strip()) > 30:
        return True
    return False

def is_high_quality_function_docstring(docstring):
    """Heuristic for function or class method docstrings:
    - At least 3 lines
    - Mention parameters, args, or returns
    """
    if not docstring:
        return False
    lines = docstring.strip().split('\n')
    if len(lines) < 3:
        return False
    keywords = ["Parameters", "Args", "Returns", "Param", "arguments"]
    if any(kw.lower() in docstring.lower() for kw in keywords):
        return True
    # If reasonably long (>30 chars), consider it good
    if len(docstring.strip()) > 30:
        return True
    return False

def is_high_quality_docstring(docstring, doc_type):
    """Check if docstring meets quality criteria and is in English."""
    if not docstring:
        return False
        
    # First check if it's English
    if not is_english(docstring):
        return False
        
    # Then apply other quality checks
    if doc_type == "file":
        return is_high_quality_file_docstring(docstring)
    elif doc_type == "class":
        return is_high_quality_class_docstring(docstring)
    elif doc_type in ("function", "class_method"):
        return is_high_quality_function_docstring(docstring)
    return False

def get_repo_name_from_path(path):
    """Extract repo name from path like: data/downloaded_repos/USERNAME/REPO_NAME"""
    parts = path.split(os.sep)
    try:
        # Find the index where the username starts (after downloaded_repos)
        for i, part in enumerate(parts):
            if part == "downloaded_repos":
                # Return username/repo_name format
                return f"{parts[i+1]}/{parts[i+2]}"
    except IndexError:
        pass
    return None

def extract_docstrings_from_file(file_path):
    """
    Parse a single Python file with AST and extract:
    - file-level docstring
    - class-level docstrings
    - function-level docstrings (including class methods)
    """
    with open(file_path, "r", encoding="utf-8", errors='replace') as f:
        source = f.read()
    
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    
    docstrings_info = []
    repo_name = get_repo_name_from_path(file_path)

    # File-level docstring
    module_docstring = ast.get_docstring(tree)
    if is_high_quality_docstring(module_docstring, "file"):
        signature = f"File: {os.path.basename(file_path)}"
        docstrings_info.append({
            "type": "file",
            "location": file_path,
            "repo_name": repo_name,
            "content": module_docstring.strip(),
            "signature": signature
        })
    
    # Classes and functions
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_docstring = ast.get_docstring(node)
            if hasattr(ast, "unparse"):
                bases = [ast.unparse(base) for base in node.bases]
            else:
                # fallback for older python versions: just get the name of base classes if simple
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    else:
                        # If complex base, just ignore
                        bases.append("Base")

            class_signature = f"class {node.name}"
            if bases:
                class_signature += f"({', '.join(bases)})"
            
            if is_high_quality_docstring(class_docstring, "class"):
                docstrings_info.append({
                    "type": "class",
                    "location": file_path,
                    "repo_name": repo_name,
                    "content": class_docstring.strip(),
                    "signature": class_signature
                })
            
            # Class methods
            for body_item in node.body:
                if isinstance(body_item, ast.FunctionDef):
                    func_docstring = ast.get_docstring(body_item)
                    args_list = [arg.arg for arg in body_item.args.args]
                    func_signature = f"def {body_item.name}({', '.join(args_list)})"
                    if is_high_quality_docstring(func_docstring, "class_method"):
                        docstrings_info.append({
                            "type": "class_method",
                            "location": file_path,
                            "repo_name": repo_name,
                            "content": func_docstring.strip(),
                            "signature": func_signature
                        })
        elif isinstance(node, ast.FunctionDef):
            # Top-level functions
            if isinstance(node.parent, ast.Module):  # We'll add a small hack to set parents
                func_docstring = ast.get_docstring(node)
                args_list = [arg.arg for arg in node.args.args]
                func_signature = f"def {node.name}({', '.join(args_list)})"
                if is_high_quality_docstring(func_docstring, "function"):
                    docstrings_info.append({
                        "type": "function",
                        "location": file_path,
                        "repo_name": repo_name,
                        "content": func_docstring.strip(),
                        "signature": func_signature
                    })

    return docstrings_info

def add_parent_references(tree):
    """Add parent references to nodes, so we can distinguish top-level functions from class methods easily."""
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node

def gather_python_files(top_dir):
    py_files = []
    for root, dirs, files in os.walk(top_dir):
        for file in files:
            if file.endswith(".py"):
                py_files.append(os.path.join(root, file))
    return py_files

def process_all_repos(top_dir, output_file):
    """Process all repositories and extract docstrings.
    
    Args:
        top_dir (str): Path to directory containing downloaded repos
        output_file (str): Path where to save the output JSONL file
    """
    py_files = gather_python_files(top_dir)
    # Setup output file
    # We'll write each docstring object as a single JSON line.
    # This allows incremental updates without invalidating JSON format.
    with open(output_file, "w", encoding="utf-8") as out_f:
        # Using tqdm to show progress over Python files
        for file_path in tqdm(py_files, desc="Processing files"):
            # Parse the file and extract docstrings
            with open(file_path, "r", encoding="utf-8", errors='replace') as f:
                source = f.read()
            try:
                tree = ast.parse(source)
                add_parent_references(tree)
            except SyntaxError:
                # Skip files that have syntax errors
                continue

            docstrings = []
            # File-level docstring
            repo_name = get_repo_name_from_path(file_path)
            module_docstring = ast.get_docstring(tree)
            if is_high_quality_docstring(module_docstring, "file"):
                docstrings.append({
                    "type": "file",
                    "location": file_path,
                    "repo_name": repo_name,
                    "content": module_docstring.strip(),
                    "signature": f"File: {os.path.basename(file_path)}"
                })
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_docstring = ast.get_docstring(node)
                    if hasattr(ast, "unparse"):
                        bases = [ast.unparse(base) for base in node.bases]
                    else:
                        bases = []
                        for base in node.bases:
                            if isinstance(base, ast.Name):
                                bases.append(base.id)
                            else:
                                bases.append("Base")

                    class_signature = f"class {node.name}"
                    if bases:
                        class_signature += f"({', '.join(bases)})"
                    
                    if is_high_quality_docstring(class_docstring, "class"):
                        docstrings.append({
                            "type": "class",
                            "location": file_path,
                            "repo_name": repo_name,
                            "content": class_docstring.strip(),
                            "signature": class_signature
                        })
                    
                    # Class methods
                    for body_item in node.body:
                        if isinstance(body_item, ast.FunctionDef):
                            func_docstring = ast.get_docstring(body_item)
                            args_list = [arg.arg for arg in body_item.args.args]
                            func_signature = f"def {body_item.name}({', '.join(args_list)})"
                            if is_high_quality_docstring(func_docstring, "class_method"):
                                docstrings.append({
                                    "type": "class_method",
                                    "location": file_path,
                                    "repo_name": repo_name,
                                    "content": func_docstring.strip(),
                                    "signature": func_signature
                                })
                elif isinstance(node, ast.FunctionDef):
                    # Check if top-level (parent is module)
                    if isinstance(node.parent, ast.Module):
                        func_docstring = ast.get_docstring(node)
                        args_list = [arg.arg for arg in node.args.args]
                        func_signature = f"def {node.name}({', '.join(args_list)})"
                        if is_high_quality_docstring(func_docstring, "function"):
                            docstrings.append({
                                "type": "function",
                                "location": file_path,
                                "repo_name": repo_name,
                                "content": func_docstring.strip(),
                                "signature": func_signature
                            })
            
            # Write each docstring as a separate JSON line immediately
            for d in docstrings:
                out_f.write(json.dumps(d, ensure_ascii=False) + "\n")
                out_f.flush()

def main():
    parser = argparse.ArgumentParser(description='Process Python files for docstrings')
    parser.add_argument('--input-dir', type=str,  default="data/downloaded_repos",
                      help='Input directory containing downloaded repos')
    parser.add_argument('--output-file', type=str,  default="data/parsed_downloaded_repos/docstrings.jsonl",
                      help='Output JSONL file path')
    args = parser.parse_args()

    process_all_repos(top_dir=args.input_dir, output_file=args.output_file)

if __name__ == "__main__":
    main()
