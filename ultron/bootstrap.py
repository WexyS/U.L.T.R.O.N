#!/usr/bin/env python3
"""Ultron Genesis Bootstrap — Initialize the unified multi-agent system and start interaction.

Usage:
    python -m ultron.bootstrap          # Interactive mode (CLI)
    python -m ultron.bootstrap --status      # Show system status
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from ultron.core.llm_router import LLMRouter
from ultron.core.agent_registry import registry
from ultron.core.react_orchestrator import ReActOrchestrator
from ultron.core.event_bus import EventBus
from ultron.core.blackboard import Blackboard
import ultron.agents as agents_pkg

load_dotenv()
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("./data/ultron_genesis.log", encoding="utf-8"),
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
║  GENESIS •  Unified Core •  Autonomous Evolution •  Multi-Agent  ║
╚═══════════════════════════════════════════════════════════════════╝
"""


async def bootstrap_interactive(orchestrator: ReActOrchestrator) -> None:
    """Interactive chat loop with the Genesis orchestrator."""
    console.print(Panel.fit(
        "[bold cyan]Ultron Genesis — Unified Multi-Agent AGI[/bold cyan]\n"
        "[dim]Type your request. Prefixes: /status, /quit[/dim]",
        border_style="cyan",
    ))

    while True:
        try:
            user_input = console.input("\n[bold green]You> [/bold green]")
            user_input = user_input.strip()

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q", "/quit"):
                break
            if user_input.lower() == "/status":
                status = orchestrator.get_status()
                console.print_json(data=status)
                continue

            # Process through orchestrator
            from ultron.core.base_agent import AgentTask
            task = AgentTask(input_data=user_input)
            
            with console.status("[bold yellow]Ultron Genesis is thinking...[/bold yellow]", spinner="dots"):
                result = await orchestrator.execute(task)

            console.print()
            if result.success:
                console.print(Panel(Markdown(str(result.output)), title="Ultron Genesis", border_style="blue"))
            else:
                console.print(Panel(f"[red]Error: {result.error}[/red]", title="Ultron Genesis", border_style="red"))

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type /quit to exit.[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            logger.exception("Processing error")


async def main() -> None:
    """Entry point for Ultron Genesis."""
    parser = argparse.ArgumentParser(description="Ultron Genesis Bootstrap")
    parser.add_argument("--status", action="store_true", help="Show system status and exit")
    
    default_model = os.getenv("ULTRON_MODEL") or os.getenv("OLLAMA_MODEL") or "qwen2.5:14b"
    parser.add_argument("--model", default=default_model, help="Ollama model to use")
    args = parser.parse_args()

    console.print(BANNER, style="bold blue")

    # 1. Initialize LLM Router
    console.print("[dim]Initializing LLM Router...[/dim]")
    llm_router = LLMRouter(ollama_model=args.model)
    llm_router.enable_all_providers(dict(os.environ))

    healthy = llm_router.get_healthy_providers()
    if not healthy:
        console.print("[red]No LLM providers available! Is Ollama running?[/red]")
        sys.exit(1)
    console.print(f"[green]LLM Providers Active: {', '.join(healthy)}[/green]")

    # 2. Initialize Genesis Core
    console.print("[dim]Initializing Genesis Core Components...[/dim]")
    event_bus = EventBus()
    blackboard = Blackboard()
    
    registry.set_factory_provider("llm_router", llm_router)
    registry.set_factory_provider("event_bus", event_bus)
    registry.set_factory_provider("blackboard", blackboard)

    # 3. Register Agents
    console.print("[dim]Registering agents...[/dim]")
    registered_count = 0
    for attr_name in agents_pkg.__all__:
        if attr_name in ("Agent", "BaseAgent"): continue
        try:
            agent_cls = getattr(agents_pkg, attr_name)
            desc = getattr(agent_cls, "agent_description", "Specialized Agent")
            registry.register_lazy(attr_name, desc, agent_cls)
            registered_count += 1
        except Exception: pass

    # 4. Initialize Orchestrator
    orchestrator = ReActOrchestrator()
    registry.register(orchestrator)
    
    # 5. Background Daemons
    if os.getenv("ULTRON_EVOLUTION_ENABLED", "0").strip() in ("1", "true", "yes", "on"):
        try:
            from ultron.core.eternal_evolution import EternalEvolutionEngine
            interval = int(os.getenv("ULTRON_EVOLUTION_INTERVAL_MINUTES", "15"))
            evolution_daemon = EternalEvolutionEngine(sleep_interval_minutes=interval)
            asyncio.create_task(evolution_daemon.start_loop())
            console.print(f"[dim]⚡ Eternal Evolution Engine active ({interval}m).[/dim]")
        except Exception as e:
            console.print(f"[yellow]Evolution daemon failed: {e}[/yellow]")

    # System ready
    console.print(f"\n[bold green]Ultron Genesis Initialized! ({registered_count} agents)[/bold green]")
    console.print()

    try:
        if args.status:
            status = orchestrator.get_status()
            console.print_json(data=status)
        else:
            await bootstrap_interactive(orchestrator)
    finally:
        console.print("\n[yellow]Ultron Genesis shutting down. Goodbye.[/yellow]")


if __name__ == "__main__":
    asyncio.run(main())
