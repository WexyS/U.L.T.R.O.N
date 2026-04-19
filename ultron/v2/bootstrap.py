#!/usr/bin/env python3
"""Ultron v2.0 Bootstrap — Initialize the full multi-agent system and start interaction.

Usage:
    python -m ultron.v2.bootstrap          # Interactive mode
    python -m ultron.v2.bootstrap --test-rpa    # Test RPA (screenshot + OCR)
    python -m ultron.v2.bootstrap --test-coder  # Test self-healing code generation
    python -m ultron.v2.bootstrap --status      # Show system status
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from ultron.v2.core.llm_router import LLMRouter
from ultron.v2.memory.engine import MemoryEngine
from ultron.v2.core.orchestrator import Orchestrator

console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("./data/ultron_v2.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("ultron.bootstrap")


BANNER = """
╔═══════════════════════════════════════════════════════════════════╗
║  ██████╗ █████╗ ██╗    ██████╗ ██╗   ██╗██████╗ ███████╗██████╗  ║
║  ██╔════╝██╔══██╗██║    ██╔══██╗██║   ██║██╔══██╗██╔════╝██╔══██╗║
║  ██████╗ ███████║██║    ██████╔╝██║   ██║██████╔╝█████╗  ██████╔╝║
║  ██╔══██╗██╔══██║██║    ██╔═══╝ ██║   ██║██╔══██╗██╔══╝  ██╔══██╗║
║  ██████╔╝██║  ██║██║    ██║     ╚██████╔╝██║  ██║███████╗██║  ██║║
║  ╚═════╝ ╚═╝  ╚═╝╚═╝    ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝║
║  v2.0  •  Multi-Agent  •  Self-Healing  •  RPA  •  Continuous Learning ║
╚═══════════════════════════════════════════════════════════════════╝
"""


async def bootstrap_interactive(orchestrator: Orchestrator) -> None:
    """Interactive chat loop with the orchestrator."""
    console.print(Panel.fit(
        "[bold cyan]Ultron v2.0 — Autonomous Multi-Agent AI[/bold cyan]\n"
        "[dim]Type your request. Prefixes: /code, /research, /rpa, /status, /quit[/dim]",
        border_style="cyan",
    ))

    while True:
        try:
            user_input = console.input("\n[bold green]You> [/bold green]")
            user_input = user_input.strip()

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                break
            if user_input.lower() == "/status":
                status = orchestrator.get_status()
                console.print_json(data=status)
                continue
            if user_input.lower() == "/quit":
                break

            # Handle prefixes — pass context to orchestrator
            ctx = None
            if user_input.startswith("/code "):
                ctx = {"intent": {"type": "code", "execute": True, "subtasks": [user_input[6:]]}}
                user_input = user_input[6:]  # Strip prefix, send clean task
            elif user_input.startswith("/research "):
                ctx = {"intent": {"type": "research", "subtasks": [user_input[10:]]}}
                user_input = user_input[10:]
            elif user_input.startswith("/rpa "):
                ctx = {"intent": {"type": "rpa", "subtasks": [user_input[5:]]}}
                user_input = user_input[5:]

            # Process through orchestrator
            with console.status("[bold yellow]Ultron processing...[/bold yellow]", spinner="dots"):
                response = await orchestrator.process(user_input, context=ctx)

            console.print()
            console.print(Panel(Markdown(response), title="Ultron", border_style="blue"))

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type /quit to exit.[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            logger.exception("Processing error")


async def test_rpa(orchestrator: Orchestrator) -> None:
    """Test RPA: take screenshot and read screen content."""
    console.print("[bold cyan]Testing RPA Module...[/bold cyan]")

    from ultron.v2.core.types import Task
    from ultron.v2.core.types import AgentRole

    agent = orchestrator.agents.get(AgentRole.RPA_OPERATOR)
    if not agent:
        console.print("[red]RPA Agent not found![/red]")
        return

    # Test 1: Screenshot
    console.print("\n[1] Taking screenshot...")
    task = Task(description="Take a screenshot", context={"action": "screenshot"})
    result = await agent.execute(task)
    console.print(f"   Result: {result.output}")
    console.print(f"   Status: {'[green]OK[/green]' if result.status.value == 'success' else '[red]FAIL[/red]'}")

    # Test 2: Mouse move
    console.print("\n[2] Testing mouse move (center of screen)...")
    task = Task(description="Move mouse", context={
        "action": "mouse_move",
        "x": 960,
        "y": 540,
    })
    result = await agent.execute(task)
    console.print(f"   Result: {result.output}")
    console.print(f"   Status: {'[green]OK[/green]' if result.status.value == 'success' else '[red]FAIL[/red]'}")

    # Test 3: Type text
    console.print("\n[3] Testing keyboard input...")
    console.print("   [dim]Opening Notepad in 2 seconds...[/dim]")
    await asyncio.sleep(2)

    import subprocess
    subprocess.Popen(["notepad.exe"], shell=True)
    await asyncio.sleep(2)

    task = Task(description="Type text", context={
        "action": "type_text",
        "text": "Hello from Ultron v2.0! RPA test successful.",
    })
    result = await agent.execute(task)
    console.print(f"   Result: {result.output}")
    console.print(f"   Status: {'[green]OK[/green]' if result.status.value == 'success' else '[red]FAIL[/red]'}")

    console.print("\n[bold green]RPA Test Complete![/bold green]")


async def test_coder(orchestrator: Orchestrator) -> None:
    """Test self-healing code generation."""
    console.print("[bold cyan]Testing Self-Healing Code Generator...[/bold cyan]")

    from ultron.v2.core.types import Task
    from ultron.v2.core.types import AgentRole

    agent = orchestrator.agents.get(AgentRole.CODER)
    if not agent:
        console.print("[red]Coder Agent not found![/red]")
        return

    # Test: Generate and execute simple Python code
    console.print("\n[1] Generating + executing code: 'Print the first 10 Fibonacci numbers'")
    task = Task(
        description="Print the first 10 Fibonacci numbers",
        context={
            "execute": True,
            "language": "python",
        },
    )
    result = await agent.execute(task)

    console.print(f"\n   Output:\n{result.output}")
    console.print(f"   Status: {'[green]OK[/green]' if result.status.value == 'success' else '[red]FAIL[/red]'}")
    if result.metadata.get("heal_iterations", 0) > 1:
        console.print(f"   Self-heal iterations: {result.metadata['heal_iterations']}")

    # Test 2: Code that will fail and need fixing
    console.print("\n[2] Testing self-healing: 'Calculate 10/0 and print result'")
    task = Task(
        description="Calculate 10/0 and print the result",
        context={
            "execute": True,
            "language": "python",
        },
    )
    result = await agent.execute(task)
    console.print(f"\n   Output: {result.output[:300] if result.output else ''}")
    console.print(f"   Error: {result.error[:200] if result.error else 'None'}")
    console.print(f"   Status: {'[green]OK[/green]' if result.status.value == 'success' else '[yellow]Expected failure[/yellow]'}")
    if result.metadata.get("heal_iterations"):
        console.print(f"   Self-heal iterations: {result.metadata['heal_iterations']}")

    console.print("\n[bold green]Coder Test Complete![/bold green]")


async def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description="Ultron v2.0 Bootstrap")
    parser.add_argument("--test-rpa", action="store_true", help="Test RPA module")
    parser.add_argument("--test-coder", action="store_true", help="Test self-healing code generator")
    parser.add_argument("--status", action="store_true", help="Show system status and exit")
    parser.add_argument("--model", default="qwen2.5:14b", help="Ollama model to use")
    parser.add_argument("--work-dir", default="./workspace", help="Working directory for code execution")
    args = parser.parse_args()

    console.print(BANNER, style="bold blue")

    # Initialize LLM Router
    console.print("[dim]Initializing LLM Router...[/dim]")
    llm_router = LLMRouter(
        ollama_model=args.model,
    )

    # Load OpenRouter API key from .env
    import os
    from dotenv import load_dotenv
    load_dotenv()
    or_key = os.environ.get("OPENROUTER_API_KEY", "")
    if or_key:
        llm_router.enable_openrouter(or_key, model="anthropic/claude-sonnet-4")
        console.print("[green]OpenRouter enabled (Claude Sonnet 4)[/green]")

    # Enable ALL providers from environment variables
    llm_router.enable_all_providers(dict(os.environ))

    # Check availability
    healthy = llm_router.get_healthy_providers()
    if not healthy:
        console.print("[red]No LLM providers available! Is Ollama running?[/red]")
        console.print("[dim]Run: ollama pull qwen2.5:14b[/dim]")
        sys.exit(1)
    console.print(f"[green]LLM Providers: {', '.join(healthy)}[/green]")

    # Initialize Memory Engine
    console.print("[dim]Initializing Memory Engine...[/dim]")
    memory = MemoryEngine(persist_dir="./data/memory_v2")

    # Start external background routines (Voicebox, etc.)
    console.print("[dim]Checking & auto-launching external tools (Voicebox)...[/dim]")
    try:
        from ultron.v2.core.auto_launchers import start_all_auto_launchers
        await start_all_auto_launchers()
    except Exception as e:
        console.print(f"[yellow]Auto-launcher failed quietly: {e}[/yellow]")

    # Initialize Orchestrator
    console.print("[dim]Initializing Orchestrator...[/dim]")
    orchestrator = Orchestrator(
        llm_router=llm_router,
        memory=memory,
        work_dir=args.work_dir,
    )

    # ⚡ Start Eternal Autonomous Evolution Daemon
    try:
        from ultron.v2.core.eternal_evolution import EternalEvolutionEngine
        evolution_daemon = EternalEvolutionEngine(orchestrator, sleep_interval_minutes=60)
        asyncio.create_task(evolution_daemon.start_loop())
        console.print("[dim]⚡ Eternal Autonomous Evolution Engine started in background...[/dim]")
    except Exception as e:
        console.print(f"[yellow]Eternal daemon failed to start: {e}[/yellow]")

    # System ready
    console.print("\n[bold green]System Initialized Successfully![/bold green]")
    console.print(f"Memory: {memory.stats()}")
    console.print()

    # Start
    await orchestrator.start()

    console.print("[bold green]Ultron v2.0 Ready![/bold green]")
    console.print(f"Memory: {memory.stats()}")
    console.print()

    try:
        if args.test_rpa:
            await test_rpa(orchestrator)
        elif args.test_coder:
            await test_coder(orchestrator)
        elif args.status:
            status = orchestrator.get_status()
            console.print_json(data=status)
        else:
            await bootstrap_interactive(orchestrator)
    finally:
        await orchestrator.stop()
        console.print("\n[yellow]Ultron stopped. Goodbye.[/yellow]")


if __name__ == "__main__":
    asyncio.run(main())
