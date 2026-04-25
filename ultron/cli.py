"""CLI Entry Point — Starts Ultron Genesis (GUI default, --cli for terminal)."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.text import Text
from rich.markdown import Markdown
from rich.panel import Panel

from ultron.config import UltronConfig, load_config, ensure_directories

console = Console()

BANNER = Text.assemble(
    ("╔" + "═" * 69 + "╗\n", "bold cyan"),
    ("║  ██████╗ █████╗ ██╗    ██████╗ ██╗   ██╗██████╗ ███████╗██████╗  ║\n", "bold blue"),
    ("║  ██╔════╝██╔══██╗██║    ██╔══██╗██║   ██║██╔══██╗██╔════╝██╔══██╗║\n", "bold blue"),
    ("║  ██████╗ ███████║██║    ██████╔╝██║   ██║██████╔╝█████╗  ██████╔╝║\n", "bold blue"),
    ("║  ██╔══██╗██╔══██║██║    ██╔═══╝ ██║   ██║██╔══██╗██╔══╝  ██╔══██╗║\n", "bold blue"),
    ("║  ██████╔╝██║  ██║██║    ██║     ╚██████╔╝██║  ██║███████╗██║  ██║║\n", "bold blue"),
    ("║  ╚═════╝ ╚═╝  ╚═╝╚═╝    ╚═╝      ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝║\n", "bold blue"),
    ("║  GENESIS • Unified Core • Autonomous Evolution • Multi-Agent AGI   ║\n", "bold green"),
    ("╚" + "═" * 69 + "╝\n", "bold cyan"),
)


async def _init_genesis_core(config: UltronConfig):
    """Initialize Genesis core components and ReActOrchestrator."""
    from dotenv import load_dotenv
    load_dotenv()
    from ultron.core.llm_router import LLMRouter
    from ultron.memory.engine import MemoryEngine
    from ultron.core.react_orchestrator import ReActOrchestrator
    from ultron.core.agent_registry import registry
    from ultron.core.event_bus import EventBus
    from ultron.core.blackboard import Blackboard
    import ultron.agents as agents_pkg

    console.print("[dim]LLM Router başlatılıyor...[/dim]")
    llm = LLMRouter(ollama_model=config.model.ollama_model or "qwen2.5:14b")
    llm.enable_all_providers(dict(os.environ))

    console.print("[dim]Genesis Core başlatılıyor...[/dim]")
    event_bus = EventBus()
    blackboard = Blackboard()
    memory = MemoryEngine(persist_dir=config.memory.persist_dir or "./data/ultron_memory")

    registry.set_factory_provider("llm_router", llm)
    registry.set_factory_provider("event_bus", event_bus)
    registry.set_factory_provider("blackboard", blackboard)

    # Register Agents
    registered_count = 0
    for attr_name in agents_pkg.__all__:
        if attr_name in ("Agent", "BaseAgent"): continue
        try:
            agent_cls = getattr(agents_pkg, attr_name)
            desc = getattr(agent_cls, "agent_description", "Specialized Agent")
            registry.register_lazy(attr_name, desc, agent_cls)
            registered_count += 1
        except Exception: pass

    console.print(f"[dim]{registered_count} ajan Genesis çekirdeğine bağlandı.[/dim]")

    orch = ReActOrchestrator()
    registry.register(orch)
    return orch


def run_gui(config: UltronConfig) -> None:
    """Start the GUI with Genesis orchestrator."""
    ensure_directories(config)

    orchestrator = None
    try:
        # Note: GUI initialization might need async wrapper if orchestrator becomes fully async
        orchestrator = asyncio.run(_init_genesis_core(config))
    except Exception as e:
        console.print(f"[red]✗[/] Genesis Init Hatası: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    try:
        from ultron.gui_app import UltronGUI
        app = UltronGUI(pipeline=None, orchestrator=orchestrator, config=config)
        app.run()
    except Exception as e:
        console.print(f"[red]GUI başlatılamadı: {e}[/]")
        sys.exit(1)


async def async_main(config: UltronConfig) -> None:
    """Terminal mode with Genesis orchestrator."""
    console.print(BANNER)

    orchestrator = await _init_genesis_core(config)
    console.print("[green]✓[/] Ultron Genesis Terminali hazır. (/quit ile çıkış)\n")

    from ultron.core.base_agent import AgentTask

    while True:
        try:
            user_input = console.input("[bold green]You> [/bold green]").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q", "/quit"):
                break

            task = AgentTask(input_data=user_input)
            with console.status("[dim]Ultron Genesis düşünüyor...[/dim]", spinner="dots"):
                result = await orchestrator.execute(task)

            console.print("\n[bold cyan]Ultron Genesis:[/bold cyan]")
            if result.success:
                console.print(Markdown(str(result.output)))
            else:
                console.print(f"[red]Hata: {result.error}[/red]")
            console.print()

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Hata: {e}[/red]")

    console.print("\n[yellow]Ultron Genesis durduruldu. Güle güle.[/yellow]")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Ultron Genesis — Unified AGI System")
    parser.add_argument("--config", "-c", help="Yapılandırma dosyası")
    parser.add_argument("--cli", action="store_true", help="Terminal modu")
    args = parser.parse_args()

    config = load_config(args.config)
    ensure_directories(config)

    # Path normalization for Genesis
    project_root = Path(__file__).parent.parent
    if not os.path.isabs(config.memory.persist_dir):
        config.memory.persist_dir = str(project_root / config.memory.persist_dir)

    logging.basicConfig(
        level=getattr(logging, config.logging.level),
        filename=os.path.join("./data", "ultron_genesis.log"),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.cli:
        try:
            asyncio.run(async_main(config))
        except KeyboardInterrupt:
            console.print("\n[yellow]İptal.[/]")
        except Exception as e:
            console.print(f"\n[red]Kritik Hata: {e}[/]")
    else:
        run_gui(config)


if __name__ == "__main__":
    main()
