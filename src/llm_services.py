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


from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIModelSettings

from pydantic_ai.models.fallback import FallbackModel

main_model = OpenAIModel(
    # model_name="kimi-k2-instruct",
    # model_name="qwen3-coder-480b-a35b-instruct",
    # model_name="glm-4p5",
    model_name="claude-sonnet-4",
    provider=OpenAIProvider(
        base_url="http://0.0.0.0:4000/",
        api_key="sk-1234"
    ),
    settings=OpenAIModelSettings(
        temperature=0.0,
        max_tokens=36000
    )
)

fallback_model_1 = OpenAIModel(
    model_name="glm-4p5",
    provider=OpenAIProvider(
        base_url="http://0.0.0.0:4000/",
        api_key="sk-1234"
    ),
    settings=OpenAIModelSettings(
        temperature=0.0,
        max_tokens=36000
    )
)

fallback_models = FallbackModel(main_model, fallback_model_1)

# ------------------------------------------------------------



from openai import OpenAI

client = OpenAI(
    base_url="http://0.0.0.0:4000/",
    api_key="sk-1234"
)

#kimi-k2-instruct
#qwen3-coder-480b-a35b-instruct
#qwen3-235b-a22b-thinking-2507

def call_llm(prompt: str, model: str = "claude-sonnet-4", temperature: float = 0.0):
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=36000
    )
    return response.choices[0].message.content