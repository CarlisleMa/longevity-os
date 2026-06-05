"""Base agent class with ReAct loop and workspace integration."""

from dataclasses import dataclass, field

import anthropic

from . import config
from .tools import TOOL_DEFINITION, create_namespace, execute_python
from .workspace import Workspace
from .memory import Memory


@dataclass
class AgentResult:
    answer: str
    turns: int
    code_blocks: list[str] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)


class BaseAgent:
    """Base class for all agents. Handles the ReAct loop, tool execution,
    and workspace/memory integration.

    Subclasses override `system_prompt` to specialize behavior.
    """

    name: str = "BaseAgent"
    system_prompt: str = "You are a helpful data analysis agent."
    can_execute_code: bool = True

    def __init__(
        self,
        workspace: Workspace,
        memory: Memory,
        model: str | None = None,
    ):
        self.workspace = workspace
        self.memory = memory
        self.model = model or config.MODEL
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.namespace = create_namespace() if self.can_execute_code else {}
        self.messages: list[dict] = []

    def _build_full_prompt(self, task: str) -> str:
        """Combine system prompt + workspace state + relevant memory."""
        parts = [self.system_prompt]

        ws_summary = self.workspace.summary()
        if ws_summary != "(workspace is empty)":
            parts.append(f"\n\n{ws_summary}")

        mem_context = self.memory.get_relevant(task)
        if mem_context:
            parts.append(f"\n\n{mem_context}")

        return "\n".join(parts)

    def run(self, task: str) -> AgentResult:
        """Execute the agent on a task via the ReAct loop.

        Returns AgentResult with the final answer, turn count, and code blocks.
        """
        self.messages = [{"role": "user", "content": task}]
        code_blocks: list[str] = []
        full_prompt = self._build_full_prompt(task)

        tools = [TOOL_DEFINITION] if self.can_execute_code else []

        for turn in range(config.MAX_TURNS):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE,
                system=full_prompt,
                messages=self.messages,
                tools=tools if tools else anthropic.NOT_GIVEN,
            )

            # Append assistant response to history
            self.messages.append({
                "role": "assistant",
                "content": response.content,
            })

            # Check if the agent is done (no tool calls)
            if response.stop_reason == "end_turn":
                answer = "".join(
                    block.text for block in response.content
                    if block.type == "text"
                )
                return AgentResult(
                    answer=answer,
                    turns=turn + 1,
                    code_blocks=code_blocks,
                    history=self.messages,
                )

            # Process tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    code = block.input.get("code", "")
                    code_blocks.append(code)
                    result = execute_python(code, self.namespace)
                    content = result.output if result.success else f"ERROR:\n{result.error}"
                    if result.output and not result.success:
                        content = f"Output before error:\n{result.output}\n\nERROR:\n{result.error}"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": content,
                    })

            if tool_results:
                self.messages.append({"role": "user", "content": tool_results})

        # Hit max turns
        return AgentResult(
            answer="[Agent reached maximum turns without producing a final answer]",
            turns=config.MAX_TURNS,
            code_blocks=code_blocks,
            history=self.messages,
        )
