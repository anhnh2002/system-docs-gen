# Copyright (c) Meta Platforms, Inc. and affiliates
from typing import List, Dict, Optional, Tuple
import os
import ast
import json
from pathlib import Path
import re

class UsageLocation:
    """Represents a location where a function/class/method is used."""
    def __init__(self, file_path: str, line_number: int, usage_type: str):
        self.file_path = file_path
        self.line_number = line_number
        self.usage_type = usage_type  # 'function', 'class', or 'method'
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'file_path': self.file_path,
            'line_number': self.line_number,
            'usage_type': self.usage_type,
            'repo_path': self.repo_path,
            'signature': self.signature
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UsageLocation':
        """Create from dictionary."""
        return cls(data['file_path'], data['line_number'], data['usage_type'])

class ContextSearcher:
    """
    Searches for usage of functions, classes, and methods in a Python project.
    Caches results to avoid repeated searches.
    """
    
    def __init__(self, repo_path: str):
        """
        Initialize the searcher.
        
        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = Path(repo_path)
        self.cache_dir = os.path.join('data', 'evaluator' , 'search_cache')
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_cache_key(self, file_path: str, signature: str) -> str:
        """Generate a cache key for the search."""
        import hashlib
        # Create a unique key based on file path and signature
        key = f"{file_path}:{signature}"
        return hashlib.md5(key.encode()).hexdigest()
    
    def _load_from_cache(self, cache_key: str) -> Optional[List[UsageLocation]]:
        """Load search results from cache if available."""
        cache_file = self.cache_dir + f"/{cache_key}.json"
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                data = json.load(f)
                return [UsageLocation.from_dict(loc) for loc in data]
        return None
    
    def _save_to_cache(self, cache_key: str, locations: List[UsageLocation]):
        """Save search results to cache."""
        cache_file = self.cache_dir + f"/{cache_key}.json"
        with open(cache_file, 'w') as f:
            json.dump([loc.to_dict() for loc in locations], f, indent=2)
    
    def find_usages(self, target_file: str, signature: str) -> List[UsageLocation]:
        """
        Find all usages of a function/class/method in the repository.
        
        Args:
            target_file: Relative path to the file containing the target
            signature: The signature of the function/class/method
            
        Returns:
            List of UsageLocation objects
        """
        cache_key = self._get_cache_key(target_file, signature)
        
        # Try to load from cache first
        cached_results = self._load_from_cache(cache_key)
        if cached_results is not None:
            return cached_results
        
        # Parse signature to get name and type
        name, usage_type = self._parse_signature(signature)
        
        locations = []
        
        # Walk through all Python files in the repo
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if not file.endswith('.py'):
                    continue
                    
                file_path = Path(root) / file
                rel_path = file_path.relative_to(self.repo_path)
                
                # Skip the target file itself
                if str(rel_path) == target_file:
                    continue
                
                try:
                    with open(file_path) as f:
                        content = f.read()
                    
                    # Find all usages in this file
                    file_locations = self._find_usages_in_file(
                        content, str(rel_path), name, usage_type
                    )
                    
                    # Add repo path and signature to each location
                    for loc in file_locations:
                        loc.repo_path = str(self.repo_path)
                        loc.signature = signature
                        
                    locations.extend(file_locations)
                    
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
        
        # Cache the results
        self._save_to_cache(cache_key, locations)
        
        return locations
    
    def _parse_signature(self, signature: str) -> Tuple[str, str]:
        """Parse a signature to get name and type."""
        signature = signature.strip()
        
        # Split into lines to check for decorators
        is_static = '@staticmethod' in signature
        # remove @staticmethod decorator
        if is_static:
            signature = signature.replace('@staticmethod', '').strip()
        
        if signature.startswith('class '):
            return signature.split()[1].split('(')[0].split(':')[0], 'class'
        elif signature.startswith('def '):
            name = signature.split()[1].split('(')[0]
            if name == '__init__':
                return None, 'method'  # Skip __init__ methods
            if is_static:
                return name, 'staticmethod'
            return name, 'function' if '(self' not in signature else 'method'
        
        raise ValueError(f"Invalid signature: {signature}")
    
    def _find_usages_in_file(self, content: str, file_path: str, name: str, 
                            usage_type: str) -> List[UsageLocation]:
        """Find all usages in a single file."""
        locations = []
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            # For function calls and static methods
            if usage_type in ('function', 'method', 'staticmethod'):
                if usage_type == 'staticmethod':
                    if isinstance(node, ast.Assign):
                        if isinstance(node.value, ast.Call):
                            if isinstance(node.value.func, ast.Attribute) and node.value.func.attr == name:
                                locations.append(UsageLocation(
                                    file_path, node.lineno, usage_type
                                ))
                elif isinstance(node, ast.Call):
                    if usage_type == 'function' and isinstance(node.func, ast.Name):
                        if node.func.id == name:
                            locations.append(UsageLocation(
                                file_path, node.lineno, usage_type
                            ))
                    elif usage_type == 'method' and isinstance(node.func, ast.Attribute):
                        if node.func.attr == name:
                            locations.append(UsageLocation(
                                file_path, node.lineno, usage_type
                            ))
            
            # For class instantiation
            elif usage_type == 'class':
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    if node.func.id == name:
                        locations.append(UsageLocation(
                            file_path, node.lineno, usage_type
                        ))
        
        return locations

class ContextPreparer:
    """
    Prepares context for example evaluation by extracting relevant code
    from usage locations.
    """
    
    def __init__(self, repo_path: str):
        """
        Initialize the preparer.
        
        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = Path(repo_path)
        self.searcher = ContextSearcher(repo_path)
    
    def prepare_contexts(self, target_file: str, signature: str) -> List[Tuple[str, str]]:
        """
        Prepare context for all usages of a function/class/method.
        
        Args:
            target_file: Relative path to the file containing the target
            signature: The signature of the function/class/method
            
        Returns:
            List of tuples (context_code, ground_truth) where:
            - context_code is the code leading up to the usage
            - ground_truth is the actual usage line
        """
        locations = self.searcher.find_usages(target_file, signature)
        contexts = []
        
        for location in locations:
            context, ground_truth = self._prepare_single_context(location)
            if context and ground_truth:
                contexts.append((context, ground_truth))
        
        return contexts
    
    def _prepare_single_context(self, location: UsageLocation) -> Tuple[Optional[str], Optional[str]]:
        """Prepare context for a single usage location."""
        file_path = self.repo_path / location.file_path
        
        with open(file_path) as f:
            lines = f.readlines()
        
        # Get the ground truth lines
        ground_truth_lines = []
        i = location.line_number - 1
        
        # Keep adding lines until we find a line ending with colon after right parenthesis
        while i < len(lines):
            line = lines[i].strip()
            ground_truth_lines.append(line)
            if ')' in line:
                break
            i += 1
            
        ground_truth = '\n'.join(ground_truth_lines)
        
        # Get the context (all lines up to the usage)
        context_lines = lines[:location.line_number - 1]
        
        # Remove trailing empty lines
        while context_lines and not context_lines[-1].strip():
            context_lines.pop()
        
        context = ''.join(context_lines)
        
        return context, ground_truth