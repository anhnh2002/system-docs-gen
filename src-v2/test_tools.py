from pydantic_ai import RunContext
from pydantic_ai.result import Usage
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

import argparse
import asyncio
import os

from agent_tools.deps import DocAgentDeps
from agent_tools.read_code_component import read_code_component_tool
from agent_tools.str_replace_editor import str_replace_editor_tool
from dependency_analyzer import DependencyParser, build_graph_from_components, get_leaf_nodes


async def main():
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
    print(f"Parsing repository: {repo_path}")
    parser = DependencyParser(repo_path)
    components = parser.parse_repository()
    
    # Save the dependency graph for future reference
    parser.save_dependency_graph(dependency_graph_path)
    print(f"Dependency graph saved to: {dependency_graph_path}")
    
    # Build the graph for traversal
    graph = build_graph_from_components(components)
    
    # Create a dependency graph in the format expected by the orchestrator
    # Dictionary mapping component paths to their dependencies
    dependency_graph = {}
    for component_id, deps in graph.items():
        dependency_graph[component_id] = list(deps)

    # Get leaf nodes
    leaf_nodes = get_leaf_nodes(graph)
    print(f"Found {len(leaf_nodes)} leaf nodes")

    model = OpenAIModel(
        # model_name="kimi-k2-instruct",
        # model_name="qwen3-coder-480b-a35b-instruct",
        model_name="claude-sonnet-4",
        provider=OpenAIProvider(
            base_url="http://0.0.0.0:4000/",
            api_key="sk-1234"
        )
    )

    # Create output directory for docs as well as working directory for the agent
    output_dir = os.path.join("output", "docs", f"{sanitized_repo_name}-docs")
    # working directory: absolute path to the output directory
    working_dir = os.path.abspath(output_dir)
    os.makedirs(working_dir, exist_ok=True)

    deps = DocAgentDeps(absolute_docs_path=working_dir, components=components, registry={})

    run_context = RunContext(
        deps=deps,
        model=model,
        usage=Usage(),
    )

    print(str_replace_editor_tool.function(
        ctx = run_context,
        command="view",
        path="."
    ))
    


if __name__ == "__main__":
    asyncio.run(main())