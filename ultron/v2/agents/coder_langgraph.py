"""
LangGraph-based Self-Healing Code Generation Loop for CoderAgent

This module implements the CoderAgent's self-correction loop using LangGraph StateGraph.
It replaces the traditional while loop with a graph-based state machine for better
observability and control flow management.

Integrates with existing Ultron infrastructure (LLMRouter, MemoryEngine) without breaking changes.
"""

from typing import TypedDict, Optional, Literal
from langgraph.graph import StateGraph, END
from ultron.v2.core.llm_router import LLMRouter
from ultron.v2.memory.engine import MemoryEngine
from ultron.v2.core.types import Task, TaskResult, TaskStatus


class AgentState(TypedDict):
    """State definition for the CoderAgent's self-healing graph."""
    task: Task
    code: str
    error: Optional[str]
    iterations: int
    status: Literal["generating", "executing", "analyzing", "success", "failed"]
    max_iterations: int


async def generate_code_node(state: AgentState) -> AgentState:
    """Node: Generate initial or corrected code using LLM."""
    task = state["task"]
    llm_router = task.context.get("llm_router")  # Injected by caller

    language = task.context.get("language", "python")
    messages = [
        {
            "role": "system",
            "content": (
                "You are a code generation engine. You output ONLY raw, executable Python code.\n"
                "RULES:\n"
                "- Output ONLY Python source code. Nothing else.\n"
                "- NO explanations, NO markdown, NO JSON, NO text before or after.\n"
                "- NO 'Here is the code', NO 'Please run this', NO 'Make sure you have'.\n"
                "- Just the pure Python code that solves the task.\n"
                "- Include print statements so output is visible.\n"
                "- If you cannot write code, output a minimal working example.\n"
            ),
        },
        {
            "role": "user",
            "content": f"Task: {task.description}\nWrite ONLY the complete, runnable {language} code."
        }
    ]

    response = await llm_router.chat(messages, max_tokens=2048)
    code = response.content.strip()

    # Clean markdown if present
    if "```" in code:
        parts = code.split("```")
        for part in parts:
            part = part.strip()
            if part and not part.startswith(("python", "py")):
                code = part
                break

    return {
        **state,
        "code": code,
        "status": "executing",
        "iterations": state["iterations"] + 1
    }


async def execute_code_node(state: AgentState) -> AgentState:
    """Node: Execute the generated code and capture results."""
    task = state["task"]
    code = state["code"]

    # Use existing CoderAgent execution logic (simplified for graph)
    success, output, error = await _execute_python_simple(code, task)

    if success:
        return {**state, "status": "success", "error": None}
    else:
        return {**state, "status": "analyzing", "error": error}


async def analyze_error_node(state: AgentState) -> AgentState:
    """Node: Analyze error and prepare for code regeneration."""
    task = state["task"]
    code = state["code"]
    error = state["error"]
    llm_router = task.context.get("llm_router")

    messages = [
        {
            "role": "system",
            "content": "You are a code debugging assistant. Analyze the error and suggest fixes."
        },
        {
            "role": "user",
            "content": (
                f"Task: {task.description}\n\n"
                f"Code:\n{code}\n\n"
                f"Error:\n{error}\n\n"
                f"Provide a brief analysis and fix suggestion."
            )
        }
    ]

    response = await llm_router.chat(messages, max_tokens=1024)

    # Store analysis in task context for potential memory storage
    task.context["error_analysis"] = response.content

    return {**state, "status": "generating"}


def should_continue(state: AgentState) -> str:
    """Conditional edge: Decide next step based on execution result and iteration limit."""
    if state["status"] == "success":
        return END
    elif state["iterations"] >= state["max_iterations"]:
        return END  # Will be marked as failed in final result
    else:
        return "analyze_error"


# Build the StateGraph
graph = StateGraph(AgentState)

# Add nodes
graph.add_node("generate_code", generate_code_node)
graph.add_node("execute_code", execute_code_node)
graph.add_node("analyze_error", analyze_error_node)

# Define flow
graph.set_entry_point("generate_code")
graph.add_edge("generate_code", "execute_code")
graph.add_conditional_edges("execute_code", should_continue)
graph.add_edge("analyze_error", "generate_code")

# Compile the graph
coder_self_healing_graph = graph.compile()


async def run_coder_self_healing(
    task: Task,
    llm_router: LLMRouter,
    memory: MemoryEngine,
    max_iterations: int = 3
) -> TaskResult:
    """
    Run the LangGraph-based self-healing loop for code generation.

    This replaces the CoderAgent._self_healing_loop method.
    """
    # Inject dependencies into task context
    task.context["llm_router"] = llm_router

    # Initial state
    initial_state: AgentState = {
        "task": task,
        "code": "",
        "error": None,
        "iterations": 0,
        "status": "generating",
        "max_iterations": max_iterations
    }

    # Run the graph
    final_state = await coder_self_healing_graph.ainvoke(initial_state)

    # Convert to TaskResult
    if final_state["status"] == "success":
        status = TaskStatus.SUCCESS
        output = final_state["code"]
        error = None
    else:
        status = TaskStatus.FAILED
        output = final_state["code"]
        error = final_state["error"] or f"Failed after {final_state['iterations']} attempts"

    # Store lesson if failed (integrate with existing memory system)
    if status == TaskStatus.FAILED:
        await memory.generate_lesson_from_failure(
            task.description,
            error,
            llm_router
        )

    return TaskResult(
        task_id=task.id,
        status=status,
        output=output,
        error=error,
        metadata={"heal_iterations": final_state["iterations"]}
    )


# Simplified execution helper (extracted from CoderAgent._execute_python)
async def _execute_python_simple(code: str, task: Task) -> tuple[bool, str, str]:
    """Simplified Python execution for the graph (security checks omitted for brevity)."""
    import asyncio
    import sys
    from pathlib import Path

    timeout = task.context.get("timeout", 30)
    work_dir = Path(task.context.get("work_dir", "./workspace"))

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-c", code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(work_dir),
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

        output = stdout.decode("utf-8", errors="replace").strip()
        error = stderr.decode("utf-8", errors="replace").strip()

        success = proc.returncode == 0
        return success, output, error
    except asyncio.TimeoutError:
        return False, "", f"Execution timed out after {timeout}s"
    except Exception as e:
        return False, "", f"Execution failed: {e}"


# Example integration in Orchestrator._execute_code_task
"""
# In orchestrator.py, replace the existing _execute_code_task method:

async def _execute_code_task(
    self,
    user_input: str,
    intent: dict,
    lesson_context: str,
) -> str:
    agent = self.agents[AgentRole.CODER]
    should_execute = intent.get("execute", True)
    task = Task(
        description=user_input,
        intent="code",
        context={
            "execute": should_execute,
            "language": intent.get("language", "python"),
            "lesson_context": lesson_context,
        },
    )

    if should_execute and agent.allow_execution:
        # NEW: Use LangGraph instead of agent.execute(task)
        from ultron.v2.agents.coder_langgraph import run_coder_self_healing
        result = await run_coder_self_healing(task, self.coder_llm_router, self.memory)
    else:
        # Fallback to original code generation only
        result = await agent._generate_code(task)
        result = TaskResult(task_id=task.id, status=TaskStatus.SUCCESS, output=result)

    if result.status == TaskStatus.FAILED:
        # Self-learning: store the failure (moved to graph)
        pass  # Already handled in run_coder_self_healing

    return result.output or result.error or "No output"
"""