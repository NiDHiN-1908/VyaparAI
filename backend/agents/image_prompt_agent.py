# backend/agents/image_prompt_agent.py
import logging
from crewai import Agent
from backend.agents.content_agent import get_ollama_llm

logger = logging.getLogger("vyaparai.agents.image_prompt_agent")

def make_image_prompt_agent() -> Agent:
    llm = get_ollama_llm()
    return Agent(
        role="AI Image Prompter",
        goal="Generate highly detailed, photorealistic visual prompts for product thumbnail layout backgrounds.",
        backstory="""You are a professional commercial photographer and prompt engineer. You excel at styling descriptive, high-quality prompts for AI image generation tools (like Midjourney, DALL-E, Stable Diffusion) using lighting direction, material texture terms, and camera lens specifications.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
