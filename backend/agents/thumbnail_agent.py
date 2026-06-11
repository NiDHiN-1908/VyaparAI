# backend/agents/thumbnail_agent.py
import logging
from crewai import Agent
from backend.agents.content_agent import get_ollama_llm

logger = logging.getLogger("vyaparai.agents.thumbnail_agent")

def make_thumbnail_agent() -> Agent:
    llm = get_ollama_llm()
    return Agent(
        role="Graphic Designer & Thumbnail Specialist",
        goal="Design high-CTR thumbnail layouts, including text overlays, layout structures, and visual generation prompts.",
        backstory="""You are a veteran YouTube thumbnail designer. You understand the psychology of visual hooks, 
contrast, font selection, and expressions that drive users to click on vertical videos and shorts.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
