# backend/agents/script_agent.py
import logging
from crewai import Agent
from backend.agents.content_agent import get_ollama_llm

logger = logging.getLogger("vyaparai.agents.script_agent")

def make_script_agent() -> Agent:
    llm = get_ollama_llm()
    return Agent(
        role="Master Product Copywriter & Screenplay Director",
        goal="""1. ACT LIKE A PROFESSIONAL: Deeply analyze the specific product identity, target audience, and unique selling proposition (USP).
2. STRATEGIZE THE SALE: Identify the emotional or practical trigger that will make people buy this exact item.
3. INNOVATE: Generate highly creative, completely unique, and diverse dialogue/scripts for every video. NEVER repeat the same script template.
4. DELIVER JSON: Output a strict, valid JSON bundle containing your innovative Hook, Problem, Solution, Scene breakdown, Voiceovers, and Subtitles.""",
        backstory="""You are a world-class advertising executive and creative genius. You never use generic templates. 
When given a product, you instantly recognize its core appeal and how to sell it. You craft wildly innovative, emotional, and catchy viral short-form commercials tailored exclusively to that specific product's unique traits.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
