from pydantic_ai import Agent
import logfire

logfire.configure()
logfire.instrument_pydantic_ai()

import argparse
import asyncio
import os
import json
from typing import Dict

from agent_tools.deps import DocAgentDeps
from agent_tools.read_code_components import read_code_components_tool
from agent_tools.str_replace_editor import str_replace_editor_tool
from agent_tools.generate_sub_module_documentations import generate_sub_module_documentation_tool
from dependency_analyzer import DependencyParser, build_graph_from_components, get_leaf_nodes
from llm_services import fallback_models, call_llm
from prompt_template import SYSTEM_PROMPT, LEAF_SYSTEM_PROMPT, OVERVIEW_PROMPT, format_user_prompt
from utils import is_complex_module


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

    # Cluster the modules
    # grouped_components = cluster_modules(leaf_nodes, components)
    # print(f"Grouped components:\n{json.dumps(grouped_components, indent=4)}")
    mock_grouped_components = {
        "core_agent": {
            "components": [
                "sweagent.agent.agents.DefaultAgent",
                "sweagent.agent.agents.RetryAgent",
                "sweagent.agent.agents.AbstractAgent",
                "sweagent.agent.models.ReplayModel",
                "sweagent.agent.models.AbstractModel",
                "sweagent.agent.models.LiteLLMModel",
                "sweagent.agent.models.HumanModel",
                "sweagent.agent.models.GlobalStats",
                "sweagent.agent.history_processors.AbstractHistoryProcessor",
                "sweagent.agent.history_processors.ClosedWindowHistoryProcessor",
                "sweagent.agent.history_processors.TagToolCallObservations",
                "sweagent.agent.history_processors.LastNObservations",
                "sweagent.agent.history_processors.CacheControlHistoryProcessor",
                "sweagent.agent.hooks.abstract.CombinedAgentHook",
                "sweagent.agent.problem_statement.problem_statement_from_simplified_input"
            ],
            "children": {}
        },
        "environment_system": {
            "components": [
                "sweagent.environment.swe_env.SWEEnv",
                "sweagent.environment.repo.repo_from_simplified_input",
                "sweagent.environment.hooks.abstract.CombinedEnvHooks"
            ],
            "children": {}
        },
        "tool_system": {
            "components": [
                "sweagent.tools.tools.ToolHandler",
                "sweagent.tools.parsing.XMLFunctionCallingParser",
                "sweagent.tools.parsing.SingleBashCodeBlockParser",
                "sweagent.tools.parsing.XMLThoughtActionParser",
                "sweagent.tools.parsing.BashCodeBlockParser",
                "sweagent.tools.parsing.Identity",
                "sweagent.tools.parsing.EditFormat"
            ],
            "children": {}
        },
        "run_system": {
            "components": [
                "sweagent.run.run.main",
                "sweagent.run.run_batch.RunBatch",
                "sweagent.run.run_batch.run_from_cli",
                "sweagent.run.run_single.RunSingle",
                "sweagent.run.run_single.run_from_cli",
                "sweagent.run.run_replay.RunReplay",
                "sweagent.run.run_replay.run_from_cli",
                "sweagent.run.run_shell.RunShell",
                "sweagent.run.run_shell.run_from_cli",
                "sweagent.run.batch_instances.InstancesFromFile",
                "sweagent.run.batch_instances.InstancesFromHuggingFace",
                "sweagent.run.batch_instances.SWESmithInstances",
                "sweagent.run.common.BasicCLI",
                "sweagent.run.hooks.abstract.CombinedRunHooks",
                "sweagent.run._progress.RunBatchProgressManager"
            ],
            "children": {}
        },
        "inspector_tools": {
            "components": [
                "sweagent.inspector.server.Handler",
                "sweagent.inspector.server.run_from_cli",
                "sweagent.inspector.static.save_all_trajectories",
                "sweagent.run.inspector_cli.TrajectoryInspectorApp",
                "sweagent.run.inspector_cli.TrajectorySelectorScreen",
                "sweagent.run.inspector_cli.TrajectoryViewer",
                "sweagent.run.inspector_cli.main"
            ],
            "children": {}
        },
        "analysis_utilities": {
            "components": [
                "sweagent.run.compare_runs.run_from_cli",
                "sweagent.run.extract_pred.run_from_cli",
                "sweagent.run.merge_predictions.run_from_cli",
                "sweagent.run.quick_stats.run_from_cli",
                "sweagent.run.remove_unfinished.run_from_cli"
            ],
            "children": {}
        }
    }

    # Create output directory for docs as well as working directory for the agent
    output_dir = os.path.join("output", "docs", f"{sanitized_repo_name}-docs")
    # working directory: absolute path to the output directory
    working_dir = os.path.abspath(output_dir)
    os.makedirs(working_dir, exist_ok=True)

    # load module tree from a json file if it exists
    module_tree_path = os.path.join(working_dir, "module_tree.json")

    for module_name in mock_grouped_components.keys():

        # Create agent
        if is_complex_module(components, mock_grouped_components[module_name]["components"]):
            agent = Agent(  
                fallback_models,
                deps_type=DocAgentDeps,
                tools=[read_code_components_tool, str_replace_editor_tool, generate_sub_module_documentation_tool],
                system_prompt=SYSTEM_PROMPT.format(module_name=module_name),
            )
        else:
            agent = Agent(
                fallback_models,
                deps_type=DocAgentDeps,
                tools=[read_code_components_tool, str_replace_editor_tool],
                system_prompt=LEAF_SYSTEM_PROMPT.format(module_name=module_name),
            )

        
        if os.path.exists(module_tree_path):
            with open(module_tree_path, "r") as f:
                module_tree = json.load(f)
        else:
            module_tree = mock_grouped_components

        deps = DocAgentDeps(
            absolute_docs_path=working_dir,
            registry={},
            components=components,
            path_to_current_module=[module_name],
            current_module_name=module_name,
            module_tree=module_tree,
        )
        result = await agent.run(
            format_user_prompt(
                module_name=module_name, 
                core_component_ids=module_tree[module_name]["components"], 
                components=components,
                module_tree=deps.module_tree
            ),
            deps=deps
        )

        # save module tree to a json file
        with open(module_tree_path, "w") as f:
            json.dump(deps.module_tree, f, indent=4)


    # Generate overview
    with open(module_tree_path, "r") as f:
        module_tree = json.load(f)
    for module_name in module_tree.keys():
        # load corresponding module documentation
        module_docs_path = os.path.join(working_dir, f"{module_name}.md")
        with open(module_docs_path, "r") as f:
            module_docs = f.read()
        module_tree[module_name]["docs"] = module_docs
    repo_structure = json.dumps(module_tree, indent=4)

    overview = call_llm(OVERVIEW_PROMPT.format(repo_name=repo_name, repo_structure=repo_structure))
    
    # parse the overview and save it to a markdown file
    overview = overview.split("<OVERVIEW>")[1].split("</OVERVIEW>")[0].strip()
    overview_path = os.path.join(working_dir, "overview.md")
    with open(overview_path, "w") as f:
        f.write(overview)
    print(f"Overview saved to: {overview_path}")

if __name__ == "__main__":
    asyncio.run(main())