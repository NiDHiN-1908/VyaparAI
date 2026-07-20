# backend/agents/research_agent.py
import logging
from crewai import Agent
from backend.agents.content_agent import get_ollama_llm

logger = logging.getLogger("vyaparai.agents.research_agent")

def make_research_agent() -> Agent:
    llm = get_ollama_llm()
    return Agent(
        role="Nursery Research & Botanical Fact Checker",
        goal="""Take a structured Product Context and enrich it with verified botanical facts and RAG research details.
Ensure no cross-plant details are introduced. Only keep facts specific to the target plant.""",
        backstory="""You are a horticultural researcher and fact checker. 
You cross-reference plant care information with local databases, ensuring that specific requirements (like humidity for Orchids or fragrance details for Jasmine) are fully detailed, verified, and completely isolated from other products.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
