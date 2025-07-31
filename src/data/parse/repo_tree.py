#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates
import os
import argparse
from pathlib import Path
import json
from typing import Dict, List, Optional

class ProjectStructureGenerator:
    def __init__(self, ignore_patterns: List[str] = None):
        self.ignore_patterns = ignore_patterns or [
            '.git', '__pycache__', '.pytest_cache',
            '.env', 'venv', 'node_modules', '.DS_Store',
            '*.pyc', '*.pyo', '*.pyd', '.Python', '*.so'
        ]
    
    def should_ignore(self, path: str) -> bool:
        """Check if the path should be ignored based on patterns."""
        path_obj = Path(path)
        return any(
            path_obj.match(pattern) or
            any(parent.match(pattern) for parent in path_obj.parents)
            for pattern in self.ignore_patterns
        )
    
    def generate_structure(self, root_path: str, max_depth: Optional[int] = None) -> Dict:
        """Generate a hierarchical structure of the project."""
        root_path = os.path.abspath(root_path)
        root_name = os.path.basename(root_path)
        
        def explore_directory(current_path: str, current_depth: int = 0) -> Dict:
            if max_depth is not None and current_depth > max_depth:
                return {"type": "directory", "name": os.path.basename(current_path), "truncated": True}
            
            structure = {
                "type": "directory",
                "name": os.path.basename(current_path),
                "contents": []
            }
            
            try:
                for item in sorted(os.listdir(current_path)):
                    item_path = os.path.join(current_path, item)
                    
                    if self.should_ignore(item_path):
                        continue
                    
                    if os.path.isfile(item_path):
                        file_info = {
                            "type": "file",
                            "name": item,
                            "extension": os.path.splitext(item)[1][1:] or "none"
                        }
                        structure["contents"].append(file_info)
                    elif os.path.isdir(item_path):
                        subdir = explore_directory(item_path, current_depth + 1)
                        if subdir.get("contents") or not subdir.get("truncated"):
                            structure["contents"].append(subdir)
            
            except PermissionError:
                structure["error"] = "Permission denied"
            
            return structure
        
        return explore_directory(root_path)
    
    def format_structure(self, structure: Dict, indent: int = 0) -> str:
        """Format the structure in a hierarchical text format."""
        output = []
        prefix = "│   " * (indent - 1) + "├── " if indent > 0 else ""
        
        if structure.get("truncated"):
            output.append(f"{prefix}{structure['name']} [...]")
            return "\n".join(output)
        
        output.append(f"{prefix}{structure['name']}/")
        
        if "contents" in structure:
            for i, item in enumerate(structure["contents"]):
                is_last = i == len(structure["contents"]) - 1
                if item["type"] == "file":
                    item_prefix = "│   " * indent + ("└── " if is_last else "├── ")
                    output.append(f"{item_prefix}{item['name']}")
                else:
                    output.append(self.format_structure(item, indent + 1))
        
        return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(
        description="Generate a project structure in LLM-friendly format"
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the project directory (default: current directory)"
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        help="Maximum depth to traverse (default: no limit)"
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--ignore",
        nargs="+",
        help="Additional patterns to ignore"
    )
    
    args = parser.parse_args()
    
    generator = ProjectStructureGenerator()
    if args.ignore:
        generator.ignore_patterns.extend(args.ignore)
    
    structure = generator.generate_structure(args.path, args.max_depth)
    
    if args.output == "json":
        print(json.dumps(structure, indent=2))
    else:
        print(generator.format_structure(structure))

if __name__ == "__main__":
    main()