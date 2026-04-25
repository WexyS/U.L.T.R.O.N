"""Agent package — tüm specialized agentlar."""

from .base import Agent
from .coder import CoderAgent
from .researcher import ResearcherAgent
from .rpa_operator import RPAOperatorAgent
from .email_agent import EmailAgent
from .sysmon_agent import SystemMonitorAgent
from .clipboard_agent import ClipboardAgent
from .meeting_agent import MeetingAgent
from .files_agent import FilesAgent
from .calendar_agent import CalendarAgent
from .task_manager_agent import TaskManagerAgent
from .vision_agent import UltronVisionAgent
from .debate_agent import DebateAgent

# ── Ultron v3.0 Cognitive Agents ───────────────────────────────────
from .cognitive.task_decomposer import TaskDecomposerAgent
from .cognitive.planning_agent import PlanningAgent
from .cognitive.self_reflection import SelfReflectionAgent
from .cognitive.critique_agent import CritiqueAgent
from .cognitive.learning_agent import LearningAgent
from .cognitive.meta_reasoning import MetaReasoningAgent

# ── Ultron v3.0 Knowledge Agents ───────────────────────────────────
from .knowledge.enhanced_researcher import EnhancedResearcherAgent
from .knowledge.academic_researcher import AcademicResearchAgent
from .knowledge.knowledge_graph_agent import KnowledgeGraphAgent
from .knowledge.fact_check_agent import FactCheckAgent
from .knowledge.news_monitor_agent import NewsMonitorAgent
from .knowledge.document_parser_agent import DocumentParserAgent

# ── Ultron v3.0 Creation Agents ────────────────────────────────────
from .creation.coder_agent_v3 import CoderAgentV3
from .creation.debugger_agent import DebuggerAgent
from .creation.code_reviewer import CodeReviewAgent
from .creation.architect_agent import ArchitectAgent
from .creation.documentation_agent import DocumentationAgent
from .creation.test_generator_agent import TestGeneratorAgent

# ── Ultron v3.0 Data & Media Agents ────────────────────────────────
from .data.data_analysis_agent import DataAnalysisAgent
from .data.visualization_agent import VisualizationAgent
from .media.image_analysis_agent import ImageAnalysisAgent

# ── Ultron v3.0 Finance Agents ─────────────────────────────────────
from .finance.finance_tracker_agent import FinanceTrackerAgent
from .finance.market_monitor_agent import MarketMonitorAgent

# ── Ultron v3.0 Creative Agents ────────────────────────────────────
from .creative.storyteller_agent import StorytellerAgent
from .creative.creative_writing_agent import CreativeWritingAgent
from .creative.game_master_agent import GameMasterAgent
from .creative.music_composition_agent import MusicCompositionAgent
from .creative.roleplay_agent import RoleplayAgent
from .creative.image_generation_agent import ImageGenerationAgent
from .creative.video_generation_agent import VideoGenerationAgent
from .creative.image_editing_agent import ImageEditingAgent

# ── Ultron v3.0 System Agents ──────────────────────────────────────
from .system.web_monitor_agent import WebMonitorAgent
from .productivity.calendar_task_agent import CalendarTaskAgent

# ── Ultron v3.0 Technical & Security Agents ────────────────────────
from .technical.security_audit_agent import SecurityAuditAgent
from .technical.system_admin_agent import SystemAdminAgent
from .technical.network_monitor_agent import NetworkMonitorAgent
from .technical.log_analysis_agent import LogAnalysisAgent
from .technical.vulnerability_scanner_agent import VulnerabilityScannerAgent

# ── Ultron v3.0 IoT & Control Agents ───────────────────────────────
from .iot.voice_control_agent import VoiceControlAgent
from .iot.visual_input_agent import VisualInputAgent
from .iot.hardware_control_agent import HardwareControlAgent
from .iot.smart_home_agent import SmartHomeAgent
from .iot.iot_sensor_agent import IoTSensorAgent

# ── Ultron v3.0 Meta-Cognitive Agents ──────────────────────────────
from .meta.self_improvement_agent import SelfImprovementAgent
from .meta.curiosity_agent import CuriosityAgent
from .meta.hypothesis_testing_agent import HypothesisTestingAgent
from .meta.creative_problem_solving_agent import CreativeProblemSolvingAgent
from .meta.autonomous_research_agent import AutonomousResearchAgent
from .swarm_catalyst import SwarmCatalyst

__all__ = [
    "Agent", "CoderAgent", "ResearcherAgent", "RPAOperatorAgent",
    "EmailAgent", "SystemMonitorAgent", "ClipboardAgent", "MeetingAgent",
    "FilesAgent", "CalendarAgent", "TaskManagerAgent", "UltronVisionAgent",
    "DebateAgent", "TaskDecomposerAgent", "PlanningAgent", "SelfReflectionAgent",
    "CritiqueAgent", "LearningAgent", "MetaReasoningAgent", "EnhancedResearcherAgent",
    "AcademicResearchAgent", "KnowledgeGraphAgent", "FactCheckAgent", "NewsMonitorAgent",
    "CoderAgentV3", "DebuggerAgent", "CodeReviewAgent", "ArchitectAgent",
    "DocumentationAgent", "TestGeneratorAgent", "DataAnalysisAgent", "VisualizationAgent",
    "DocumentParserAgent", "ImageAnalysisAgent", "FinanceTrackerAgent", "MarketMonitorAgent",
    "StorytellerAgent", "CreativeWritingAgent", "GameMasterAgent", "MusicCompositionAgent",
    "RoleplayAgent", "ImageGenerationAgent", "VideoGenerationAgent", "ImageEditingAgent",
    "SecurityAuditAgent", "SystemAdminAgent", "NetworkMonitorAgent",
    "LogAnalysisAgent", "VulnerabilityScannerAgent", "VoiceControlAgent", "VisualInputAgent",
    "HardwareControlAgent", "SmartHomeAgent", "IoTSensorAgent", "SelfImprovementAgent",
    "CuriosityAgent", "HypothesisTestingAgent", "CreativeProblemSolvingAgent", "AutonomousResearchAgent",
    "WebMonitorAgent", "CalendarTaskAgent", "SwarmCatalyst"
]
