# backend/agents/publishing_agent.py
import logging
from crewai import Agent
from backend.agents.content_agent import get_ollama_llm

logger = logging.getLogger("vyaparai.agents.publishing_agent")

def make_publishing_agent() -> Agent:
    llm = get_ollama_llm()
    return Agent(
        role="Digital Distribution Specialist",
        goal="Automate the publishing and scheduling of marketing videos and custom thumbnails to YouTube.",
        backstory="""You are an expert platform distributor. You understand metadata optimization, 
tags, schedules, and YouTube API upload structures. Your focus is to ensure the approved video 
is successfully deployed with its matching title, description, and hashtags.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
