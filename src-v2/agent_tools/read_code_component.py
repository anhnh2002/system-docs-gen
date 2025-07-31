from pydantic_ai import RunContext, Tool
from .deps import DocAgentDeps


def read_code_component(ctx: RunContext[DocAgentDeps], component_id: str) -> str:
    """Read the code of a given component id

    Args:
        component_id: The id of the component to read, e.g. sweagent.types.AgentRunResult where sweagent.types part is the path to the component and AgentRunResult is the name of the component
    """
    if component_id not in ctx.deps.components:
        return f"Component {component_id} not found"
    return ctx.deps.components[component_id].source_code

read_code_component_tool = Tool(function=read_code_component, name="read_code_component", description="Read the code of a given component id", takes_ctx=True)