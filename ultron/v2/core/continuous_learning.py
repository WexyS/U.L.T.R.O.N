"""Continuous Learning Daemon — Automatically improving Ultron every day."""

import asyncio
import logging
import os
from datetime import datetime
from ultron.v2.core.event_bus import event_bus
from scripts.data_pipeline.harvest_conversations import ConversationHarvester
from scripts.data_pipeline.generate_synthetic_data import SyntheticDataGenerator

logger = logging.getLogger("ultron.core.learning")

class ContinuousLearningEngine:
    """Background engine that collects training data from interactions."""
    
    def __init__(self, interval_hours: int = 24):
        self.interval_hours = interval_hours
        self.harvester = ConversationHarvester()
        self.generator = SyntheticDataGenerator()
        self._running = False

    async def start(self):
        """Start the learning loop."""
        if self._running:
            return
        self._running = True
        logger.info(f"Continuous Learning Engine started (Interval: {self.interval_hours}h)")
        
        while self._running:
            try:
                await self.perform_learning_cycle()
            except Exception as e:
                logger.error(f"Learning cycle failed: {e}")
            
            await asyncio.sleep(self.interval_hours * 3600)

    async def stop(self):
        self._running = False

    async def perform_learning_cycle(self):
        """Harvest local data and generate synthetic samples."""
        logger.info("Starting daily learning cycle...")
        
        # 1. Harvest from local DB
        harvested = self.harvester.harvest(min_length=200)
        
        # 2. Generate some synthetic data to maintain diversity
        synthetic = await self.generator.generate_batch(count_per_topic=2)
        
        # 3. Log progress to Event Bus
        total = len(harvested) + len(synthetic)
        await event_bus.publish_simple(
            "learning_progress",
            "ContinuousLearner",
            {
                "timestamp": datetime.now().isoformat(),
                "harvested_count": len(harvested),
                "synthetic_count": len(synthetic),
                "total_new_samples": total
            }
        )
        logger.info(f"Learning cycle complete. {total} new samples collected.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = ContinuousLearningEngine()
    asyncio.run(engine.start())
