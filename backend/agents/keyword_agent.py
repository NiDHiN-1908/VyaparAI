# backend/agents/keyword_agent.py
import logging
from crewai import Agent
from backend.agents.content_agent import get_ollama_llm

logger = logging.getLogger("vyaparai.agents.keyword_agent")

def make_keyword_agent() -> Agent:
    llm = get_ollama_llm()
    return Agent(
        role="SEO Keyword Strategist",
        goal="Analyze product catalogs to categorize keywords into Primary, Secondary, Long Tail, Purchase Intent, and Regional groupings.",
        backstory="""You are a senior search optimizer specialized in Indian e-commerce. 
You know how local shoppers search in Google (e.g. mixing English, Hindi, and regional phrases). 
Your output organizes terms logically to maximize purchase matching.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
