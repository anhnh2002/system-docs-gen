"""
DeepwikiAgent - A tool for generating comprehensive documentation from Python codebases.

This module orchestrates the documentation generation process by:
1. Analyzing code dependencies
2. Clustering related modules
3. Generating documentation using AI agents
4. Creating overview documentation
"""

from pydantic_ai import Agent
import logfire
import logging
import argparse
import asyncio
import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional

# Configure logging and monitoring
logfire.configure()
logfire.instrument_pydantic_ai()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Local imports
from agent_tools.deps import DeepwikiAgentDeps
from agent_tools.read_code_components import read_code_components_tool
from agent_tools.str_replace_editor import str_replace_editor_tool
from agent_tools.generate_sub_module_documentations import generate_sub_module_documentation_tool
from dependency_analyzer import DependencyParser, build_graph_from_components, get_leaf_nodes
from llm_services import fallback_models, call_llm
from prompt_template import SYSTEM_PROMPT, LEAF_SYSTEM_PROMPT, OVERVIEW_PROMPT, format_user_prompt
from utils import is_complex_module
from cluster_modules import cluster_modules


# Constants
DEFAULT_REPO_PATH = 'data/raw_test_repo'
OUTPUT_BASE_DIR = 'output'
DEPENDENCY_GRAPHS_DIR = 'dependency_graphs'
DOCS_DIR = 'docs'
MODULE_TREE_FILENAME = 'module_tree.json'
OVERVIEW_FILENAME = 'overview.md'


@dataclass
class Config:
    """Configuration class for DeepwikiAgent."""
    repo_path: str
    output_dir: str
    dependency_graph_dir: str
    docs_dir: str
    
    @classmethod
    def from_args(cls, args: argparse.Namespace) -> 'Config':
        """Create configuration from parsed arguments."""
        repo_name = os.path.basename(os.path.normpath(args.repo_path))
        sanitized_repo_name = ''.join(c if c.isalnum() else '_' for c in repo_name)
        
        return cls(
            repo_path=args.repo_path,
            output_dir=OUTPUT_BASE_DIR,
            dependency_graph_dir=os.path.join(OUTPUT_BASE_DIR, DEPENDENCY_GRAPHS_DIR),
            docs_dir=os.path.join(OUTPUT_BASE_DIR, DOCS_DIR, f"{sanitized_repo_name}-docs")
        )


class FileManager:
    """Handles file I/O operations."""
    
    @staticmethod
    def ensure_directory(path: str) -> None:
        """Create directory if it doesn't exist."""
        os.makedirs(path, exist_ok=True)
    
    @staticmethod
    def save_json(data: Any, filepath: str) -> None:
        """Save data as JSON to file."""
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
    
    @staticmethod
    def load_json(filepath: str) -> Optional[Dict[str, Any]]:
        """Load JSON from file, return None if file doesn't exist."""
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'r') as f:
            return json.load(f)
    
    @staticmethod
    def save_text(content: str, filepath: str) -> None:
        """Save text content to file."""
        with open(filepath, 'w') as f:
            f.write(content)
    
    @staticmethod
    def load_text(filepath: str) -> str:
        """Load text content from file."""
        with open(filepath, 'r') as f:
            return f.read()


class DependencyGraphBuilder:
    """Handles dependency analysis and graph building."""
    
    def __init__(self, config: Config):
        self.config = config
        self.file_manager = FileManager()
    
    def build_dependency_graph(self) -> tuple[Dict[str, Any], Dict[str, List[str]], List[str]]:
        """
        Build and save dependency graph, returning components, graph, and leaf nodes.
        
        Returns:
            Tuple of (components, dependency_graph, leaf_nodes)
        """
        logger.info(f"Parsing repository: {self.config.repo_path}")
        
        # Ensure output directory exists
        self.file_manager.ensure_directory(self.config.dependency_graph_dir)
        
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
        logger.info(f"Dependency graph saved to: {dependency_graph_path}")
        
        # Build graph for traversal
        graph = build_graph_from_components(components)
        
        # Create dependency graph mapping
        dependency_graph = {component_id: list(deps) for component_id, deps in graph.items()}
        
        # Get leaf nodes
        leaf_nodes = get_leaf_nodes(graph)
        logger.info(f"Found {len(leaf_nodes)} leaf nodes")
        
        return components, dependency_graph, leaf_nodes


class AgentOrchestrator:
    """Orchestrates the AI agents for documentation generation."""
    
    def __init__(self, config: Config, file_manager: FileManager):
        self.config = config
        self.file_manager = file_manager
    
    def create_agent(self, module_name: str, components: Dict[str, Any], 
                    grouped_components: Dict[str, Any]) -> Agent:
        """Create an appropriate agent based on module complexity."""
        if is_complex_module(components, grouped_components[module_name]["components"]):
            return Agent(
                fallback_models,
                deps_type=DeepwikiAgentDeps,
                tools=[
                    read_code_components_tool, 
                    str_replace_editor_tool, 
                    generate_sub_module_documentation_tool
                ],
                system_prompt=SYSTEM_PROMPT.format(module_name=module_name),
            )
        else:
            return Agent(
                fallback_models,
                deps_type=DeepwikiAgentDeps,
                tools=[read_code_components_tool, str_replace_editor_tool],
                system_prompt=LEAF_SYSTEM_PROMPT.format(module_name=module_name),
            )
    
    async def process_module(self, module_name: str, components: Dict[str, Any], 
                           grouped_components: Dict[str, Any], working_dir: str) -> Dict[str, Any]:
        """Process a single module and generate its documentation."""
        logger.info(f"Processing module: {module_name}")
        
        # Load or create module tree
        module_tree_path = os.path.join(working_dir, MODULE_TREE_FILENAME)
        module_tree = self.file_manager.load_json(module_tree_path) or grouped_components
        
        # Create agent
        agent = self.create_agent(module_name, components, grouped_components)
        
        # Create dependencies
        deps = DeepwikiAgentDeps(
            absolute_docs_path=working_dir,
            absolute_repo_path=str(os.path.abspath(self.config.repo_path)),
            registry={},
            components=components,
            path_to_current_module=[module_name],
            current_module_name=module_name,
            module_tree=module_tree,
        )
        
        # Run agent
        try:
            result = await agent.run(
                format_user_prompt(
                    module_name=module_name,
                    core_component_ids=module_tree[module_name]["components"],
                    components=components,
                    module_tree=deps.module_tree
                ),
                deps=deps
            )
            
            # Save updated module tree
            self.file_manager.save_json(deps.module_tree, module_tree_path)
            logger.info(f"Successfully processed module: {module_name}")
            
            return deps.module_tree
            
        except Exception as e:
            logger.error(f"Error processing module {module_name}: {str(e)}")
            raise


class DocumentationGenerator:
    """Main documentation generation orchestrator."""
    
    def __init__(self, config: Config):
        self.config = config
        self.file_manager = FileManager()
        self.graph_builder = DependencyGraphBuilder(config)
        self.agent_orchestrator = AgentOrchestrator(config, self.file_manager)
    
    def prepare_grouped_components(self, grouped_components: Dict[str, Any]) -> None:
        """Prepare grouped components by removing path and adding children."""
        for value in grouped_components.values():
            if 'path' in value:
                del value["path"]
            value["children"] = {}
    
    async def generate_module_documentation(self, components: Dict[str, Any], 
                                          grouped_components: Dict[str, Any]) -> str:
        """Generate documentation for all modules."""
        # Prepare output directory
        working_dir = os.path.abspath(self.config.docs_dir)
        self.file_manager.ensure_directory(working_dir)
        
        # Process each module
        final_module_tree = None
        for module_name in grouped_components.keys():
            try:
                final_module_tree = await self.agent_orchestrator.process_module(
                    module_name, components, grouped_components, working_dir
                )
            except Exception as e:
                logger.error(f"Failed to process module {module_name}: {str(e)}")
                continue
        
        return working_dir
    
    def generate_overview(self, working_dir: str) -> str:
        """Generate overview documentation."""
        module_tree_path = os.path.join(working_dir, MODULE_TREE_FILENAME)
        module_tree = self.file_manager.load_json(module_tree_path)
        
        if not module_tree:
            raise FileNotFoundError(f"Module tree not found at {module_tree_path}")
        
        # Load module documentation
        for module_name in module_tree.keys():
            module_docs_path = os.path.join(working_dir, f"{module_name}.md")
            try:
                module_docs = self.file_manager.load_text(module_docs_path)
                module_tree[module_name]["docs"] = module_docs
            except FileNotFoundError:
                logger.warning(f"Documentation not found for module: {module_name}")
                module_tree[module_name]["docs"] = "Documentation not available"
        
        # Generate overview
        repo_name = os.path.basename(os.path.normpath(self.config.repo_path))
        repo_structure = json.dumps(module_tree, indent=4)
        
        try:
            overview = call_llm(OVERVIEW_PROMPT.format(
                repo_name=repo_name, 
                repo_structure=repo_structure
            ))
            
            # Parse and save overview
            overview_content = overview.split("<OVERVIEW>")[1].split("</OVERVIEW>")[0].strip()
            overview_path = os.path.join(working_dir, OVERVIEW_FILENAME)
            self.file_manager.save_text(overview_content, overview_path)
            
            return overview_path
            
        except Exception as e:
            logger.error(f"Error generating overview: {str(e)}")
            raise
    
    async def run(self) -> None:
        """Run the complete documentation generation process."""
        try:
            # Build dependency graph
            components, dependency_graph, leaf_nodes = self.graph_builder.build_dependency_graph()
            
            # Cluster modules
            grouped_components = cluster_modules(leaf_nodes, components)
            logger.info(f"Grouped components into {len(grouped_components)} modules")
            
            # Prepare components
            self.prepare_grouped_components(grouped_components)
            
            # Generate module documentation
            working_dir = await self.generate_module_documentation(components, grouped_components)
            
            # Generate overview
            overview_path = self.generate_overview(working_dir)
            
            logger.info(f"Documentation generation completed successfully!")
            logger.info(f"Documentation saved to: {working_dir}")
            logger.info(f"Overview saved to: {overview_path}")
            
        except Exception as e:
            logger.error(f"Documentation generation failed: {str(e)}")
            raise


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate comprehensive documentation for Python components in dependency order.'
    )
    parser.add_argument(
        '--repo-path',
        type=str,
        default=DEFAULT_REPO_PATH,
        help=f'Path to the repository (default: {DEFAULT_REPO_PATH})'
    )
    
    return parser.parse_args()


async def main() -> None:
    """Main entry point for the documentation generation process."""
    try:
        # Parse arguments and create configuration
        args = parse_arguments()
        config = Config.from_args(args)
        
        # Create and run documentation generator
        doc_generator = DocumentationGenerator(config)
        await doc_generator.run()
        
    except KeyboardInterrupt:
        logger.info("Documentation generation interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())