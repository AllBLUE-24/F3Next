"""Discovery LLM prompts — one module per job."""

from containers.discovery.prompts.chat import ADI_CHAT_SYSTEM_PROMPT, OPENING_MESSAGE
from containers.discovery.prompts.extract import TRANSCRIPT_EXTRACTION_PROMPT
from containers.discovery.prompts.niche import NICHE_RESOLUTION_PROMPT
from containers.discovery.prompts.planner import MVP_PLANNER_PROMPT, MVP_PLANNER_REVISION_PROMPT
from containers.discovery.prompts.recommend import RECOMMENDATION_PROMPT
from containers.discovery.prompts.workflow import WORKFLOW_EXPLANATION_PROMPT

# Backward-compatible aliases
ADI_SYSTEM_PROMPT = ADI_CHAT_SYSTEM_PROMPT
DISCOVERY_TURN_PROMPT = ""
DISCOVERY_PROMPT = DISCOVERY_TURN_PROMPT

__all__ = [
    "OPENING_MESSAGE",
    "ADI_CHAT_SYSTEM_PROMPT",
    "ADI_SYSTEM_PROMPT",
    "TRANSCRIPT_EXTRACTION_PROMPT",
    "NICHE_RESOLUTION_PROMPT",
    "RECOMMENDATION_PROMPT",
    "MVP_PLANNER_PROMPT",
    "MVP_PLANNER_REVISION_PROMPT",
    "WORKFLOW_EXPLANATION_PROMPT",
    "DISCOVERY_TURN_PROMPT",
    "DISCOVERY_PROMPT",
]
