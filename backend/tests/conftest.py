# backend/tests/conftest.py
import pytest
import re
from unittest.mock import MagicMock, patch
import langchain_openai
from backend.modules.video_monitoring_module import video_monitoring_svc as youtube_monitor_svc

def mock_invoke_side_effect(prompt, *args, **kwargs):
    prompt_str = str(prompt)
    print(f"\n--- DEBUG PROMPT --- Length: {len(prompt_str)}\n{prompt_str[:250]}\n--------------------\n")
    
    # Dynamically extract the product name from the prompt to customize the mock response
    product_name = "Mock Plant"
    match = re.search(r"product:\s*'([^']+)'", prompt_str, re.IGNORECASE)
    if not match:
        match = re.search(r"product name:\s*'([^']+)'", prompt_str, re.IGNORECASE)
    if not match:
        match = re.search(r"plant product:\s*'([^']+)'", prompt_str, re.IGNORECASE)
    if not match:
        match = re.search(r"for product:\s*'([^']+)'", prompt_str, re.IGNORECASE)
    if match:
        product_name = match.group(1)
        
    mock_response = MagicMock()
    
    # Identify type of prompt and return appropriate mock structured JSON
    if "Product Context" in prompt_str or "Horticultural Product Profile" in prompt_str or "plant characteristics" in prompt_str:
        # Customize characteristics based on the matched plant name
        category = "Foliage"
        flowering = "false"
        fragrance = "false"
        medicinal = "false"
        unique_features = "[\"Air purifying\"]"
        benefits = "[\"Beautifies your home\"]"
        
        if "aloe" in product_name.lower():
            category = "Succulent / Medicinal / Low Maintenance"
            medicinal = "true"
            unique_features = "[\"Highly drought-tolerant\", \"Gel-filled leaves\"]"
            benefits = "[\"Natural skin care gel\", \"Soothing minor burns\"]"
        elif "jasmine" in product_name.lower():
            category = "Outdoor / Climber / Flowering / Fragrance"
            flowering = "true"
            fragrance = "true"
            unique_features = "[\"Starry white flowers\", \"Calming night bloom\"]"
            benefits = "[\"Intense sweet evening fragrance\", \"Anxiety-reducing aroma\"]"
            
        mock_response.content = f"""```json
{{
  "product_name": "{product_name}",
  "category": "{category}",
  "botanical_name": "{product_name} barbadensis",
  "indoor_outdoor": "Indoor/Outdoor",
  "flowering": {flowering},
  "foliage": true,
  "fragrance": {fragrance},
  "medicinal": {medicinal},
  "air_purifying": true,
  "flowering_season": "Summer",
  "sunlight": "Bright indirect light",
  "watering": "Low to moderate",
  "soil": "Well-draining mix",
  "fertilizer": "Organic monthly",
  "propagation": "Stem cuttings",
  "care_level": "Easy",
  "unique_features": {unique_features},
  "customer_benefits": {benefits},
  "emotional_benefits": "Brings joy and calm",
  "common_mistakes": "Overwatering",
  "FAQs": "How often to water? When dry.",
  "target_audience": "Home gardeners"
}}
```"""
    elif "Enrich the following Product Context" in prompt_str:
        mock_response.content = f"""```json
{{
  "product_name": "{product_name}",
  "category": "Flowering",
  "botanical_name": "{product_name} barbadensis",
  "indoor_outdoor": "Indoor/Outdoor",
  "flowering": true,
  "foliage": true,
  "fragrance": true,
  "medicinal": true,
  "air_purifying": true,
  "flowering_season": "Summer",
  "sunlight": "Bright indirect light",
  "watering": "Low to moderate",
  "soil": "Well-draining mix",
  "fertilizer": "Organic monthly",
  "propagation": "Stem cuttings",
  "care_level": "Easy",
  "unique_features": ["Enriched features"],
  "customer_benefits": ["Enriched benefits"],
  "emotional_benefits": "Joyful focus",
  "common_mistakes": "Overwatering",
  "FAQs": "Water when dry.",
  "target_audience": "Home gardeners"
}}
```"""
    elif "promotional script bundle" in prompt_str or "video script" in prompt_str or "expert botanical copywriter" in prompt_str or "Writing Screenplay" in prompt_str:
        MOCK_SCRIPTS = {
            "rose": "The majestic Rose Plant is a symbol of beauty. Ensure it gets plenty of direct sunlight for maximum blooms. Water deep in the soil and prune in early spring. Attracts bees and butterflies to your garden.",
            "aloe": "Aloe Vera is the ultimate healing succulent. The soothing gel from its thick leaves works wonders for skin care and minor burns. Thrives in dry soil and bright indirect light. Propagates easily from pups.",
            "snake": "Known as the bedroom champion, the Snake Plant filters toxins and produces oxygen at night. NASA recommended for air purification. Needs water only once a month and handles low light perfectly.",
            "money": "Bring positive Feng Shui energy with a Money Plant. This lush climber propagation is easy in water jars or soil pots with moss sticks. Thrives in indirect light and brings prosperity to your home.",
            "orchid": "Exquisite orchids feature unique air roots and love humidity. Do not plant in regular soil; use pine bark. Their exotic luxury blooms last for weeks under bright filtered morning sun.",
            "jasmine": "Experience the sweet fragrance of climbing Jasmine flowers in the night. Perfect for trellis or balcony display. Calming essential oils are known to reduce anxiety and stress.",
            "bonsai": "Bonsai is the traditional Japanese art of cultivating miniature trees. Focus on careful wiring and pruning for Zen mindfulness, balance, and harmony. A beautiful living sculpture.",
            "areca": "The Areca Palm is a pet safe golden cane humidifier and air purifier. Its tropical green fronds filter gaseous toxins. Keep soil moist and place in bright indirect light.",
            "peace": "Peace Lily spathes show beautiful white flowers that filter mold spores. It droops its hooded leaves dramatically when thirsty, loving shade and low indoor light.",
            "cactus": "This desert Cactus succulent thrives on neglect. Features beautiful defensive needles and spines. Needs gritty well-draining sandy soil, intense bright sun, and minimal water."
        }
        matched_script = "This is a generic healthy plant script. Make sure to water it and care for it."
        for k, v in MOCK_SCRIPTS.items():
            if k in product_name.lower():
                matched_script = v
                break
                
        import random
        cta_phrase = random.choice([
            "Comment the word 'Link' below to get the details!",
            "Comment 'Link' below to view our online catalog!",
            "Drop a comment saying 'Link' below to get our direct catalog link!",
            "Want our secret high-bloom checklist? Comment the word 'Link' below!"
        ])
        full_script = f"Hey plant lovers! {matched_script} {cta_phrase}"
        mock_response.content = f"""```json
{{
  "title": "Secrets of {product_name}!",
  "hook": "Stop watering your {product_name} like this!",
  "script_text": "{full_script}",
  "scene_breakdown": [
    {{
      "scene": 1,
      "instruction": "Show {product_name}",
      "voiceover": "Hey plant lovers! {matched_script}"
    }},
    {{
      "scene": 2,
      "instruction": "Show catalog",
      "voiceover": "{cta_phrase}"
    }}
  ],
  "caption_timeline": [
    {{
      "start": 0.0,
      "end": 6.0,
      "text": "Hey plant lovers! {matched_script}"
    }},
    {{
      "start": 6.0,
      "end": 10.0,
      "text": "{cta_phrase}"
    }}
  ],
  "thumbnail_text": "Grow {product_name}!",
  "seo_description": "Learn to care for your {product_name}.",
  "hashtags": ["#{product_name.replace(' ', '')}", "#PlantCare"]
}}
```"""
    elif "Keyword" in prompt_str or "SEO" in prompt_str:
        mock_response.content = f"""```json
{{
  "primary": ["{product_name}", "buy {product_name}"],
  "secondary": ["home decor", "gardening"],
  "long_tail": ["best {product_name} in india"],
  "intent": ["order {product_name}"],
  "regional": ["{product_name} mumbai"]
}}
```"""
    elif "thumbnail" in prompt_str or "high-CTR" in prompt_str:
        mock_response.content = """```json
{
  "layout": "Centered layout with bold yellow text overlay",
  "text": "Grow now!",
  "prompt": "Stunning photo of plant"
}
```"""
    elif "ImagePromptAgent" in prompt_str or "image generator prompt" in prompt_str:
        mock_response.content = "Stunning close up photo of plant in a wooden stand, soft warm lighting, 8k"
    else:
        # Default fallback JSON containing generic structured keys
        mock_response.content = f"""```json
{{
  "title": "Secrets of {product_name}!",
  "hook": "Stop watering your {product_name} like this!",
  "script_text": "This beautiful {product_name} has amazing features. Comment the word 'Link' below to get the details!",
  "scene_breakdown": [
    {{
      "scene": 1,
      "instruction": "Show {product_name}",
      "voiceover": "This beautiful {product_name} has amazing features."
    }},
    {{
      "scene": 2,
      "instruction": "Show catalog",
      "voiceover": "Comment the word 'Link' below to get the details!"
    }}
  ],
  "caption_timeline": [
    {{
      "start": 0.0,
      "end": 3.0,
      "text": "This beautiful {product_name} has amazing features."
    }},
    {{
      "start": 3.0,
      "end": 6.0,
      "text": "Comment the word 'Link' below to get the details!"
    }}
  ],
  "thumbnail_text": "Grow {product_name}!",
  "seo_description": "Learn to care for your {product_name}.",
  "hashtags": ["#PlantCare"]
}}
```"""
        
    return mock_response

# Apply the monkey patch at the class level immediately when pytest imports conftest.py
langchain_openai.ChatOpenAI.invoke = MagicMock(side_effect=mock_invoke_side_effect)

# Patch litellm.completion for CrewAI agents to run them entirely in-memory
import litellm

def mock_litellm_completion(*args, **kwargs):
    messages = kwargs.get("messages", [])
    prompt_str = str(messages)
    mock_res = mock_invoke_side_effect(prompt_str)
    
    response_mock = MagicMock()
    choice_mock = MagicMock()
    choice_mock.message.content = mock_res.content
    response_mock.choices = [choice_mock]
    return response_mock

litellm.completion = MagicMock(side_effect=mock_litellm_completion)

@pytest.fixture(autouse=True)
def cleanup_services():
    yield
    try:
        youtube_monitor_svc.stop()
    except Exception:
        pass
