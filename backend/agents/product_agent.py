# backend/agents/product_agent.py
import logging
from crewai import Agent
from backend.agents.content_agent import get_ollama_llm

logger = logging.getLogger("vyaparai.agents.product_agent")

def make_product_agent() -> Agent:
    llm = get_ollama_llm()
    return Agent(
        role="Horticultural Product Profile Specialist",
        goal="""Analyze plant products and descriptions to build a structured Product Context JSON with properties:
product_name, category, botanical_name, indoor_outdoor, flowering, foliage, fragrance, medicinal, air_purifying, flowering_season, sunlight, watering, soil, fertilizer, propagation, care_level, unique_features, customer_benefits, emotional_benefits, common_mistakes, FAQs, target_audience.""",
        backstory="""You are a senior botanist and plant catalog manager. 
You extract structured attributes from descriptions with 100% botanical accuracy, mapping every parameter like soil, watering, light, and benefits into a clean schema.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
