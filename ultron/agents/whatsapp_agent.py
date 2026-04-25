import logging
import asyncio
from typing import Optional
from ultron.agents.base import Agent
from ultron.core.types import AgentRole, AgentStatus, Task, TaskResult, TaskStatus
from ultron.core.event_bus import EventBus
from ultron.core.blackboard import Blackboard
from ultron.core.llm_router import LLMRouter

logger = logging.getLogger(__name__)

class WhatsAppAgent(Agent):
    agent_name = "WhatsAppAgent"
    agent_description = "Specialized agent for WhatsApp Web automation."

    """Specialized agent for WhatsApp Web automation."""

    def __init__(
        self,
        llm_router: LLMRouter,
        event_bus: EventBus,
        blackboard: Blackboard,
    ) -> None:
        super().__init__(
            role=AgentRole.ASSISTANT, # Using Assistant role for custom messaging
            llm_router=llm_router,
            event_bus=event_bus,
            blackboard=blackboard,
        )
        self._browser = None
        self._page = None

    def _default_system_prompt(self) -> str:
        return (
            "You are a WhatsApp messaging expert.\n"
            "Your goal is to navigate WhatsApp Web to send messages to specific contacts.\n"
            "If the browser is not logged in, show the QR code to the user.\n"
            "Always verify the contact name before typing the message."
        )

    async def execute(self, task: Task) -> TaskResult:
        self.state.status = AgentStatus.BUSY
        try:
            from playwright.async_api import async_playwright
            
            contact = task.context.get("contact", "")
            message = task.context.get("message", "")
            
            if not contact or not message:
                return TaskResult(task_id=task.task_id, status=TaskStatus.FAILED, error="Contact and message are required.")

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False) # Headful to see QR if needed
                context = await browser.new_context(user_data_dir="./data/whatsapp_session")
                page = await context.new_page()
                
                await page.goto("https://web.whatsapp.com")
                
                # Wait for login/QR or chat list
                logger.info("Waiting for WhatsApp Web to load...")
                try:
                    await page.wait_for_selector('div[contenteditable="true"]', timeout=30000)
                except:
                    return TaskResult(task_id=task.task_id, status=TaskStatus.FAILED, 
                                     output="Lütfen WhatsApp Web QR kodunu taratın. Oturum açılınca tekrar deneyin.")

                # Search for contact
                search_box = await page.wait_for_selector('div[title="Arama kutusu"]', timeout=5000)
                await search_box.click()
                await search_box.fill(contact)
                await page.keyboard.press("Enter")
                await asyncio.sleep(2)

                # Type and send
                input_box = await page.wait_for_selector('div[title="Bir mesaj yazın"]', timeout=5000)
                await input_box.click()
                await input_box.fill(message)
                await page.keyboard.press("Enter")
                
                await asyncio.sleep(1)
                await browser.close()
                
                return TaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.SUCCESS,
                    output=f"✅ Mesaj başarıyla gönderildi: {contact} -> {message}"
                )
        except Exception as e:
            logger.error(f"WhatsApp error: {e}")
            return TaskResult(task_id=task.task_id, status=TaskStatus.FAILED, error=str(e))
        finally:
            self.state.status = AgentStatus.IDLE
