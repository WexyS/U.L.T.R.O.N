"""Reasoning Engine — Chain-of-Thought, Reflection, and Confidence Scoring.

The reasoning engine is the AGI's "thinking layer". It sits between the
orchestrator and agents, providing:

1. Chain-of-Thought (CoT): Step-by-step reasoning before action
2. Self-Reflection: Evaluate the quality of generated plans/answers
3. Confidence Scoring: Numeric assessment of plan/answer reliability
4. Multi-step Decomposition: Break complex queries into atomic steps
5. Meta-cognition: Know when it doesn't know enough and needs more info

Usage:
    engine = ReasoningEngine(llm_router, memory)
    result = await engine.reason("How do I deploy a FastAPI app to AWS?")
    print(result.final_answer)
    print(result.confidence)
    print(result.reasoning_steps)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ReasoningStrategy(str, Enum):
    """Which reasoning approach to use."""
    DIRECT = "direct"              # Simple question → simple answer
    CHAIN_OF_THOUGHT = "cot"       # Step-by-step reasoning
    TREE_OF_THOUGHT = "tot"        # Multiple reasoning paths, pick best
    SELF_REFINE = "self_refine"    # Generate → Critique → Refine loop
    PLAN_AND_SOLVE = "plan_solve"  # Create explicit plan, then solve


@dataclass
class ReasoningStep:
    """A single step in the reasoning chain."""
    step_number: int
    thought: str
    action: str = ""           # What was done (if any)
    observation: str = ""      # What was observed
    confidence: float = 0.0    # 0.0 to 1.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ReasoningResult:
    """Complete result of a reasoning session."""
    query: str
    strategy: ReasoningStrategy
    steps: list[ReasoningStep] = field(default_factory=list)
    final_answer: str = ""
    confidence: float = 0.0
    reasoning_trace: str = ""    # Human-readable trace
    metadata: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    reflection: str = ""         # Self-assessment
    needs_more_info: bool = False
    suggested_followup: list[str] = field(default_factory=list)


class ReasoningEngine:
    """Core reasoning engine for AGI-level thinking.

    This engine provides multi-strategy reasoning, self-reflection,
    and confidence assessment to elevate Ultron's cognitive capabilities
    beyond simple prompt→response patterns.
    """

    def __init__(
        self,
        llm_router,
        memory=None,
        max_reasoning_steps: int = 8,
        reflection_threshold: float = 0.6,
    ) -> None:
        self.llm_router = llm_router
        self.memory = memory
        self.max_reasoning_steps = max_reasoning_steps
        self.reflection_threshold = reflection_threshold

        # Statistics
        self._total_reasoning_sessions = 0
        self._avg_confidence = 0.0

    # ── Public API ───────────────────────────────────────────────────────

    async def reason(
        self,
        query: str,
        context: Optional[dict] = None,
        strategy: Optional[ReasoningStrategy] = None,
    ) -> ReasoningResult:
        """Main entry point: reason about a query and return a structured result.

        If no strategy is specified, the engine auto-selects the best one
        based on query complexity.
        """
        import time
        start = time.monotonic()

        # Auto-select strategy if not specified
        if strategy is None:
            strategy = await self._select_strategy(query)

        logger.info("Reasoning with strategy: %s for query: %s", strategy.value, query[:80])

        # Execute the selected strategy
        if strategy == ReasoningStrategy.DIRECT:
            result = await self._reason_direct(query, context)
        elif strategy == ReasoningStrategy.CHAIN_OF_THOUGHT:
            result = await self._reason_cot(query, context)
        elif strategy == ReasoningStrategy.TREE_OF_THOUGHT:
            result = await self._reason_tot(query, context)
        elif strategy == ReasoningStrategy.SELF_REFINE:
            result = await self._reason_self_refine(query, context)
        elif strategy == ReasoningStrategy.PLAN_AND_SOLVE:
            result = await self._reason_plan_and_solve(query, context)
        else:
            result = await self._reason_direct(query, context)

        # Self-reflection if confidence is below threshold
        if result.confidence < self.reflection_threshold:
            result = await self._reflect_and_improve(result)

        result.duration_ms = (time.monotonic() - start) * 1000

        # Update statistics
        self._total_reasoning_sessions += 1
        self._avg_confidence = (
            (self._avg_confidence * (self._total_reasoning_sessions - 1) + result.confidence)
            / self._total_reasoning_sessions
        )

        # Store in memory if available
        if self.memory:
            self._store_reasoning(result)

        return result

    # ── Strategy Selection ───────────────────────────────────────────────

    async def _select_strategy(self, query: str) -> ReasoningStrategy:
        """Auto-select the best reasoning strategy for a given query."""
        messages = [
            {"role": "system", "content": (
                "You are a meta-reasoning system. Given a user query, determine the best reasoning strategy.\n"
                "Options:\n"
                "- direct: Simple factual questions, greetings, or straightforward requests\n"
                "- cot: Questions requiring step-by-step logical reasoning\n"
                "- tot: Complex problems with multiple possible approaches\n"
                "- self_refine: Creative tasks where iterative improvement helps\n"
                "- plan_solve: Multi-step tasks requiring explicit planning\n\n"
                "Return ONLY one word: direct, cot, tot, self_refine, or plan_solve"
            )},
            {"role": "user", "content": query},
        ]

        try:
            response = await self.llm_router.chat(messages, temperature=0.1, max_tokens=20)
            strategy_name = response.content.strip().lower().replace("_", "_")

            strategy_map = {
                "direct": ReasoningStrategy.DIRECT,
                "cot": ReasoningStrategy.CHAIN_OF_THOUGHT,
                "tot": ReasoningStrategy.TREE_OF_THOUGHT,
                "self_refine": ReasoningStrategy.SELF_REFINE,
                "plan_solve": ReasoningStrategy.PLAN_AND_SOLVE,
            }

            return strategy_map.get(strategy_name, ReasoningStrategy.CHAIN_OF_THOUGHT)
        except Exception:
            # Default to CoT if strategy selection fails
            return ReasoningStrategy.CHAIN_OF_THOUGHT

    # ── Strategy Implementations ─────────────────────────────────────────

    async def _reason_direct(self, query: str, context: Optional[dict] = None) -> ReasoningResult:
        """Direct response — no multi-step reasoning needed."""
        messages = [
            {"role": "system", "content": (
                "You are a highly capable AI assistant. Provide a clear, accurate, and helpful response."
            )},
            {"role": "user", "content": query},
        ]

        response = await self.llm_router.chat(messages, temperature=0.3, max_tokens=2048)

        return ReasoningResult(
            query=query,
            strategy=ReasoningStrategy.DIRECT,
            steps=[ReasoningStep(step_number=1, thought="Direct response", confidence=0.8)],
            final_answer=response.content,
            confidence=0.8,
            reasoning_trace="Direct response — no multi-step reasoning required.",
        )

    async def _reason_cot(self, query: str, context: Optional[dict] = None) -> ReasoningResult:
        """Chain-of-Thought reasoning — step by step."""
        # Gather lesson context from memory
        lesson_context = ""
        if self.memory:
            try:
                lesson_context = self.memory.get_lesson_context(query)
            except Exception:
                pass

        cot_prompt = (
            "You are an expert reasoning system. Think through this problem step by step.\n\n"
            "RULES:\n"
            "1. Break the problem into clear logical steps\n"
            "2. For each step, show your reasoning\n"
            "3. If you're uncertain about a step, say so\n"
            "4. At the end, provide a final answer and confidence score (0.0-1.0)\n\n"
            "FORMAT your response as:\n"
            "Step 1: [thought]\n"
            "Step 2: [thought]\n"
            "...\n"
            "FINAL ANSWER: [your answer]\n"
            "CONFIDENCE: [0.0-1.0]\n"
        )

        if lesson_context:
            cot_prompt += f"\nRelevant lessons from past experience:\n{lesson_context}\n"

        messages = [
            {"role": "system", "content": cot_prompt},
            {"role": "user", "content": query},
        ]

        response = await self.llm_router.chat(messages, temperature=0.3, max_tokens=4096)

        # Parse the CoT response
        steps, final_answer, confidence = self._parse_cot_response(response.content)

        return ReasoningResult(
            query=query,
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
            steps=steps,
            final_answer=final_answer,
            confidence=confidence,
            reasoning_trace=response.content,
        )

    async def _reason_tot(self, query: str, context: Optional[dict] = None) -> ReasoningResult:
        """Tree-of-Thought — explore multiple reasoning paths, pick the best."""
        # Generate 3 different reasoning paths
        paths = []
        for i in range(3):
            path_prompt = (
                f"You are reasoning path #{i+1}/3. Think through this problem from a unique angle.\n"
                f"Be creative and consider different approaches. Show your reasoning step by step.\n"
                f"At the end: FINAL ANSWER: [answer]\nCONFIDENCE: [0.0-1.0]"
            )

            messages = [
                {"role": "system", "content": path_prompt},
                {"role": "user", "content": query},
            ]

            response = await self.llm_router.chat(messages, temperature=0.5 + (i * 0.15), max_tokens=2048)
            steps, answer, conf = self._parse_cot_response(response.content)
            paths.append({"steps": steps, "answer": answer, "confidence": conf, "trace": response.content})

        # Evaluate paths — pick the best one using a judge prompt
        evaluation_prompt = (
            "You are a reasoning evaluator. Compare these different reasoning paths and select the BEST one.\n"
            "Consider: accuracy, completeness, logical soundness, and confidence.\n\n"
        )
        for i, path in enumerate(paths):
            evaluation_prompt += f"--- Path {i+1} (confidence={path['confidence']:.2f}) ---\n"
            evaluation_prompt += f"{path['trace'][:500]}\n\n"

        evaluation_prompt += (
            "Return ONLY a JSON object: {\"best_path\": 1|2|3, \"reason\": \"why this path is best\"}"
        )

        messages = [
            {"role": "system", "content": "You are an objective reasoning evaluator."},
            {"role": "user", "content": evaluation_prompt},
        ]

        try:
            eval_response = await self.llm_router.chat(messages, temperature=0.1, max_tokens=200)
            json_match = re.search(r'\{[^}]+\}', eval_response.content)
            if json_match:
                eval_data = json.loads(json_match.group())
                best_idx = int(eval_data.get("best_path", 1)) - 1
                best_idx = max(0, min(best_idx, len(paths) - 1))
            else:
                best_idx = max(range(len(paths)), key=lambda i: paths[i]["confidence"])
        except Exception:
            best_idx = max(range(len(paths)), key=lambda i: paths[i]["confidence"])

        best = paths[best_idx]
        return ReasoningResult(
            query=query,
            strategy=ReasoningStrategy.TREE_OF_THOUGHT,
            steps=best["steps"],
            final_answer=best["answer"],
            confidence=best["confidence"],
            reasoning_trace=best["trace"],
            metadata={"paths_explored": len(paths), "selected_path": best_idx + 1},
        )

    async def _reason_self_refine(self, query: str, context: Optional[dict] = None) -> ReasoningResult:
        """Self-refine — generate, critique, improve."""
        # Step 1: Initial generation
        messages = [
            {"role": "system", "content": "Provide a thoughtful, comprehensive response."},
            {"role": "user", "content": query},
        ]
        initial = await self.llm_router.chat(messages, temperature=0.4, max_tokens=2048)

        # Step 2: Self-critique
        critique_messages = [
            {"role": "system", "content": (
                "You are a critical reviewer. Analyze this response for:\n"
                "1. Accuracy — are there any factual errors?\n"
                "2. Completeness — is anything missing?\n"
                "3. Clarity — is it easy to understand?\n"
                "4. Actionability — can the user act on this?\n\n"
                "List specific improvements needed. Return JSON:\n"
                "{\"score\": 0.0-1.0, \"issues\": [\"issue1\", ...], \"improvements\": [\"fix1\", ...]}"
            )},
            {"role": "user", "content": f"Original query: {query}\n\nResponse to review:\n{initial.content}"},
        ]
        critique = await self.llm_router.chat(critique_messages, temperature=0.2, max_tokens=1024)

        # Parse critique
        score = 0.7
        issues = []
        try:
            json_match = re.search(r'\{[\s\S]*\}', critique.content)
            if json_match:
                critique_data = json.loads(json_match.group())
                score = float(critique_data.get("score", 0.7))
                issues = critique_data.get("issues", [])
        except Exception:
            pass

        # Step 3: Refine based on critique (if score < 0.8)
        if score < 0.8 and issues:
            refine_messages = [
                {"role": "system", "content": (
                    "Improve this response based on the following critique. "
                    "Keep what's good, fix what's wrong. Provide the IMPROVED response only."
                )},
                {"role": "user", "content": (
                    f"Original query: {query}\n\n"
                    f"Original response:\n{initial.content}\n\n"
                    f"Issues found:\n" + "\n".join(f"- {i}" for i in issues)
                )},
            ]
            refined = await self.llm_router.chat(refine_messages, temperature=0.3, max_tokens=2048)
            final_answer = refined.content
            confidence = min(score + 0.15, 0.95)  # Improvement boost
        else:
            final_answer = initial.content
            confidence = score

        steps = [
            ReasoningStep(step_number=1, thought="Initial generation", confidence=score),
            ReasoningStep(step_number=2, thought=f"Self-critique: {len(issues)} issues found", confidence=score),
        ]
        if score < 0.8 and issues:
            steps.append(ReasoningStep(step_number=3, thought="Refined based on critique", confidence=confidence))

        return ReasoningResult(
            query=query,
            strategy=ReasoningStrategy.SELF_REFINE,
            steps=steps,
            final_answer=final_answer,
            confidence=confidence,
            reasoning_trace=f"Initial score: {score}, Issues: {issues}",
            reflection=critique.content,
        )

    async def _reason_plan_and_solve(self, query: str, context: Optional[dict] = None) -> ReasoningResult:
        """Plan-and-Solve — create explicit plan, then execute each step."""
        # Step 1: Create plan
        plan_messages = [
            {"role": "system", "content": (
                "You are a planning specialist. Given a task, create a clear execution plan.\n"
                "Return a JSON array of steps:\n"
                "[{\"step\": 1, \"action\": \"what to do\", \"expected_output\": \"what we expect\"}, ...]"
            )},
            {"role": "user", "content": query},
        ]
        plan_response = await self.llm_router.chat(plan_messages, temperature=0.2, max_tokens=1024)

        # Parse plan
        plan_steps = []
        try:
            json_match = re.search(r'\[[\s\S]*\]', plan_response.content)
            if json_match:
                plan_steps = json.loads(json_match.group())
        except Exception:
            plan_steps = [{"step": 1, "action": query, "expected_output": "Complete response"}]

        # Step 2: Execute each plan step
        reasoning_steps = []
        accumulated_context = ""

        for i, plan_step in enumerate(plan_steps[:self.max_reasoning_steps]):
            step_messages = [
                {"role": "system", "content": (
                    f"You are executing step {i+1} of a plan.\n"
                    f"Previous context: {accumulated_context[:1000] if accumulated_context else 'None'}\n"
                    f"Execute this step and provide the result."
                )},
                {"role": "user", "content": plan_step.get("action", query)},
            ]
            step_response = await self.llm_router.chat(step_messages, temperature=0.3, max_tokens=1024)

            reasoning_steps.append(ReasoningStep(
                step_number=i + 1,
                thought=plan_step.get("action", ""),
                observation=step_response.content[:500],
                confidence=0.7,
            ))
            accumulated_context += f"\nStep {i+1} result: {step_response.content[:300]}"

        # Step 3: Synthesize final answer
        synthesis_messages = [
            {"role": "system", "content": (
                "Synthesize the results of all executed steps into a coherent final answer."
            )},
            {"role": "user", "content": (
                f"Original question: {query}\n\n"
                f"Execution results:\n{accumulated_context}"
            )},
        ]
        synthesis = await self.llm_router.chat(synthesis_messages, temperature=0.3, max_tokens=2048)

        return ReasoningResult(
            query=query,
            strategy=ReasoningStrategy.PLAN_AND_SOLVE,
            steps=reasoning_steps,
            final_answer=synthesis.content,
            confidence=0.75,
            reasoning_trace=f"Plan: {len(plan_steps)} steps, Executed: {len(reasoning_steps)}",
            metadata={"plan": plan_steps},
        )

    # ── Reflection ───────────────────────────────────────────────────────

    async def _reflect_and_improve(self, result: ReasoningResult) -> ReasoningResult:
        """Self-reflect on a low-confidence result and try to improve it."""
        messages = [
            {"role": "system", "content": (
                "You are a meta-cognitive evaluator. Review this reasoning and answer.\n"
                "Identify weaknesses and provide an improved answer if possible.\n"
                "Also identify: do we need more information to answer properly?\n\n"
                "Return JSON:\n"
                "{\n"
                "  \"improved_answer\": \"better answer or empty if original is fine\",\n"
                "  \"new_confidence\": 0.0-1.0,\n"
                "  \"needs_more_info\": true/false,\n"
                "  \"suggested_followup\": [\"question to ask user\", ...],\n"
                "  \"reflection\": \"assessment of reasoning quality\"\n"
                "}"
            )},
            {"role": "user", "content": (
                f"Query: {result.query}\n"
                f"Strategy: {result.strategy.value}\n"
                f"Answer: {result.final_answer[:1000]}\n"
                f"Confidence: {result.confidence}"
            )},
        ]

        try:
            response = await self.llm_router.chat(messages, temperature=0.2, max_tokens=2048)
            json_match = re.search(r'\{[\s\S]*\}', response.content)
            if json_match:
                reflection_data = json.loads(json_match.group())

                improved = reflection_data.get("improved_answer", "")
                if improved and len(improved) > 10:
                    result.final_answer = improved

                result.confidence = float(reflection_data.get("new_confidence", result.confidence))
                result.needs_more_info = reflection_data.get("needs_more_info", False)
                result.suggested_followup = reflection_data.get("suggested_followup", [])
                result.reflection = reflection_data.get("reflection", "")

                result.steps.append(ReasoningStep(
                    step_number=len(result.steps) + 1,
                    thought="Self-reflection and improvement",
                    observation=result.reflection,
                    confidence=result.confidence,
                ))
        except Exception as e:
            logger.warning("Reflection failed: %s", e)

        return result

    # ── Parsing Helpers ──────────────────────────────────────────────────

    def _parse_cot_response(self, content: str) -> tuple[list[ReasoningStep], str, float]:
        """Parse a Chain-of-Thought formatted response."""
        steps = []
        final_answer = content
        confidence = 0.7

        # Extract steps
        step_pattern = re.compile(r'(?:Step\s+(\d+)[:\.]?\s*)(.*?)(?=Step\s+\d+|FINAL\s+ANSWER|CONFIDENCE|$)', re.DOTALL | re.IGNORECASE)
        for match in step_pattern.finditer(content):
            step_num = int(match.group(1))
            thought = match.group(2).strip()
            if thought:
                steps.append(ReasoningStep(step_number=step_num, thought=thought))

        # Extract final answer
        answer_match = re.search(r'FINAL\s+ANSWER\s*:\s*(.*?)(?=CONFIDENCE|$)', content, re.DOTALL | re.IGNORECASE)
        if answer_match:
            final_answer = answer_match.group(1).strip()

        # Extract confidence
        conf_match = re.search(r'CONFIDENCE\s*:\s*([\d.]+)', content, re.IGNORECASE)
        if conf_match:
            try:
                confidence = float(conf_match.group(1))
                confidence = max(0.0, min(1.0, confidence))
            except ValueError:
                pass

        # If no steps were found, create a single step
        if not steps:
            steps = [ReasoningStep(step_number=1, thought=content[:200], confidence=confidence)]

        # Set confidence on all steps
        for step in steps:
            if step.confidence == 0.0:
                step.confidence = confidence

        return steps, final_answer, confidence

    # ── Memory Integration ───────────────────────────────────────────────

    def _store_reasoning(self, result: ReasoningResult) -> None:
        """Store reasoning result in memory for future reference."""
        try:
            self.memory.store(
                entry_id=f"reasoning_{int(datetime.now().timestamp())}",
                content=(
                    f"Query: {result.query}\n"
                    f"Strategy: {result.strategy.value}\n"
                    f"Confidence: {result.confidence:.2f}\n"
                    f"Answer: {result.final_answer[:500]}"
                ),
                entry_type="episodic",
                metadata={
                    "type": "reasoning",
                    "strategy": result.strategy.value,
                    "confidence": result.confidence,
                    "steps": len(result.steps),
                },
            )
        except Exception as e:
            logger.debug("Failed to store reasoning: %s", e)

    # ── Statistics ───────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        return {
            "total_sessions": self._total_reasoning_sessions,
            "avg_confidence": round(self._avg_confidence, 3),
            "max_steps": self.max_reasoning_steps,
            "reflection_threshold": self.reflection_threshold,
        }
