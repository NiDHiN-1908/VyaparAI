# backend/agents/content_agent.py
import logging
from crewai import Agent
# pyrefly: ignore [missing-import]
from langchain_openai import ChatOpenAI
from backend.config import settings

logger = logging.getLogger("vyaparai.agents.content_agent")

def get_ollama_llm() -> ChatOpenAI:
    """Helper to initialize Ollama LLM using the OpenAI-compatible endpoint."""
    model_name = settings.OLLAMA_MODEL
    if "/" not in model_name:
        model_name = f"ollama/{model_name}"
    return ChatOpenAI(
        model=model_name,
        openai_api_key="ollama",  # Placeholder key
        openai_api_base=f"{settings.OLLAMA_BASE_URL}/v1",
        temperature=0.7
    )

def make_content_agent() -> Agent:
    llm = get_ollama_llm()
    return Agent(
        role="Creative Social Media Copywriter",
        goal="""Generate engaging, platform-specific marketing content for Indian micro-businesses. 
Create scripts for YouTube (educational/promotional), Reels (short, catchy), WhatsApp (direct sale/brochure style), and Google Business (informative, local SEO optimized).""",
        backstory="""You are an expert copywriter with a decade of experience crafting high-converting ad copy for Indian local shops, manufacturers, and boutiques. 
You know how to write in a warm, welcoming, and persuasive tone that resonates with Indian buyers, blending local cultural references and clear value propositions.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
