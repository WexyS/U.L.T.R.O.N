"""
MemoryManager — Tüm katmanları birleştiren tek arayüz.
Her konuşma turunda: working memory'e ekle, önem skoru hesapla,
önemliyse long_term'e kaydet, entity extraction yap.
"""

from .working_memory import WorkingMemory
from .long_term_memory import LongTermMemory


class MemoryManager:
    def __init__(self):
        self.working = WorkingMemory(max_messages=20)
        self.long_term = LongTermMemory()

    async def init(self):
        await self.long_term.init()

    async def process_turn(self, user_msg: str, assistant_msg: str, importance: float = 0.4):
        self.working.add("user", user_msg)
        self.working.add("assistant", assistant_msg)
        if importance > 0.3:
            summary = f"Kullanıcı: {user_msg[:100]} | Ultron: {assistant_msg[:100]}"
            await self.long_term.store_episode(summary, importance=importance)

    async def get_context(self, query: str) -> dict:
        memories = await self.long_term.recall(query, top_k=3)
        return {
            "working": await self.working.to_messages_async(),
            "long_term": memories,
            "token_count": self.working.token_count()
        }

    async def nightly_consolidation(self):
        await self.long_term.nightly_decay()
        await self.long_term.consolidate()

    def stats(self) -> dict:
        return {
            "working": self.working.stats(),
            "long_term": self.long_term.stats(),
        }
