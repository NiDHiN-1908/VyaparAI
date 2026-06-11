# backend/agents/video_agent.py
import logging
from crewai import Agent
from backend.agents.content_agent import get_ollama_llm

logger = logging.getLogger("vyaparai.agents.video_agent")

def make_video_agent() -> Agent:
    llm = get_ollama_llm()
    return Agent(
        role="Video Post-Production Director",
        goal="Assemble images, subtitles, overlays, and regional audio tracks into premium vertical marketing videos.",
        backstory="""You are a creative director specialized in TikToks, Instagram Reels, and YouTube Shorts. 
You know how to align text overlays with audio timing, select optimal aspect ratios (9:16), and structure visually stunning sequences.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
