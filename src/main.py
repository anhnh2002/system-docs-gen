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
from dependency_analyzer import DependencyGraphBuilder
from llm_services import fallback_models, call_llm
from prompt_template import SYSTEM_PROMPT, LEAF_SYSTEM_PROMPT, OVERVIEW_PROMPT, format_user_prompt
from utils import is_complex_module
from cluster_modules import cluster_modules
from config import (
    Config,
    MODULE_TREE_FILENAME,
    OVERVIEW_FILENAME
)
from utils import file_manager


class AgentOrchestrator:
    """Orchestrates the AI agents for documentation generation."""
    
    def __init__(self, config: Config):
        self.config = config
    
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
        module_tree = file_manager.load_json(module_tree_path) or grouped_components
        
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
            max_depth=self.config.max_depth,
            current_depth=1
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
            file_manager.save_json(deps.module_tree, module_tree_path)
            logger.info(f"Successfully processed module: {module_name}")
            
            return deps.module_tree
            
        except Exception as e:
            logger.error(f"Error processing module {module_name}: {str(e)}")
            raise


class DocumentationGenerator:
    """Main documentation generation orchestrator."""
    
    def __init__(self, config: Config):
        self.config = config
        self.graph_builder = DependencyGraphBuilder(config)
        self.agent_orchestrator = AgentOrchestrator(config)
    
    async def generate_module_documentation(self, components: Dict[str, Any], 
                                          grouped_components: Dict[str, Any]) -> str:
        """Generate documentation for all modules."""
        # Prepare output directory
        working_dir = os.path.abspath(self.config.docs_dir)
        file_manager.ensure_directory(working_dir)
        
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
        module_tree = file_manager.load_json(module_tree_path)
        
        if not module_tree:
            raise FileNotFoundError(f"Module tree not found at {module_tree_path}")
        
        # Load module documentation
        for module_name in module_tree.keys():
            module_docs_path = os.path.join(working_dir, f"{module_name}.md")
            try:
                module_docs = file_manager.load_text(module_docs_path)
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
            file_manager.save_text(overview_content, overview_path)
            
            return overview_path
            
        except Exception as e:
            logger.error(f"Error generating overview: {str(e)}")
            raise
    
    async def run(self) -> None:
        """Run the complete documentation generation process."""
        try:
            # Build dependency graph
            components, leaf_nodes = self.graph_builder.build_dependency_graph()
            
            # Cluster modules
            working_dir = os.path.abspath(self.config.docs_dir)
            file_manager.ensure_directory(working_dir)
            module_tree_path = os.path.join(working_dir, MODULE_TREE_FILENAME)
            # check if module tree exists
            if os.path.exists(module_tree_path):
                logger.info(f"Module tree found at {module_tree_path}")
                grouped_components = file_manager.load_json(module_tree_path)
            else:
                logger.info(f"Module tree not found at {module_tree_path}, clustering modules")
                grouped_components = cluster_modules(leaf_nodes, components)
                file_manager.save_json(grouped_components, module_tree_path)
            logger.info(f"Grouped components into {len(grouped_components)} modules")

            return
            
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
        required=True,
        help='Path to the repository'
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