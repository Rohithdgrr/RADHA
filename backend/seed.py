"""Seed dev data for sqlite3 — run: python seed.py (no website login needed)"""
import asyncio
from app.db.base import AsyncSessionLocal
from app.models import CouncilSession, ModelResponse


async def main():
    async with AsyncSessionLocal() as session:
        # check if already seeded anon sessions
        from sqlalchemy import select

        existing = await session.execute(select(CouncilSession).limit(1))
        if existing.scalars().first():
            print("already seeded")
            return

        # No user needed — anon only (website login removed, only LMArena token matters)

        council = CouncilSession(
            user_id=None,  # anon
            user_query="What is quantum computing?",
            selected_models=["claude", "chatgpt", "gemini"],
            chairman_model="claude",
            mode="consensus",
            depth="detailed",
            show_reasoning=True,
            synthesis="Quantum computing uses qubits that can be 0 and 1 simultaneously via superposition. It promises exponential speedups for factoring, simulation, and optimization, but faces decoherence.",
            agreements="All agree on superposition and exponential potential; classical vs quantum bit distinction.",
            divergences="Gemini emphasizes error correction overhead; DeepSeek would add photonic qubits if queried.",
            unique_insights=["Photonic qubits — mentioned by DeepSeek in extended delib"],
            deliberation_log=[
                {"type": "model_start", "model": "claude", "ts": "2026-09-04T00:00:00Z"},
                {"type": "model_done", "model": "claude", "latency": 1.2, "status": "done"},
                {"type": "synthesis_start", "chairman": "claude", "ts": "2026-09-04T00:00:02Z"},
                {"type": "done", "total_latency": 4.2, "ts": "2026-09-04T00:00:04Z"},
            ],
            status="done",
            total_latency=4.2,
        )
        session.add(council)
        await session.flush()

        for model in ["claude", "chatgpt", "gemini"]:
            resp = ModelResponse(
                session_id=council.id,
                model_name=model,
                reasoning=f"Reasoning for {model}: we need to explain superposition...",
                final_answer=f"Answer from {model}: Quantum computing is ...",
                confidence=0.92 if model == "claude" else 0.85,
                latency=1.1 + len(model) * 0.1,
                status="done",
                token_count=180,
            )
            session.add(resp)

        await session.commit()
        print(f"seeded anon session {council.id} (Kimi K2.5/K3 versions ready)")


if __name__ == "__main__":
    asyncio.run(main())
