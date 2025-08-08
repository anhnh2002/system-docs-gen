from typing import Dict, List, Any
import os
from config import Config
from .ast_parser import DependencyParser
from .topo_sort import build_graph_from_components, get_leaf_nodes
from utils import file_manager


class DependencyGraphBuilder:
    """Handles dependency analysis and graph building."""
    
    def __init__(self, config: Config):
        self.config = config
    
    def build_dependency_graph(self) -> tuple[Dict[str, Any], List[str]]:
        """
        Build and save dependency graph, returning components and leaf nodes.
        
        Returns:
            Tuple of (components, leaf_nodes)
        """
        # Ensure output directory exists
        file_manager.ensure_directory(self.config.dependency_graph_dir)
        
        # Parse repository
        parser = DependencyParser(self.config.repo_path)
        components = parser.parse_repository()
        
        # Save dependency graph
        repo_name = os.path.basename(os.path.normpath(self.config.repo_path))
        sanitized_repo_name = ''.join(c if c.isalnum() else '_' for c in repo_name)
        dependency_graph_path = os.path.join(
            self.config.dependency_graph_dir, 
            f"{sanitized_repo_name}_dependency_graph.json"
        )
        
        parser.save_dependency_graph(dependency_graph_path)
        
        # Build graph for traversal
        graph = build_graph_from_components(components)
        
        # Get leaf nodes
        leaf_nodes = get_leaf_nodes(graph)
        
        return components, leaf_nodes