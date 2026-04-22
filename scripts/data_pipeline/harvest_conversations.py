"""Conversation Harvester — Extracting high-quality training data from local chat history."""

import sqlite3
import json
import os
import logging
from typing import List, Dict

logger = logging.getLogger("ultron.data.harvester")

class ConversationHarvester:
    """Harvests successful chat pairs for SFT/DPO training."""
    
    def __init__(self, db_path: str = "data/conversations.db"):
        self.db_path = db_path
        self.output_file = "data/training/harvested_sft.json"

    def harvest(self, min_length: int = 100) -> List[Dict]:
        """Harvest high-quality (instruction, output) pairs."""
        if not os.path.exists(self.db_path):
            logger.error(f"Database not found at {self.db_path}")
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # We want user message followed by assistant response
        query = """
        SELECT m1.content as user_msg, m2.content as assistant_msg
        FROM messages m1
        JOIN messages m2 ON m1.conversation_id = m2.conversation_id
        WHERE m1.role = 'user' AND m2.role = 'assistant'
        AND m1.created_at < m2.created_at
        AND length(m2.content) > ?
        GROUP BY m1.id
        ORDER BY m1.created_at DESC
        """
        
        cursor.execute(query, (min_length,))
        rows = cursor.fetchall()
        
        dataset = []
        for row in rows:
            user_msg, assistant_msg = row
            dataset.append({
                "instruction": user_msg,
                "input": "",
                "output": assistant_msg
            })
            
        conn.close()
        
        # Save results
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Harvested {len(dataset)} examples to {self.output_file}")
        return dataset

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    harvester = ConversationHarvester()
    harvester.harvest()
