# backend/agents/comment_monitor_agent.py
import re
import logging
from backend.agents.content_agent import get_ollama_llm

logger = logging.getLogger("vyaparai.agents.comment_monitor_agent")

# Heuristics lists for fallback matching
HIGH_INTENT_KEYWORDS = [
    r"price", r"cost", r"how much", r"rate", r"buy", r"order", 
    r"available", r"delivery", r"location", r"address", r"contact",
    r"whatsapp", r"phone", r"number", r"खरीद", r"कीमत", r"कॉल", r"விலை", r"விலை என்ன",
    r"ధర", r"ఖరీదు", r"വില", r"എത്ര"
]

MEDIUM_INTENT_KEYWORDS = [
    r"nice", r"good", r"beautiful", r"great", r"super", r"wow",
    r"awesome", r"like", r"good work", r"அழகு", r"நல்லது", r"अच्छा",
    r"బాగుంది", r"നല്ലത്"
]

def classify_comment_heuristics(text: str) -> str:
    """Fallback classifier using regular expressions for local/offline testing."""
    text_lower = text.lower()
    
    for pattern in HIGH_INTENT_KEYWORDS:
        if re.search(pattern, text_lower):
            return "HIGH_INTENT"
            
    for pattern in MEDIUM_INTENT_KEYWORDS:
        if re.search(pattern, text_lower):
            return "MEDIUM_INTENT"
            
    return "SPAM"

def classify_comment(comment_text: str) -> str:
    """
    Classifies comment_text into HIGH_INTENT, MEDIUM_INTENT, or SPAM
    using Llama 3.1 via Ollama, with robust regex fallbacks.
    """
    logger.info(f"Classifying comment: '{comment_text}'")
    try:
        llm = get_ollama_llm()
        prompt = (
            "You are a Sales Intent Classifier for an Indian local retail shop. "
            "Analyze the following user comment on a social media video and classify it into one of these EXACT classes:\n"
            "- HIGH_INTENT (if the user wants to buy, asks for price, how to order, shipping details, location, phone number, or expresses urgent interest)\n"
            "- MEDIUM_INTENT (if the user praises the product, asks general questions not directly about buying, or gives positive feedback)\n"
            "- SPAM (if it is promotional, gibberish, emojis only, or completely unrelated)\n\n"
            f"Comment: \"{comment_text}\"\n\n"
            "Return ONLY the classified category name (HIGH_INTENT, MEDIUM_INTENT, or SPAM). Do not include any explanation or punctuation."
        )
        response = llm.predict(prompt)
        intent = response.strip().upper()
        
        # Clean response to ensure it maps exactly to the classes
        if "HIGH_INTENT" in intent:
            return "HIGH_INTENT"
        elif "MEDIUM_INTENT" in intent:
            return "MEDIUM_INTENT"
        elif "SPAM" in intent:
            return "SPAM"
        else:
            # If Ollama outputs something else, use heuristics
            return classify_comment_heuristics(comment_text)
            
    except Exception as e:
        logger.warning(f"Ollama comment classification failed: {e}. Utilizing regex keywords fallback.")
        return classify_comment_heuristics(comment_text)
