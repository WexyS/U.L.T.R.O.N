"""Test for Dynamic Skill Discovery."""
import pytest
import asyncio
import os
from pathlib import Path
from ultron.core.skill_engine import SkillEngine

@pytest.mark.asyncio
async def test_dynamic_skill_creation():
    engine = SkillEngine()
    skill_name = "test_dynamic_hello"
    skill_description = "A test skill created dynamically."
    skill_code = "return {'message': 'Hello from dynamic skill!'}"
    
    # Ensure cleanup
    skill_file = Path(f"ultron/v2/skills/{skill_name}.py")
    if skill_file.exists():
        skill_file.unlink()
        
    # Create new skill
    result = await engine.skill_create_new_skill(skill_name, skill_code, skill_description)
    assert result["success"] is True
    
    # Execute the new skill
    # We might need to wait a bit or re-trigger load_dynamic_skills (which skill_create_new_skill does)
    output = await engine.run(skill_name)
    assert output["message"] == "Hello from dynamic skill!"
    
    # Cleanup
    if skill_file.exists():
        skill_file.unlink()
