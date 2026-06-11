# backend/agents/script_agent.py
import logging
from crewai import Agent
from backend.agents.content_agent import get_ollama_llm

logger = logging.getLogger("vyaparai.agents.script_agent")

def make_script_agent() -> Agent:
    llm = get_ollama_llm()
    return Agent(
        role="Copywriter & Screenplay Director",
        goal="""Generate complete marketing video script bundles containing Hooks, Objections, Call To Actions, 
detailed scene instructions, voiceovers, subtitle timelines, titles, and SEO tags.""",
        backstory="""You are an award-winning ad director. You specialize in viral short-form commercials. 
You know how to structure the hook in the first 3 seconds, build a clear problem/solution bridge, and list product benefits in a highly engaging voice.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
