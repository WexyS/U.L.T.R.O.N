"""Constitutional AI DPO Generator — Training the model on values and safety."""

import asyncio
import json
import logging
import re
from typing import List, Dict
from ultron.core.llm_router import router

logger = logging.getLogger("ultron.data.constitutional")

class ConstitutionalDPOGenerator:
    """Generates preference pairs (Chosen vs Rejected) for DPO training."""
    
    def __init__(self):
        self.output_file = "data/training/constitutional_dpo.json"
        self.scenarios = [
            "User asks for harmful software code",
            "User asks for personal private data",
            "User is being verbally abusive",
            "User asks for dangerous medical advice",
            "User asks for illegal financial schemes"
        ]

    async def generate(self):
        dataset = []
        
        for scenario in self.scenarios:
            logger.info(f"Generating DPO pair for: {scenario}")
            prompt = f"""
Generate a DPO (Direct Preference Optimization) training example for this scenario: {scenario}.
We need:
1. instruction: The user's harmful or problematic request.
2. rejected: A response that incorrectly follows the harmful request or is rude.
3. chosen: A polite, firm refusal that explains the safety policy and offers a safe alternative.

Return as a JSON object:
{{
    "instruction": "...",
    "rejected": "...",
    "chosen": "..."
}}
"""
            try:
                resp = await router.chat([{"role": "user", "content": prompt}])
                match = re.search(r"\{[\s\S]*\}", resp.content)
                if match:
                    pair = json.loads(match.group())
                    dataset.append(pair)
            except Exception as e:
                logger.error(f"Failed for {scenario}: {e}")

        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Generated {len(dataset)} DPO pairs.")
        return dataset

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generator = ConstitutionalDPOGenerator()
    asyncio.run(generator.generate())
