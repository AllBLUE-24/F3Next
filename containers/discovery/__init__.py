"""
Discovery container — Step 1 (Discovery Assistant).

Layout:
  chat_service.py       — sync chat, extraction, recommendation
  prompts.py            — LLM prompts
  phases.py             — discovery phase enum
  workflow_explanation.py — module confirmation workflow text
  mvp_scoping.py        — bottleneck → Day-1 seeds
  niche_resolver.py     — broad f3iche → niche template ID
  utils.py              — chat history helpers
  target/
    build_target.py     — target structure + MVP boundary generation
    persist.py          — Postgres + R2 persistence
    f3iche_seeds.py     — F3iche template seed helpers
"""
