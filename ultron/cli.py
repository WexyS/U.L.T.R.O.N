"""CLI arayüzü — Ultron'ı başlatır (GUI varsayılan, --cli ile terminal)."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
from pathlib import Path

from rich.console import Console
from rich.text import Text

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
    ("║  Qwen 2.5 14B + Claude  •  Multi-Agent  •  OpenRouter         ║\n", "bold green"),
    ("╚" + "═" * 69 + "╝\n", "bold cyan"),
)


def _init_v2_sync(config: UltronConfig):
    """Initialize v2 orchestrator synchronously."""
    from dotenv import load_dotenv
    load_dotenv()
    from ultron.v2.core.llm_router import LLMRouter
    from ultron.v2.memory.engine import MemoryEngine
    from ultron.v2.core.orchestrator import Orchestrator

    console.print("[dim]LLM Router başlatılıyor...[/dim]")
    llm = LLMRouter(ollama_model=config.model.ollama_model or "qwen2.5:14b")
    llm.enable_all_providers(dict(os.environ))

    console.print("[dim]Memory Engine başlatılıyor...[/dim]")
    memory = MemoryEngine(persist_dir="./data/memory_v2")

    console.print("[dim]Orchestrator başlatılıyor...[/dim]")
    orch = Orchestrator(llm_router=llm, memory=memory, work_dir="./workspace")

    async def _bootstrap() -> None:
        try:
            await orch.start()
        except Exception as exc:
            console.print(f"[yellow]⚠[/] Orchestrator start: {exc}")

    asyncio.run(_bootstrap())

    providers = llm.get_healthy_providers()
    console.print(f"[green]✓[/] Providers: {', '.join(providers)}")
    console.print(f"[green]✓[/] Agents: {list(orch.agents.keys())}")
    return orch


def run_gui(config: UltronConfig) -> None:
    """Mark-XXXV GUI'yi başlat — SADECE v2 orchestrator ile."""
    ensure_directories(config)

    # V2 Orchestrator (tek gerçek beyin)
    orchestrator = None
    try:
        orchestrator = _init_v2_sync(config)
    except Exception as e:
        console.print(f"[red]✗[/] v2 Multi-Agent: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # GUI (orchestrator ile, voice pipeline YOK — cache loop sorunu var)
    try:
        from ultron.gui_app import UltronGUI
        app = UltronGUI(pipeline=None, orchestrator=orchestrator, config=config)
        app.run()
    except Exception as e:
        console.print(f"[red]GUI başlatılamadı: {e}[/]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def async_main(config: UltronConfig) -> None:
    """Terminal modu — v2 orchestrator ile."""
    console.print(BANNER)

    from dotenv import load_dotenv
    load_dotenv()
    from ultron.v2.core.llm_router import LLMRouter
    from ultron.v2.memory.engine import MemoryEngine
    from ultron.v2.core.orchestrator import Orchestrator

    llm = LLMRouter(ollama_model=config.model.ollama_model or "qwen2.5:14b")
    llm.enable_all_providers(dict(os.environ))
    memory = MemoryEngine(persist_dir="./data/memory_v2")
    orch = Orchestrator(llm_router=llm, memory=memory, work_dir="./workspace")

    try:
        await orch.start()
    except Exception as exc:
        console.print(f"[yellow]⚠[/] Orchestrator start: {exc}")

    console.print("[green]✓[/] Ultron v2.0 hazır. Yazmaya başlayın (/quit ile çıkış)\n")

    while True:
        try:
            user_input = console.input("[bold green]You> [/bold green]").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                break

            with console.status("[dim]Ultron düşünüyor...[/dim]", spinner="dots"):
                response = await orch.process(user_input)

            console.print(f"\n[bold cyan]Ultron:[/bold cyan] {response}\n")
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[red]Hata: {e}[/red]")

    await orch.stop()
    console.print("\n[yellow]Güle güle.[/yellow]")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Ultron — Kişisel Yapay Zeka Asistanı")
    parser.add_argument("--config", "-c", help="Yapılandırma dosyası")
    parser.add_argument("--cli", action="store_true", help="Terminal modu")
    args = parser.parse_args()

    config = load_config(args.config)

    # Resolve paths
    project_root = Path(__file__).parent.parent
    log_file = config.logging.file
    if not os.path.isabs(log_file):
        log_file = str(project_root / log_file)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    mem_dir = config.memory.persist_dir
    if not os.path.isabs(mem_dir):
        config.memory.persist_dir = str(project_root / mem_dir)

    doc_dir = config.documents.persist_directory
    if not os.path.isabs(doc_dir):
        config.documents.persist_directory = str(project_root / doc_dir)

    work_dir = config.coding.work_dir
    if not os.path.isabs(work_dir):
        config.coding.work_dir = str(project_root / work_dir)

    ensure_directories(config)

    logging.basicConfig(
        level=getattr(logging, config.logging.level),
        filename=log_file,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.cli:
        try:
            asyncio.run(async_main(config))
        except KeyboardInterrupt:
            console.print("\n[yellow]İptal.[/]")
        except Exception as e:
            console.print(f"\n[red]Hata: {e}[/]")
    else:
        run_gui(config)


if __name__ == "__main__":
    main()
