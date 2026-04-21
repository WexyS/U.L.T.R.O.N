"""User Profile Manager — Persistent Relationship and Persona Tracking."""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class UserProfileManager:
    """Manages long-term user characteristics, preferences, and traits."""
    
    def __init__(self, persist_path: str = "./data/memory_v2/user_profile.json"):
        self.persist_path = Path(persist_path)
        self.profile = self._load_profile()

    def _load_profile(self) -> Dict[str, Any]:
        """Load profile from disk or return default."""
        if self.persist_path.exists():
            try:
                with open(self.persist_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load user profile: {e}")
        
        # Default fallback
        return {
            "user": {
                "name": "User",
                "technical_level": "Intermediate",
                "preferred_languages": [],
                "interaction_style": "Standard",
                "interests": [],
                "observed_traits": [],
                "learned_preferences": {},
                "last_updated": datetime.now().isoformat()
            },
            "history_summary": ""
        }

    def save_profile(self):
        """Save current profile state to disk."""
        try:
            self.profile["user"]["last_updated"] = datetime.now().isoformat()
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(self.profile, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save user profile: {e}")

    def get_summary_for_prompt(self) -> str:
        """Generates a concise summary for the LLM system prompt."""
        u = self.profile.get("user", {})
        summary = (
            f"USER PROFILE:\n"
            f"- Name: {u.get('name')}\n"
            f"- Technical Level: {u.get('technical_level')}\n"
            f"- Interests: {', '.join(u.get('interests', []))}\n"
            f"- Interaction Style: {u.get('interaction_style')}\n"
            f"- Observed Traits: {', '.join(u.get('observed_traits', []))}\n"
            f"- Known Preferences: {json.dumps(u.get('learned_preferences', {}))}\n"
            f"CONTEXT SUMMARY: {self.profile.get('history_summary', 'New interaction.')}"
        )
        return summary

    async def update_from_interaction(self, user_msg: str, assistant_msg: str, llm_callable=None):
        """
        Analyzes the interaction to extract new user traits.
        Requires an LLM callable to perform the semantic analysis.
        """
        if not llm_callable:
            return

        prompt = (
            f"Analyze the following interaction and extract any NEW user preferences, "
            f"traits, or technical details. Return ONLY a JSON object with keys: "
            f"'new_traits' (list), 'new_interests' (list), 'interaction_style_update' (string).\n\n"
            f"USER: {user_msg}\n"
            f"ASSISTANT: {assistant_msg}"
        )
        
        try:
            analysis_json = await llm_callable(prompt)
            updates = json.loads(analysis_json)
            
            # Merge updates
            u = self.profile["user"]
            u["observed_traits"] = list(set(u.get("observed_traits", []) + updates.get("new_traits", [])))
            u["interests"] = list(set(u.get("interests", []) + updates.get("new_interests", [])))
            if updates.get("interaction_style_update"):
                u["interaction_style"] = updates["interaction_style_update"]
            
            self.save_profile()
            logger.info("User profile updated from interaction.")
        except Exception as e:
            logger.error(f"Failed to update user profile from interaction: {e}")

manager = UserProfileManager()
