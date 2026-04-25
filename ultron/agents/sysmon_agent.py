"""System Monitor Agent — psutil ile CPU/RAM/disk/GPU izleme."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from ultron.agents.base import Agent
from ultron.core.blackboard import Blackboard
from ultron.core.event_bus import EventBus
from ultron.core.llm_router import LLMRouter
from ultron.core.types import AgentRole, Task, TaskResult, TaskStatus

logger = logging.getLogger(__name__)

# ── Optional dependency ──────────────────────────────────────────────────────
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None  # type: ignore[assignment]


class SystemMonitorAgent(Agent):
    agent_name = "SystemMonitorAgent"
    agent_description = "System monitor agent — CPU, RAM, disk, network metrics via psutil."

    """System monitor agent — CPU, RAM, disk, network metrics via psutil."""

    # Default alert thresholds (percent)
    DEFAULT_CPU_THRESHOLD: float = 85.0
    DEFAULT_RAM_THRESHOLD: float = 90.0
    DEFAULT_DISK_THRESHOLD: float = 95.0

    def __init__(
        self,
        llm_router: LLMRouter,
        event_bus: EventBus,
        blackboard: Blackboard,
    ) -> None:
        super().__init__(
            role=AgentRole.SYSMON,
            llm_router=llm_router,
            event_bus=event_bus,
            blackboard=blackboard,
        )
        self._cpu_threshold: float = self.DEFAULT_CPU_THRESHOLD
        self._ram_threshold: float = self.DEFAULT_RAM_THRESHOLD
        self._disk_threshold: float = self.DEFAULT_DISK_THRESHOLD

        # Allow per-instance override from environment
        import os

        try:
            self._cpu_threshold = float(
                os.getenv("ULTRON_SYSMON_CPU_THRESHOLD", self._cpu_threshold)
            )
            self._ram_threshold = float(
                os.getenv("ULTRON_SYSMON_RAM_THRESHOLD", self._ram_threshold)
            )
            self._disk_threshold = float(
                os.getenv("ULTRON_SYSMON_DISK_THRESHOLD", self._disk_threshold)
            )
        except ValueError:
            logger.warning("Invalid threshold env vars, using defaults")

    # ── Abstract overrides ───────────────────────────────────────────────────

    def _default_system_prompt(self) -> str:
        return (
            "You are Ultron, a system monitoring assistant. You track CPU, "
            "memory, disk and network usage on the host machine. You can "
            "report current metrics, list top processes by resource usage, "
            "check if thresholds are exceeded, and provide disk usage "
            "breakdown. Always present data clearly with units and "
            "percentages. Warn when any metric approaches or exceeds its "
            "threshold."
        )

    async def execute(self, task: Task) -> TaskResult:
        """Route task based on description / intent keyword."""
        text = (task.input_data + " " + task.intent).lower()

        try:
            if not PSUTIL_AVAILABLE:
                return TaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    error=(
                        "psutil is not installed. Run: pip install psutil"
                    ),
                    metadata={"agent": self.role.value},
                )

            if any(kw in text for kw in ("metric", "status", "cpu", "ram", "memory", "usage", "durum")):
                result = await self._get_system_metrics()
                return self._ok(task, result)

            if any(kw in text for kw in ("process", "top", "task", "working")):
                by = task.context.get("by", "cpu")
                limit = task.context.get("limit", 10)
                result = await self._get_top_processes(limit=limit, by=by)
                return self._ok(task, result)

            if any(kw in text for kw in ("alert", "threshold", "warn", "check", "kontrol")):
                result = await self._check_thresholds()
                return self._ok(task, result)

            if any(kw in text for kw in ("disk", "storage", "depo")):
                result = await self._get_disk_usage()
                return self._ok(task, result)

            # Default: return system metrics
            result = await self._get_system_metrics()
            return self._ok(task, result)

        except Exception as exc:
            logger.exception("SystemMonitorAgent task %s failed", task.task_id)
            return TaskResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                error=str(exc),
                metadata={"agent": self.role.value},
            )

    async def _subscribe_events(self) -> None:
        """Subscribe to sysmon-related events."""
        await self.event_bus.publish_simple(
            "agent:ready", self.role.value, {"agent": self.role.value}
        )

        self.event_bus.subscribe_all(self._on_any_event)
        logger.info("SystemMonitorAgent subscribed to sysmon:* events")

    async def _on_any_event(self, event: Any) -> None:
        """Handle any event — filter sysmon-related ones."""
        if not event.name.startswith("sysmon:"):
            return

        logger.info("SystemMonitorAgent received event '%s'", event.name)
        data = event.data
        action = data.get("action", "")

        if action in ("metrics", "status"):
            try:
                metrics = await self._get_system_metrics()
                await self._publish_event("sysmon:metrics_ready", {"metrics": metrics})
            except Exception as exc:
                await self._publish_event("sysmon:error", {"error": str(exc)})

        elif action in ("alert", "threshold", "check"):
            try:
                alerts = await self._check_thresholds()
                await self._publish_event("sysmon:alerts_ready", {"alerts": alerts})
            except Exception as exc:
                await self._publish_event("sysmon:error", {"error": str(exc)})

        elif action in ("process", "top"):
            try:
                processes = await self._get_top_processes(
                    limit=data.get("limit", 10),
                    by=data.get("by", "cpu"),
                )
                await self._publish_event("sysmon:processes_ready", {"processes": processes})
            except Exception as exc:
                await self._publish_event("sysmon:error", {"error": str(exc)})

        elif action in ("disk", "storage"):
            try:
                disk_info = await self._get_disk_usage()
                await self._publish_event("sysmon:disk_ready", {"disk": disk_info})
            except Exception as exc:
                await self._publish_event("sysmon:error", {"error": str(exc)})

    # ── System metrics ───────────────────────────────────────────────────────

    async def _get_system_metrics(self) -> str:
        """Collect and return a human-readable system metrics report."""

        # psutil calls are synchronous → run in thread pool
        cpu_count, cpu_freq, cpu_pct = await asyncio.to_thread(self._read_cpu_info)
        mem = await asyncio.to_thread(psutil.virtual_memory)  # type: ignore[union-attr]
        swap = await asyncio.to_thread(psutil.swap_memory)  # type: ignore[union-attr]
        net = await asyncio.to_thread(psutil.net_io_counters)  # type: ignore[union-attr]
        boot_time = await asyncio.to_thread(
            lambda: time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(psutil.boot_time()))  # type: ignore[union-attr]
        )
        uptime_seconds = time.time() - psutil.boot_time()  # type: ignore[union-attr]

        # Format
        lines: list[str] = []
        lines.append("═══ System Metrics Report ═══")
        lines.append("")

        # CPU
        lines.append("── CPU ──")
        lines.append(f"  Logical cores : {cpu_count}")
        if cpu_freq and cpu_freq.current > 0:
            lines.append(
                f"  Frequency     : {cpu_freq.current:.0f} MHz "
                f"(min: {cpu_freq.min:.0f}, max: {cpu_freq.max:.0f})"
            )
        lines.append(f"  Usage         : {cpu_pct:.1f}%")
        lines.append(
            f"  Per-core      : "
            f"{', '.join(f'{p:.1f}%' for p in self._per_cpu_percent())}"
        )
        lines.append("")

        # Memory
        lines.append("── Memory ──")
        lines.append(f"  Total         : {self._bytes_to_gb(mem.total):.1f} GB")
        lines.append(f"  Used          : {self._bytes_to_gb(mem.used):.1f} GB")
        lines.append(f"  Available     : {self._bytes_to_gb(mem.available):.1f} GB")
        lines.append(f"  Usage         : {mem.percent:.1f}%")
        lines.append(f"  Swap Total    : {self._bytes_to_gb(swap.total):.1f} GB")
        lines.append(f"  Swap Used     : {self._bytes_to_gb(swap.used):.1f} GB")
        lines.append("")

        # Network
        if net:
            lines.append("── Network ──")
            lines.append(f"  Bytes sent    : {self._bytes_to_human(net.bytes_sent)}")
            lines.append(f"  Bytes recv    : {self._bytes_to_human(net.bytes_recv)}")
            lines.append(f"  Packets sent  : {net.packets_sent:,}")
            lines.append(f"  Packets recv  : {net.packets_recv:,}")
            lines.append("")

        # Uptime
        lines.append("── Uptime ──")
        lines.append(f"  Boot time     : {boot_time}")
        lines.append(f"  Up for        : {self._format_uptime(uptime_seconds)}")

        report = "\n".join(lines)

        # Store on blackboard for other agents
        await self.store_context(
            "sysmon:latest_metrics",
            {
                "cpu_percent": cpu_pct,
                "mem_percent": mem.percent,
                "mem_available_gb": self._bytes_to_gb(mem.available),
                "timestamp": time.time(),
            },
        )

        return report

    # ── Top processes ────────────────────────────────────────────────────────

    async def _get_top_processes(self, limit: int = 10, by: str = "cpu") -> str:
        """Return the top processes sorted by CPU or memory usage."""

        def _collect() -> list[dict[str, Any]]:
            procs: list[dict[str, Any]] = []
            for proc in psutil.process_iter(  # type: ignore[union-attr]
                ["pid", "name", "username", "cpu_percent", "memory_percent", "memory_info", "status"]
            ):
                try:
                    info = proc.info
                    mem_mb = 0.0
                    if info.get("memory_info"):
                        mem_mb = info["memory_info"].rss / (1024 * 1024)
                    procs.append(
                        {
                            "pid": info.get("pid", "?"),
                            "name": info.get("name", "?"),
                            "username": info.get("username", "?"),
                            "cpu_percent": info.get("cpu_percent", 0.0) or 0.0,
                            "memory_percent": info.get("memory_percent", 0.0) or 0.0,
                            "memory_mb": round(mem_mb, 1),
                            "status": info.get("status", "?"),
                        }
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):  # type: ignore[union-attr]
                    continue
            return procs

        all_procs = await asyncio.to_thread(_collect)

        # Sort
        reverse = True
        if by.lower() in ("mem", "memory", "ram"):
            all_procs.sort(key=lambda p: p["memory_percent"], reverse=reverse)
        elif by.lower() in ("pid",):
            all_procs.sort(key=lambda p: p["pid"], reverse=False)
        else:
            all_procs.sort(key=lambda p: p["cpu_percent"], reverse=reverse)

        top = all_procs[:limit]

        # Format
        lines: list[str] = []
        lines.append(f"═══ Top {len(top)} Processes (by {by}) ═══")
        lines.append("")
        lines.append(
            f"{'PID':<8} {'Name':<25} {'CPU%':<8} {'MEM%':<8} {'MEM(MB)':<10} {'Status':<12}"
        )
        lines.append("-" * 71)
        for p in top:
            lines.append(
                f"{p['pid']:<8} {p['name']:<25} {p['cpu_percent']:<8.1f} "
                f"{p['memory_percent']:<8.1f} {p['memory_mb']:<10.1f} {p['status']:<12}"
            )

        return "\n".join(lines)

    # ── Threshold checking ───────────────────────────────────────────────────

    async def _check_thresholds(
        self,
        cpu_threshold: Optional[float] = None,
        ram_threshold: Optional[float] = None,
        disk_threshold: Optional[float] = None,
    ) -> str:
        """Compare current metrics against thresholds and report alerts."""
        cpu_t = cpu_threshold if cpu_threshold is not None else self._cpu_threshold
        ram_t = ram_threshold if ram_threshold is not None else self._ram_threshold
        disk_t = disk_threshold if disk_threshold is not None else self._disk_threshold

        # Read current values
        cpu_pct = await asyncio.to_thread(psutil.cpu_percent, interval=1)  # type: ignore[union-attr]
        mem = await asyncio.to_thread(psutil.virtual_memory)  # type: ignore[union-attr]

        alerts: list[str] = []
        has_alert = False

        # CPU check
        if cpu_pct >= cpu_t:
            alerts.append(
                f"⚠ ALERT — CPU usage {cpu_pct:.1f}% exceeds threshold {cpu_t:.0f}%"
            )
            has_alert = True
        else:
            alerts.append(
                f"  OK  — CPU usage {cpu_pct:.1f}% (threshold: {cpu_t:.0f}%)"
            )

        # RAM check
        if mem.percent >= ram_t:
            alerts.append(
                f"⚠ ALERT — RAM usage {mem.percent:.1f}% exceeds threshold {ram_t:.0f}%"
            )
            has_alert = True
        else:
            alerts.append(
                f"  OK  — RAM usage {mem.percent:.1f}% (threshold: {ram_t:.0f}%)"
            )

        # Disk check (all partitions)
        disk_lines = await self._check_disk_thresholds(disk_t)
        alerts.extend(disk_lines)
        if any("ALERT" in line for line in disk_lines):
            has_alert = True

        # Publish alert event if needed
        await self._publish_event(
            "sysmon:threshold_check",
            {
                "cpu_percent": cpu_pct,
                "ram_percent": mem.percent,
                "has_alert": has_alert,
                "thresholds": {
                    "cpu": cpu_t,
                    "ram": ram_t,
                    "disk": disk_t,
                },
            },
        )

        header = "═══ Threshold Check ═══"
        if has_alert:
            header += "\n⛔ Some thresholds exceeded!"
        else:
            header += "\n✓ All metrics within normal range."

        return header + "\n\n" + "\n".join(alerts)

    async def _check_disk_thresholds(self, threshold: float) -> list[str]:
        """Check disk usage for all mounted partitions."""

        def _read_disks() -> list[tuple[str, float, float, float]]:
            partitions = psutil.disk_partitions(all=False)  # type: ignore[union-attr]
            results: list[tuple[str, float, float, float]] = []
            for part in partitions:
                try:
                    usage = psutil.disk_usage(part.mountpoint)  # type: ignore[union-attr]
                    results.append(
                        (
                            part.mountpoint,
                            usage.percent,
                            self._bytes_to_gb(usage.total),
                            self._bytes_to_gb(usage.free),
                        )
                    )
                except (PermissionError, OSError):
                    continue
            return results

        disk_data = await asyncio.to_thread(_read_disks)

        lines: list[str] = []
        for mount, pct, total_gb, free_gb in disk_data:
            if pct >= threshold:
                lines.append(
                    f"⚠ ALERT — Disk '{mount}' usage {pct:.1f}% "
                    f"(total: {total_gb:.1f} GB, free: {free_gb:.1f} GB, "
                    f"threshold: {threshold:.0f}%)"
                )
            else:
                lines.append(
                    f"  OK  — Disk '{mount}' usage {pct:.1f}% "
                    f"(total: {total_gb:.1f} GB, free: {free_gb:.1f} GB)"
                )
        return lines

    # ── Disk usage summary ───────────────────────────────────────────────────

    async def _get_disk_usage(self) -> str:
        """Return a disk usage summary for all mounted partitions."""

        def _read_disks() -> list[dict[str, Any]]:
            partitions = psutil.disk_partitions(all=False)  # type: ignore[union-attr]
            results: list[dict[str, Any]] = []
            for part in partitions:
                try:
                    usage = psutil.disk_usage(part.mountpoint)  # type: ignore[union-attr]
                    results.append(
                        {
                            "device": part.device,
                            "mountpoint": part.mountpoint,
                            "fstype": part.fstype,
                            "total_gb": self._bytes_to_gb(usage.total),
                            "used_gb": self._bytes_to_gb(usage.used),
                            "free_gb": self._bytes_to_gb(usage.free),
                            "percent": usage.percent,
                        }
                    )
                except (PermissionError, OSError):
                    continue
            return results

        disk_data = await asyncio.to_thread(_read_disks)

        lines: list[str] = []
        lines.append("═══ Disk Usage ═══")
        lines.append("")
        lines.append(
            f"{'Mount':<20} {'Type':<10} {'Total':<12} {'Used':<12} {'Free':<12} {'Use%':<8}"
        )
        lines.append("-" * 74)
        for d in disk_data:
            lines.append(
                f"{d['mountpoint']:<20} {d['fstype']:<10} "
                f"{d['total_gb']:<12.1f} {d['used_gb']:<12.1f} "
                f"{d['free_gb']:<12.1f} {d['percent']:<8.1f}"
            )

        return "\n".join(lines)

    # ── Static helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _read_cpu_info() -> tuple[int, Any, float]:
        """Synchronous CPU info read — runs in thread."""
        count = psutil.cpu_count(logical=True)  # type: ignore[union-attr]
        freq = psutil.cpu_freq()  # type: ignore[union-attr]
        pct = psutil.cpu_percent(interval=0.5)  # type: ignore[union-attr]
        return count, freq, pct

    @staticmethod
    def _per_cpu_percent() -> list[float]:
        """Per-CPU usage percentages."""
        return psutil.cpu_percent(percpu=True, interval=0)  # type: ignore[union-attr]

    @staticmethod
    def _bytes_to_gb(n: float | int) -> float:
        return n / (1024 ** 3)

    @staticmethod
    def _bytes_to_human(n: float | int) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(n) < 1024:
                return f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} PB"

    @staticmethod
    def _format_uptime(seconds: float) -> str:
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        return " ".join(parts)

    @staticmethod
    def _ok(task: Task, output: str) -> TaskResult:
        return TaskResult(
            task_id=task.task_id,
            status=TaskStatus.SUCCESS,
            output=output,
            metadata={"agent": AgentRole.SYSMON.value},
        )
