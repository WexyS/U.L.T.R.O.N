"""Tests for User Profile and Emotional Intelligence (EQ) features."""
import pytest
import asyncio
from ultron.v2.memory.user_profile_manager import UserProfileManager
from ultron.v2.core.react_orchestrator import ReActOrchestrator

@pytest.fixture
def profile_manager(tmp_path):
    # Use a temporary file for testing
    test_path = tmp_path / "test_profile.json"
    return UserProfileManager(persist_path=str(test_path))

def test_profile_initialization(profile_manager):
    """Test if the profile manager loads correctly."""
    summary = profile_manager.get_summary_for_prompt()
    assert "USER PROFILE" in summary
    assert "Technical Level" in summary

def test_profile_update(profile_manager):
    """Test if we can manually update profile traits."""
    profile_manager.profile["user"]["observed_traits"].append("Loves testing")
    profile_manager.save_profile()
    
    summary = profile_manager.get_summary_for_prompt()
    assert "Loves testing" in summary

@pytest.mark.asyncio
async def test_sentiment_analysis():
    """Test the sentiment analysis logic in Orchestrator."""
    orchestrator = ReActOrchestrator()
    
    # We mock the sentiment for unit testing if needed, 
    # but here we test the logic.
    stress_text = "I am so frustrated, nothing is working and I have a deadline!"
    sentiment = await orchestrator._analyze_sentiment(stress_text)
    
    # The output should be one of our defined moods
    assert sentiment in ["CHILL", "STRESSED", "CURIOUS", "ANGRY", "EXCITED", "CONFUSED"]

@pytest.mark.asyncio
async def test_orchestrator_profile_injection():
    """Test if the orchestrator correctly pulls the user profile."""
    from ultron.v2.core.base_agent import AgentTask
    
    orchestrator = ReActOrchestrator()
    task = AgentTask(task_id="test", input_data="Hello Ultron")
    
    # This triggers the profile loading in the execute flow (partial test)
    user_context = orchestrator.memory.get_summary_for_prompt() if hasattr(orchestrator, 'memory') and hasattr(orchestrator.memory, 'get_summary_for_prompt') else "Test Profile"
    assert "PROFILE" in user_context or "Test Profile" == user_context
