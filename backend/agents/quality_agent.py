# backend/agents/quality_agent.py
import logging
from typing import Dict, Any
from crewai import Agent
from backend.agents.content_agent import get_ollama_llm

logger = logging.getLogger("vyaparai.agents.quality_agent")

def make_quality_agent() -> Agent:
    llm = get_ollama_llm()
    return Agent(
        role="Asset Quality Assurance Inspector",
        goal="Audit marketing scripts, thumbnail layouts, and titles to evaluate compliance and assign a score out of 100.",
        backstory="""You are a strict QA manager. You verify that marketing campaigns satisfy brand safety, 
grammar, keyword SEO coverage, readability, and script length. If the score drops below 80, you flag it for regeneration.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

def audit_campaign_quality(script_data: Dict[str, Any], keywords: list) -> Dict[str, Any]:
    """
    Programmatically audits script and keyword parameters.
    Returns score and status (APPROVED / REGENERATE).
    """
    logger.info("Executing program quality audit...")
    score = 85  # Default passing score
    feedback = []

    # Quality check heuristics
    if len(script_data.get("title", "")) < 10:
        score -= 10
        feedback.append("Title is too short. Needs more clickability.")
        
    if not script_data.get("hook", ""):
        score -= 15
        feedback.append("Script is missing a dedicated hook section.")
        
    if len(script_data.get("script_text", "")) < 100:
        score -= 15
        feedback.append("Script content is too sparse to compile a video.")

    # Check keyword coverage
    covered_kws = 0
    script_lower = script_data.get("script_text", "").lower()
    for kw in keywords:
        if kw.lower() in script_lower:
            covered_kws += 1
            
    if covered_kws < 2:
        score -= 15
        feedback.append("Low SEO keyword density in script text.")

    status = "APPROVED" if score >= 80 else "REGENERATE"
    logger.info(f"QA Audit completed. Score: {score}/100. Status: {status}")

    return {
        "score": score,
        "status": status,
        "feedback": " | ".join(feedback) if feedback else "Assets passed quality standard."
    }
