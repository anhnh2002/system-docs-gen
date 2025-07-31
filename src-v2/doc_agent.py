from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModelSettings

from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.models.anthropic import AnthropicModelSettings

from anthropic.types import (
    MessageParam,
    TextBlockParam
)
from anthropic.types.beta import BetaToolParam
from pydantic_ai.models import ModelRequestParameters
from pydantic_ai.messages import ModelMessage, ModelRequest, SystemPromptPart
from pydantic_ai.models.anthropic import AnthropicModel


class AnthropicModelWithCache(AnthropicModel):
    async def _map_message(  # type: ignore
        self, messages: list[ModelMessage]
    ) -> tuple[list[TextBlockParam], list[MessageParam]]:
        _, anthropic_messages = await super()._map_message(messages)
        system_prompt: list[TextBlockParam] = []
        is_cached = False
        for message in reversed(messages):
            if isinstance(message, ModelRequest):
                for part in reversed(message.parts):
                    if isinstance(part, SystemPromptPart):
                        if not part.dynamic_ref and not is_cached:
                            block = TextBlockParam(
                                type="text",
                                text=part.content,
                                cache_control={"type": "ephemeral"},
                            )
                            is_cached = True
                        else:
                            block = TextBlockParam(
                                type="text",
                                text=part.content,
                            )

                        system_prompt.append(block)

        system_prompt.reverse()
        return system_prompt, anthropic_messages
    
    def _get_tools(
        self, model_request_parameters: ModelRequestParameters
    ) -> list[BetaToolParam]:
        tools = super()._get_tools(model_request_parameters)
        if tools:
            tools[-1]["cache_control"] = {"type": "ephemeral"}
        return tools


import logfire

logfire.configure()
logfire.instrument_pydantic_ai()

import argparse
import asyncio
import os
import json
from typing import Dict

from agent_tools.deps import DocAgentDeps
from agent_tools.read_code_component import read_code_component_tool
from agent_tools.str_replace_editor import str_replace_editor_tool
from dependency_analyzer import DependencyParser, build_graph_from_components, get_leaf_nodes
from cluster_modules import cluster_modules
from dependency_analyzer import CodeComponent


# model = OpenAIModel(
#     model_name="kimi-k2-instruct",
#     # model_name="qwen3-coder-480b-a35b-instruct",
#     # model_name="claude-sonnet-4",
#     provider=OpenAIProvider(
#         base_url="http://0.0.0.0:4000/",
#         api_key="sk-1234"
#     ),
#     settings=OpenAIModelSettings(
#         temperature=0.0
#     )
# )

from anthropic import AsyncAnthropic

anthropic_client = AsyncAnthropic(
    base_url="http://0.0.0.0:4000/",
    api_key="sk-1234"
)


model = AnthropicModelWithCache(
    model_name="claude-sonnet-4",
    provider=AnthropicProvider(
        anthropic_client=anthropic_client
    ),
    settings=AnthropicModelSettings(
        temperature=0.0
    )
)

SYSTEM_PROMPT = """
<ROLE>
You are an AI documentation assistant and your task is generate SYSTEM documentation based on given module name and its core code components.
</ROLE>

<REQUIREMENTS>
The purpose of the documentation is to help the developers and maintainers understand the module and its core functionality.
The documentation should:
- Start with `{module_name}.md` file containing a brief introduction, architecture overview, and high-level functionality. {module_name}.md will be the main documentation file referencing other files via [alt_text](path_to_complemetary_file).
- Include a detailed description markdown file of each core component, its purpose, and how it fits into the overall system.
- Provide a clear explanation of the module's dependencies and how they interact.
- Include a variety of diagrams in MERMAID format to help visualize the module's architecture, dependencies, interactions, flow, etc.
- Save results in the working directory in markdown format.
- Finally, you can revise {module_name}.md to make sure it references all the files correctly.
</REQUIREMENTS>

<ACCESSIBILITY>
- You have access to a working directory through `str_replace_editor` tool where you can interact with the file system in order to generate the documentation.
- While generating the documentation, you can use `read_code_component` tool to explore the code of the module and its dependencies which is not included in the core component codes.
</ACCESSIBILITY>
""".strip()

USER_PROMPT = """
Please explore the code of the following module and its dependencies to generate the documentation.

<MODULE_NAME>
{module_name}
</MODULE_NAME>

<CORE_COMPONENT_CODES>
{formated_core_component_codes}
</CORE_COMPONENT_CODES>
""".strip()

def format_user_prompt(module_name: str, core_component_ids: list[str], components: Dict[str, CodeComponent]) -> str:

    # group core_component_ids by their path
    grouped_components: dict[str, list[CodeComponent]] = {}
    for component_id in core_component_ids:
        component = components[component_id]
        path = component.relative_path
        if path not in grouped_components:
            grouped_components[path] = []
        grouped_components[path].append(component_id)

    core_component_codes = ""
    for path, component_ids in grouped_components.items():
        core_component_codes += f"# {path}\n## Core Component IDs\n"

        for component_id in component_ids:
            core_component_codes += f"### {component_id}\n"
        
        # read content of the file
        with open(components[component_ids[0]].file_path, "r") as f:
            core_component_codes += f.read()
        
    return USER_PROMPT.format(module_name=module_name, formated_core_component_codes=core_component_codes)

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
            "path": "sweagent/agent",
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
            ]
        },
        "environment_system": {
            "path": "sweagent/environment",
            "components": [
                "sweagent.environment.swe_env.SWEEnv",
                "sweagent.environment.repo.repo_from_simplified_input",
                "sweagent.environment.hooks.abstract.CombinedEnvHooks"
            ]
        },
        "tool_system": {
            "path": "sweagent/tools",
            "components": [
                "sweagent.tools.tools.ToolHandler",
                "sweagent.tools.parsing.XMLFunctionCallingParser",
                "sweagent.tools.parsing.SingleBashCodeBlockParser",
                "sweagent.tools.parsing.XMLThoughtActionParser",
                "sweagent.tools.parsing.BashCodeBlockParser",
                "sweagent.tools.parsing.Identity",
                "sweagent.tools.parsing.EditFormat"
            ]
        },
        "run_system": {
            "path": "sweagent/run",
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
            ]
        },
        "inspector_tools": {
            "path": "sweagent/inspector",
            "components": [
                "sweagent.inspector.server.Handler",
                "sweagent.inspector.server.run_from_cli",
                "sweagent.inspector.static.save_all_trajectories",
                "sweagent.run.inspector_cli.TrajectoryInspectorApp",
                "sweagent.run.inspector_cli.TrajectorySelectorScreen",
                "sweagent.run.inspector_cli.TrajectoryViewer",
                "sweagent.run.inspector_cli.main"
            ]
        },
        "analysis_utilities": {
            "path": "sweagent/run",
            "components": [
                "sweagent.run.compare_runs.run_from_cli",
                "sweagent.run.extract_pred.run_from_cli",
                "sweagent.run.merge_predictions.run_from_cli",
                "sweagent.run.quick_stats.run_from_cli",
                "sweagent.run.remove_unfinished.run_from_cli"
            ]
        }
    }

    # Create agent
    agent = Agent(  
        model,
        deps_type=DocAgentDeps,
        tools=[read_code_component_tool, str_replace_editor_tool],
        system_prompt=SYSTEM_PROMPT.format(module_name="core_agent"),
    )

    # Create output directory for docs as well as working directory for the agent
    output_dir = os.path.join("output", "docs", f"{sanitized_repo_name}-docs")
    # working directory: absolute path to the output directory
    working_dir = os.path.abspath(output_dir)
    os.makedirs(working_dir, exist_ok=True)

    deps = DocAgentDeps(absolute_docs_path=working_dir, components=components, registry={})
    result = await agent.run(
        format_user_prompt(module_name="core_agent", core_component_ids=mock_grouped_components["core_agent"]["components"], components=components),
        deps=deps
    )
    print(result.all_messages)
    # async with agent.run_stream(
    #     format_user_prompt(module_name="core_agent", core_component_ids=mock_grouped_components["core_agent"]["components"], components=components),
    #     deps=deps
    # ) as result:
    #     async for message in result.stream():  
    #         # print(message)
    #         pass


if __name__ == "__main__":
    asyncio.run(main())