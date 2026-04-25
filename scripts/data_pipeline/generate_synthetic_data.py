"""Synthetic Data Generator — Using LLMs to generate training data for free."""

import asyncio
import json
import os
import logging
from typing import List, Dict
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.data.synthetic")

class SyntheticDataGenerator:
    """Generates synthetic SFT/DPO data using available free LLM providers."""
    
    def __init__(self):
        self.output_file = "data/training/synthetic_sft.json"
        self.topics = [
            "Python programming best practices",
            "Advanced SQL queries and optimization",
            "React.js component patterns",
            "Siberian Husky care and training",
            "Space exploration history",
            "Quantum physics for beginners",
            "Sustainable architecture trends",
            "World history: Industrial Revolution",
            "Turkish cuisine: Regional specialties",
            "Effective project management methodologies"
        ]

    async def generate_batch(self, count_per_topic: int = 5):
        """Generate a batch of Q&A pairs for each topic."""
        dataset = []
        
        for topic in self.topics:
            logger.info(f"Generating data for topic: {topic}")
            prompt = f"""
Generate {count_per_topic} high-quality question and answer pairs about: {topic}.
The response must be a JSON list of objects with "instruction" and "output" keys.
The "instruction" is the user's question, and "output" is the ideal assistant response.
Make the responses helpful, accurate, and in Turkish.

JSON Format:
[
  {{"instruction": "...", "output": "..."}},
  ...
]
"""
            try:
                # Use the router (it will pick the best free provider like Gemini or Groq)
                resp = await router.chat([{"role": "user", "content": prompt}])
                
                # Extract JSON
                import re
                match = re.search(r"\[[\s\S]*\]", resp.content)
                if match:
                    pairs = json.loads(match.group())
                    dataset.extend(pairs)
                    logger.info(f"Successfully generated {len(pairs)} pairs for {topic}")
            except Exception as e:
                logger.error(f"Failed to generate for {topic}: {e}")

        # Save results
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Total synthetic data generated: {len(dataset)} examples")
        return dataset

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generator = SyntheticDataGenerator()
    asyncio.run(generator.generate_batch())
