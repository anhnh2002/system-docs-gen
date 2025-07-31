import os
import sys
import time
import ast
import json
import argparse
import logging
import random
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from collections import defaultdict
import tiktoken  # Add this import for token counting

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("generate_comprehensive_docs")

# Import dependency analyzer modules
from dependency_analyzer import (
    CodeComponent, 
    DependencyParser, 
    dependency_first_dfs, 
    build_graph_from_components,
    get_leaf_nodes
)
from prune_tree import prune_tree
from cluster_modules import cluster_modules


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Generate docstrings for Python components in dependency order.'
    )
    parser.add_argument(
        '--repo-path', 
        type=str, 
        default='data/raw_test_repo',
        help='Path to the repository (default: data/raw_test_repo)'
    )

    args = parser.parse_args()
    repo_path = args.repo_path
    
    # Create output directory for dependency graph
    output_dir = os.path.join("output", "dependency_graphs")
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract repository name from path for creating a unique filename
    repo_name = os.path.basename(os.path.normpath(repo_path))
    # Create a sanitized version of the repo name (remove special characters)
    sanitized_repo_name = ''.join(c if c.isalnum() else '_' for c in repo_name)
    dependency_graph_path = os.path.join(output_dir, f"{sanitized_repo_name}_dependency_graph.json")
    
    # Parse the repository to build the dependency graph
    logger.info(f"Parsing repository: {repo_path}")
    parser = DependencyParser(repo_path)
    components = parser.parse_repository()
    
    # Save the dependency graph for future reference
    parser.save_dependency_graph(dependency_graph_path)
    logger.info(f"Dependency graph saved to: {dependency_graph_path}")
    
    # Build the graph for traversal
    graph = build_graph_from_components(components)
    
    # Create a dependency graph in the format expected by the orchestrator
    # Dictionary mapping component paths to their dependencies
    dependency_graph = {}
    for component_id, deps in graph.items():
        dependency_graph[component_id] = list(deps)

    # Get leaf nodes
    leaf_nodes = get_leaf_nodes(graph)
    logger.info(f"Found {len(leaf_nodes)} leaf nodes:\n{'\n'.join(sorted(leaf_nodes))}")

    # Prune the tree
    # pruned_file_path = os.path.join(output_dir, f"{sanitized_repo_name}_pruned_tree.json")
    # prune_tree(["sweagent.agent.agents.DefaultAgent"], components, pruned_file_path)

    # Cluster the modules
    grouped_components = cluster_modules(leaf_nodes, components)
    logger.info(f"Grouped components:\n{json.dumps(grouped_components, indent=4)}")

    



if __name__ == "__main__":
    main() 