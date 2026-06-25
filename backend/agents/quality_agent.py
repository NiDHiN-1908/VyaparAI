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

def audit_campaign_quality(script_data: Dict[str, Any], keywords: list, product_name: str = "") -> Dict[str, Any]:
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

    # STRICT CONTENT VALIDATION RULES FOR NON-FOOD PRODUCTS
    # Identify if product is food/agri based strictly on product name if provided, to avoid circular validation bypasses.
    name_lower = product_name.lower() if product_name else ""
    
    non_food_kws = [
        "paint", "coating", "emulsion", "varnish", "primer", "acrylic", "wall painting",
        "phone", "laptop", "battery", "led", "screen", "sensor", "camera", "headphone", "device", "charge", "electronics",
        "saree", "shirt", "pant", "shoe", "dress", "clothing", "fabric", "silk", "cotton", "wear", "fashion",
        "table", "chair", "sofa", "desk", "bed", "furniture", "woodwork", "cabinet",
        "cream", "lotion", "serum", "lipstick", "soap", "shampoo", "beauty", "cosmetic", "skincare",
        "car", "bike", "engine", "motor", "tyre", "automotive", "vehicle", "brake",
        "software", "app", "saas", "dashboard", "platform", "database", "crm", "automation",
        "medicine", "tablet", "health", "clinical", "capsule", "doctor", "care", "supplement"
    ]
    
    food_kws = [
        "cardamom", "coconut", "oil", "food", "beverage", "tea", "coffee", "spice", 
        "honey", "juice", "fresh", "organic", "farm", "harvest", "fruit", "vegetable",
        "agriculture", "farming", "gardening", "produce", "meat", "dairy", "spices", "elaichi"
    ]

    is_food_or_agri = True
    if name_lower:
        if any(kw in name_lower for kw in non_food_kws):
            is_food_or_agri = False
        elif any(kw in name_lower for kw in food_kws):
            is_food_or_agri = True
        else:
            # Fallback to checking title/script text ONLY if name is not classified
            combined_text = (script_data.get("title", "") + " " + script_data.get("script_text", "")).lower()
            if any(kw in combined_text for kw in non_food_kws):
                is_food_or_agri = False
            else:
                is_food_or_agri = any(kw in combined_text for kw in food_kws)
    else:
        # Fallback for unit tests where product_name might be empty
        combined_text = (script_data.get("title", "") + " " + script_data.get("script_text", "")).lower()
        if any(kw in combined_text for kw in non_food_kws):
            is_food_or_agri = False
        else:
            is_food_or_agri = any(kw in combined_text for kw in food_kws)
    
    if not is_food_or_agri:
        forbidden_words = [
            "farmer", "farmers", "farm", "farm fresh", "fresh from farms", "harvested",
            "handpicked", "locally grown", "vacuum sealed", "fresh delivery", 
            "preservative free", "organic produce", "straight from farms", 
            "freshly picked", "fresh stock", "chemical free food"
        ]
        
        script_lower_all = (
            script_data.get("script_text", "").lower() + " " + 
            script_data.get("hook", "").lower() + " " + 
            script_data.get("title", "").lower() + " " + 
            script_data.get("seo_description", "").lower()
        )
        
        found_forbidden = []
        for word in forbidden_words:
            if word in script_lower_all:
                found_forbidden.append(word)
                
        if found_forbidden:
            score = 0
            feedback.append(f"CRITICAL ERROR: Prohibited cross-category terms found for non-food product: {', '.join(found_forbidden)}")

    status = "APPROVED" if score >= 80 else "REGENERATE"
    logger.info(f"QA Audit completed. Score: {score}/100. Status: {status}")

    return {
        "score": score,
        "status": status,
        "feedback": " | ".join(feedback) if feedback else "Assets passed quality standard."
    }
