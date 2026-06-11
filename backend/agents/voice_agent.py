# backend/agents/voice_agent.py
import logging
from crewai import Agent
from backend.agents.content_agent import get_ollama_llm

logger = logging.getLogger("vyaparai.agents.voice_agent")

def make_voice_agent() -> Agent:
    llm = get_ollama_llm()
    return Agent(
        role="Voice Production Engineer",
        goal="Configure and render translated marketing script texts into clear, expressive local-language voiceovers.",
        backstory="""You are an expert audio producer. You specialize in synthetic speech (TTS), vocal modulation, and pacing. 
Your goal is to ensure the marketing audio is clear, friendly, and matches the target demographic's listening preferences.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
