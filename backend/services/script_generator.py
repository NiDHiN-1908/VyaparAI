# backend/services/script_generator.py
import logging
import random
import re
import difflib
from typing import Dict, Any, List, Optional
from backend.services.supabase_service import supabase_svc
from backend.services.rag_service import rag_svc
from backend.agents.content_agent import get_ollama_llm

logger = logging.getLogger("vyaparai.services.script_generator")

BOTANICAL_VALIDATION_RULES = {
    "jasmine": {
        "allowed_keywords": ["fragrance", "scent", "sweet", "starry", "white", "flower", "bloom", "climber", "climbing", "trellis", "fence", "balcony", "pollinators", "night", "evening"],
        "forbidden_keywords": ["thick succulent leaves", "succulent", "gel", "extract", "aloe", "water storage", "cactus", "cacti", "snake plant", "sansevieria"]
    },
    "snake plant": {
        "allowed_keywords": ["bedroom", "low light", "air-purifying", "nasa", "toxin", "oxygen", "indestructible", "dry soil", "minimal water", "mother-in-law"],
        "forbidden_keywords": ["flower", "bloom", "fragrance", "scent", "sweet", "starry", "climbing", "trellis", "bonsai", "wiring", "gel"]
    },
    "aloe vera": {
        "allowed_keywords": ["gel", "skin", "soothing", "succulent", "drought", "propagation", "pups", "mother plant", "cactus soil", "immortality"],
        "forbidden_keywords": ["fragrance", "scent", "sweet", "starry", "white", "climber", "climbing", "trellis", "bonsai", "wiring", "palm", "bloom for weeks"]
    },
    "rose": {
        "allowed_keywords": ["pruning", "bloom", "sunlight", "outdoor", "fragrance", "classic", "attracts bees", "fences", "balconies", "romantic"],
        "forbidden_keywords": ["indoor", "bedroom", "shade", "succulent", "gel", "air roots", "bark", "moss stick", "water storage", "toxin", "humidifier"]
    },
    "money plant": {
        "allowed_keywords": ["feng shui", "vastu", "climber", "water propagation", "ivy", "moss stick", "hydroponic", "devil's ivy", "prosperity"],
        "forbidden_keywords": ["flower", "bloom", "fragrance", "scent", "sweet", "succulent", "gel", "pruning roses", "bonsai", "wiring"]
    },
    "orchid": {
        "allowed_keywords": ["aerial roots", "air roots", "pine bark", "humidity", "exotic", "luxury", "moss", "bloom for weeks"],
        "forbidden_keywords": ["soil", "garden soil", "succulent", "gel", "outdoor garden", "indestructible", "bedroom air"]
    },
    "bonsai": {
        "allowed_keywords": ["zen", "mindfulness", "wiring", "pruning", "art", "sculpture", "miniature", "harmony", "balance"],
        "forbidden_keywords": ["gel", "air-purifying", "nasa", "bedroom air", "hydroponic", "water jar", "climber", "trellis"]
    },
    "areca palm": {
        "allowed_keywords": ["humidifier", "toxins", "pet-friendly", "cat", "dog", "fronds", "golden cane", "gaseous toxins"],
        "forbidden_keywords": ["flower", "bloom", "fragrance", "scent", "sweet", "succulent", "gel", "cactus", "spines", "wiring"]
    },
    "peace lily": {
        "allowed_keywords": ["droop", "thirsty", "spathes", "white", "shade", "low light", "mold spores", "hooded"],
        "forbidden_keywords": ["succulent", "gel", "wiring", "desert", "intense sun", "cactus", "spines"]
    },
    "cactus": {
        "allowed_keywords": ["desert", "spines", "needles", "low water", "neglect", "gritty soil", "sandy", "succulent mix"],
        "forbidden_keywords": ["high water", "daily water", "shade", "humidity", "humidifier", "air roots", "moss stick", "trellis"]
    }
}

CTA_STYLES = [
    "Our nursery has a fresh, healthy batch pre-potted and loaded with buds. Comment 'Link' or 'BUY' below to get your direct WhatsApp checkout discount!",
    "Want this beautiful, fragrant plant delivered fresh to your doorstep? Comment 'Link' below to view nursery pricing and free delivery options!",
    "Ready to transform your home garden? Comment 'Link' below and we'll send our direct nursery catalog and special price offer straight to your DMs!",
    "Get your healthy, root-conditioned plant today! Comment the word 'Link' below to get a direct WhatsApp checkout link!",
    "Comment 'Link' below to check current nursery availability, special price offer, and free plant care guide!"
]

# 1. BOTANICAL DATABASE FOR TARGET PLANTS
BOTANICAL_DB = {
    "snake plant": {
        "scientific_name": "Sansevieria trifasciata",
        "category": "Indoor / Low Maintenance / Air-purifying",
        "benefits": [
            "Converts carbon dioxide to oxygen at night, making it the perfect bedroom plant",
            "Passes the famous NASA Clean Air Study for removing toxins like benzene, formaldehyde, xylene, and toluene",
            "Filters household toxins day and night"
        ],
        "care_instructions": "Water only when the soil is completely dry (usually once in 2-3 weeks). Enjoys indirect sunlight but survives in low-light corners.",
        "interesting_facts": "Virtually indestructible, it's known as 'Mother-in-law's tongue' due to its sharp leaves.",
        "common_mistakes": "Overwatering leads to root rot. Never let it sit in soggy soil.",
        "faqs": [
            {"q": "Can it survive in a dark bedroom?", "a": "Yes, it is highly shade-tolerant, though it grows faster in indirect light."}
        ],
        "growing_tips": "Use a well-draining succulent soil mix and a terracotta pot to allow excess moisture to evaporate.",
        "uses": "Home decor, air purification, indoor bedrooms, office desks.",
        "keywords": ["snake plant", "sansevieria", "bedroom plant", "air purifier", "nasa study", "low maintenance plant"]
    },
    "rose": {
        "scientific_name": "Rosa",
        "category": "Outdoor / Flowering / Decorative / Premium Collection",
        "benefits": [
            "Adds premium aesthetic value and classic elegance to your outdoor garden",
            "Produces a natural therapeutic fragrance that relieves stress and calms the mind",
            "Attracts beneficial pollinators like honeybees and butterflies to your yard"
        ],
        "care_instructions": "Needs at least 5-6 hours of direct morning sunlight daily. Water deeply but ensure soil drains completely.",
        "interesting_facts": "Different colors hold symbolic meanings: red for romance, yellow for friendship, and white for purity.",
        "common_mistakes": "Watering the leaves directly instead of the soil, which invites black spots and fungal diseases.",
        "faqs": [
            {"q": "How often should I prune roses?", "a": "Prune them in early spring or late winter to promote heavy blooming."}
        ],
        "growing_tips": "Feed them organic compost or bone meal once a month during the growing season for maximum blooms.",
        "uses": "Garden borders, cut flowers, balcony decor, gifting.",
        "keywords": ["rose plant", "rose blooms", "garden beauty", "rose care tips", "flowering plant", "fragrant roses"]
    },
    "aloe vera": {
        "scientific_name": "Aloe barbadensis miller",
        "category": "Succulent / Medicinal / Low Maintenance",
        "benefits": [
            "Gel is packed with vitamins and antioxidants, perfect for natural skin care and soothing burns",
            "Highly drought-tolerant, surviving weeks without a drop of water",
            "Acts as a natural air purifier and signals high toxin levels with brown spots"
        ],
        "care_instructions": "Place in bright, indirect sunlight or direct sun. Water sparingly, only when the soil is bone dry.",
        "interesting_facts": "Used for over 6,000 years, Egyptians called it the 'plant of immortality'.",
        "common_mistakes": "Using standard garden soil which retains water, drowning the roots. Always use cactus mix.",
        "faqs": [
            {"q": "How do I harvest the gel?", "a": "Cut an outer leaf close to the base, wash it, stand it upright to drain the yellow aloin, then slice it open."}
        ],
        "growing_tips": "Propagates easily by separating the small 'pups' that grow around the mother plant's base.",
        "uses": "Skin treatment, home first-aid, cosmetics, low-water gardening.",
        "keywords": ["aloe vera gel", "skin care plant", "medicinal succulent", "drought tolerant", "easy propagation", "aloe care"]
    },
    "money plant": {
        "scientific_name": "Epipremnum aureum",
        "category": "Indoor / Climber / Hanging plant / Low Maintenance",
        "benefits": [
            "Brings positive energy, prosperity, and good luck according to Feng Shui and Vastu",
            "Thrives easily in both water jars and soil pots, making propagation a breeze",
            "Excellent climber that quickly covers walls, shelves, and moss sticks with lush green leaves"
        ],
        "care_instructions": "Thrives in indirect sunlight. Water when the top inch of soil feels dry. Can grow hydroponically in plain water.",
        "interesting_facts": "Also called Devil's Ivy because it is nearly impossible to kill and stays green even in the dark.",
        "common_mistakes": "Using hard tap water with chlorine, which turns the glossy leaves yellow. Use filtered or rested water.",
        "faqs": [
            {"q": "Does it grow in water forever?", "a": "Yes, but change the water weekly and feed it liquid fertilizer occasionally."}
        ],
        "growing_tips": "Take stem cuttings with at least one node and place them in water to watch roots grow in 7 days.",
        "uses": "Living room decor, water vase display, moss stick climbing, hanging baskets.",
        "keywords": ["money plant", "feng shui plant", "water propagation", "fast growing climber", "devils ivy", "indoor vine"]
    },
    "orchid": {
        "scientific_name": "Orchidaceae",
        "category": "Indoor / Rare plant / Flowering / Premium Collection / Luxury",
        "benefits": [
            "Produces exotic, long-lasting flowers that bloom for weeks, representing luxury and elegance",
            "Features unique air roots that absorb moisture directly from the humid atmosphere",
            "Sleek minimalist look that elevates contemporary interior design"
        ],
        "care_instructions": "Give them bright, filtered light. Do not plant in regular soil; use pine bark or moss. Water weekly by soaking.",
        "interesting_facts": "With over 25,000 species, orchids are one of the two largest families of flowering plants on earth.",
        "common_mistakes": "Letting water sit in the leaf joints, which leads to crown rot. Keep leaves dry.",
        "faqs": [
            {"q": "Why are the roots growing outside the pot?", "a": "These are aerial roots used to grab moisture and light. Do not cut them!"}
        ],
        "growing_tips": "Mist their aerial roots daily if indoor humidity is low, or place on a pebble tray with water.",
        "uses": "Luxury decor, elegant centerpieces, exotic gifts, humid balconies.",
        "keywords": ["orchid care", "exotic blooms", "premium orchids", "air roots", "luxury houseplant", "humidity loving"]
    },
    "jasmine": {
        "scientific_name": "Jasminum",
        "category": "Outdoor / Climber / Flowering / Fragrance",
        "benefits": [
            "Emits an intense, sweet fragrance, particularly at night, creating a soothing garden aura",
            "Used to extract essential oils that reduce anxiety and promote restful sleep",
            "Vigorous climber that quickly covers trellises, fences, and balconies with starry white flowers"
        ],
        "care_instructions": "Requires full sun to partial shade. Prefers rich, moist, well-draining soil. Water regularly to keep soil damp.",
        "interesting_facts": "The name Jasmine is derived from the Persian word 'Yasmin', which means 'gift from God'.",
        "common_mistakes": "Over-pruning during the blooming season, which removes the fresh buds before they open.",
        "faqs": [
            {"q": "Does jasmine need support?", "a": "Yes, most jasmines are climbers that require a trellis or fence to scale."}
        ],
        "growing_tips": "Prune immediately after the summer flowering cycle finishes to encourage bushier growth for next season.",
        "uses": "Balcony trellises, natural home fragrance, herbal teas, landscaping.",
        "keywords": ["jasmine climber", "jasmine fragrance", "night blooming jasmine", "herbal scent", "balcony climber"]
    },
    "bonsai": {
        "scientific_name": "Bonsai (Artform)",
        "category": "Indoor or Outdoor / Bonsai / Decorative / Premium Collection",
        "benefits": [
            "Represents the ancient Japanese art of Zen, cultivating patience and mindfulness",
            "Stunning living sculpture that serves as a high-end, premium statement piece",
            "Symbolizes longevity, balance, and harmony in your home workspace"
        ],
        "care_instructions": "Requires careful watering—never let the soil dry out fully. Needs bright light, prune regularly to shape.",
        "interesting_facts": "Bonsai is not a dwarf species; any tree can be trained into a bonsai using wiring and pruning.",
        "common_mistakes": "Treating it like a regular indoor plastic plant. It requires fresh air, humidity, and precise watering.",
        "faqs": [
            {"q": "How old do Bonsais get?", "a": "With proper care, they can live for hundreds of years, passed down through generations."}
        ],
        "growing_tips": "Learn to wire branches gently in spring when the wood is flexible, removing the wire before it cuts the bark.",
        "uses": "Zen desktop decor, artistic collection, premium gifting, patio display.",
        "keywords": ["bonsai tree", "bonsai art", "zen gardening", "miniature tree", "premium bonsai", "wiring and pruning"]
    },
    "areca palm": {
        "scientific_name": "Dypsis lutescens",
        "category": "Indoor / Air-purifying / Foliage / Decorative",
        "benefits": [
            "Acts as a natural humidifier, releasing over a liter of water vapor daily to prevent dry skin",
            "Highly effective at removing indoor gaseous toxins like xylene, toluene, and formaldehyde",
            "100% pet-friendly and safe for cats and dogs, unlike many other houseplants"
        ],
        "care_instructions": "Enjoys bright, filtered light. Water when the top soil begins to feel dry. Avoid overwatering.",
        "interesting_facts": "Also known as the Golden Cane Palm due to its beautiful yellow-golden stems.",
        "common_mistakes": "Using heavily fluoridated water, which causes salt buildup and burns the leaf tips brown.",
        "faqs": [
            {"q": "Why are my palm leaves turning yellow?", "a": "Usually due to dry air or direct scorching sunlight. Move it slightly away from windows."}
        ],
        "growing_tips": "Feed with liquid fertilizer every 2 months in spring and summer to maintain deep green fronds.",
        "uses": "Living room corners, office lobbies, tropical theme decor, pet-safe gardens.",
        "keywords": ["areca palm", "golden cane palm", "humidifier plant", "pet friendly houseplant", "tropical decor"]
    },
    "peace lily": {
        "scientific_name": "Spathiphyllum",
        "category": "Indoor / Flowering / Air-purifying / Shade plant",
        "benefits": [
            "Cleans indoor air by filtering out dangerous mold spores and chemical vapors",
            "Produces elegant, hooded white spathes that look like peace flags",
            "Clearly signals when it is thirsty by drooping its leaves, then bounces back in hours"
        ],
        "care_instructions": "Thrives in low-light and shade. Water only when the leaves start to droop or the soil dry.",
        "interesting_facts": "Peace Lilies are not true lilies; they belong to the Araceae family, like calla lilies.",
        "common_mistakes": "Giving it too much direct sun, which immediately scorches the delicate white flowers and green leaves.",
        "faqs": [
            {"q": "How do I make my Peace Lily bloom?", "a": "If it won't bloom, move it to a slightly brighter room with indirect light; low light stops flowering."}
        ],
        "growing_tips": "Wipe the broad leaves weekly with a damp cloth to remove dust and maximize photosynthesis.",
        "uses": "Bedroom air filtering, shade gardens, office desk ornaments, indoor plants.",
        "keywords": ["peace lily", "peace lily bloom", "shade tolerant plant", "drooping leaves warning", "clean mold spores"]
    },
    "cactus": {
        "scientific_name": "Cactaceae",
        "category": "Indoor or Outdoor / Succulent / Low Maintenance / Desert Beauty",
        "benefits": [
            "Incredibly low maintenance, requiring water only once a month",
            "Unique geometrical shapes and protective spines that add a striking modern look to decor",
            "Brings resilient desert vibes and vibrant, surprising floral blooms in dry conditions"
        ],
        "care_instructions": "Needs intense, bright sun. Water deeply but very rarely. Must use sandy, gritty cactus soil.",
        "interesting_facts": "Cactus spines are actually modified leaves that help the plant capture dew and prevent evaporation.",
        "common_mistakes": "Watering in winter when the plant is dormant. They need almost zero water from November to February.",
        "faqs": [
            {"q": "How do I know if my cactus is healthy?", "a": "It should be firm to the touch. Softness or mushiness indicates root rot from overwatering."}
        ],
        "growing_tips": "Repot using heavy leather gloves or kitchen tongs to protect your fingers from sharp needles.",
        "uses": "Sunny windowsills, rocky outdoor gardens, miniature desk gardens.",
        "keywords": ["cactus succulent", "desert decor", "low water gardening", "window plant", "cactus needles"]
    }
}

# 2. DEFINITION OF THE 25 CREATIVE SCRIPT STYLES
SCRIPT_STYLES = {
    "storytelling": {
        "desc": "Narrating a journey or a mini-story about the plant's origin, history, or how it transforms a gardener's life.",
        "tone": "Warm, reflective, engaging, narrative",
        "structure": ["Hook / Narrative opener", "Story development", "Horticultural facts tied to story", "Emotional connection", "Natural CTA"]
    },
    "educational": {
        "desc": "Focusing on care tips, leaf diagnostics, propagation secrets, or growth habits.",
        "tone": "Expert, clear, informative, helpful",
        "structure": ["Hook / Question", "The core concept / explanation", "Step-by-step instructions", "Pro tip", "Horticultural CTA"]
    },
    "customer problem -> solution": {
        "desc": "Starting with a common frustration (e.g. killing house plants, dull decor, dry air) and showing how this plant is the answer.",
        "tone": "Empathetic, solving, reassuring",
        "structure": ["Pain point hook", "Agitation of the problem", "Introduction of plant as solution", "Key benefits resolving issue", "Problem solver CTA"]
    },
    "emotional": {
        "desc": "Focusing on the peace, mindfulness, stress relief, and positive aura the plant brings.",
        "tone": "Calming, gentle, poetic, serene",
        "structure": ["Mindful opener", "Sensory details (touch, smell, green sights)", "Emotional value & wellness", "Care connection", "Gentle CTA"]
    },
    "luxury": {
        "desc": "Positioning the plant as a rare, elegant, premium living design element.",
        "tone": "Sophisticated, exclusive, high-end",
        "structure": ["Sleek design hook", "Aesthetic value and visual status", "Exclusive plant traits", "Styling recommendation", "Exclusive CTA"]
    },
    "cinematic": {
        "desc": "Dramatic visuals, grand analogies, focus on leaf patterns, light rays, and close-ups.",
        "tone": "Epic, artistic, awe-inspiring",
        "structure": ["Epic visual hook", "Analogy of nature's design", "Botanical details", "Cinematic landscape care", "Direct visual CTA"]
    },
    "documentary": {
        "desc": "Explaining the plant's natural habitat, origin (e.g. tropical forests of Brazil, deserts of Mexico), and survival strategies.",
        "tone": "Educational, narrative, adventurous",
        "structure": ["Wild origin hook", "Natural habitat exploration", "Survival adaptations", "Home placement matching wild environment", "Scientific CTA"]
    },
    "nature appreciation": {
        "desc": "A tribute to green foliage, blooming patterns, and the beauty of natural life.",
        "tone": "Poetic, enthusiastic, nature-loving",
        "structure": ["Appreciation hook", "Foliage details", "Natural cycles", "Gardening joy", "Enthusiast CTA"]
    },
    "gardening tips": {
        "desc": "Direct, action-oriented hacks on fertilizer, repotting, pruning, or potting soil.",
        "tone": "Practical, hands-on, expert",
        "structure": ["Direct action hook", "The hack breakdown", "Materials needed", "Expected result", "Quick CTA"]
    },
    "before vs after": {
        "desc": "Contrasting an empty, boring space with a lush green sanctuary, or a droopy plant with a thriving one.",
        "tone": "Inspiring, dramatic, transformation",
        "structure": ["Before state hook", "The gap / missing element", "The transformation agent (the plant)", "After state description", "Actionable CTA"]
    },
    "myth vs fact": {
        "desc": "Debunking common misconceptions (e.g., all plants need daily watering, succulents love deep shade) with scientific facts.",
        "tone": "Intriguing, corrective, educational",
        "structure": ["Myth hook", "Debunking explanation", "Scientific fact", "Practical care outcome", "Fact checker CTA"]
    },
    "fun facts": {
        "desc": "Listing unusual, quirky, or surprising facts about the plant's biology or history.",
        "tone": "Lighthearted, surprising, trivia-based",
        "structure": ["Surprising trivia hook", "Quirky facts", "Biological explanation", "Conversation starter care", "Fun CTA"]
    },
    "scientific explanation": {
        "desc": "Focusing on photosynthesis, toxin chemical filtration, transpiration rates, or botanical classification.",
        "tone": "Scientific, expert, technical but accessible",
        "structure": ["Scientific terminology hook", "Biological mechanisms", "Clean air/growth chemistry", "Home application", "Technical CTA"]
    },
    "lifestyle": {
        "desc": "Showing how a busy professional, active parent, or minimalist fits this plant into their daily routine.",
        "tone": "Casual, modern, relatable",
        "structure": ["Daily routine hook", "Busy lifestyle integration", "Low-effort care tips", "Visual decor impact", "Relatable CTA"]
    },
    "home decoration": {
        "desc": "Focusing on interior design, matching plant pots to walls, shelf placement, and corner styling.",
        "tone": "Creative, artistic, stylish",
        "structure": ["Decor upgrade hook", "Styling ideas (shelves, corners, tables)", "Light matching", "Visual texture blending", "Designer CTA"]
    },
    "festival special": {
        "desc": "Tying the plant to upcoming festivals, holiday decorations, or auspicious gifting traditions (e.g. Diwali, New Year, housewarming).",
        "tone": "Festive, warm, celebratory",
        "structure": ["Auspicious / Festive hook", "Symbolism and traditional values", "Gifting appeal", "Holiday display tips", "Festive CTA"]
    },
    "seasonal promotion": {
        "desc": "Highlighting monsoon growth, winter dormancy care, or summer blooming cycles.",
        "tone": "Urgent, timely, seasonal",
        "structure": ["Seasonal change hook", "Current climate effect on plant", "Must-do seasonal care", "Limited season offer", "Timely CTA"]
    },
    "kids education": {
        "desc": "Simple, fun language designed to teach children how plants grow, breathe, and drink water.",
        "tone": "Playful, simple, enthusiastic",
        "structure": ["Kid friendly hook", "Simple plant biology (roots drink, leaves eat light)", "Fun daily care duty", "Educational value", "Family CTA"]
    },
    "sustainability": {
        "desc": "Focusing on eco-friendly gardening, organic fertilizers, reducing carbon footprints, and natural biodiversity.",
        "tone": "Conscious, eco-friendly, green",
        "structure": ["Green planet hook", "Organic care practices", "Sustainability benefits", "Eco-impact of growing plants", "Conscious CTA"]
    },
    "wellness": {
        "desc": "Connecting plants to mental health, oxygen rich sleep, stress reduction, and healing vibes.",
        "tone": "Therapeutic, restorative, slow-paced",
        "structure": ["Vibe check hook", "Mental clarity / Stress reduction benefits", "Sleep and breathing improvement", "Mindful watering habit", "Wellness CTA"]
    },
    "quick facts": {
        "desc": "Fast-paced list of top 3 parameters: Light, Water, Soil.",
        "tone": "Crisp, concise, direct",
        "structure": ["Catchy speed hook", "Light rating", "Water rating", "Soil rating", "Fast CTA"]
    },
    "question-based hook": {
        "desc": "Starting with a provocative question that sparks instant curiosity.",
        "tone": "Inquisitive, curious, engaging",
        "structure": ["Intriguing question hook", "Core search for answer", "Horticultural evidence", "Takeaway tip", "Answer CTA"]
    },
    "challenge format": {
        "desc": "Frame the video as a challenge: 'Can you keep this plant alive for 30 days?', 'Try this 1-week water propagation challenge.'",
        "tone": "Exciting, community-driven, playful",
        "structure": ["Challenge invitation hook", "Rules / Step-by-step setup", "What to look for (growth indicators)", "Community check-in", "Challenger CTA"]
    },
    "asmr style": {
        "desc": "Focusing on the auditory sounds of gardening: leaf dusting, potting soil pouring, misting spray, and visual textures.",
        "tone": "Soft-spoken, sensory, whispering-vibe, calm",
        "structure": ["Sensation-rich ASMR hook", "Visual leaf check & dust wipe sound", "Watering/potting soil crunch", "Quiet care reflection", "Whispered CTA"]
    },
    "viral short-form content": {
        "desc": "Extremely punchy, high pacing, trending style with a bold claim or shocking hook.",
        "tone": "Energetic, bold, snappy",
        "structure": ["Shocking statement hook", "Rapid facts / Visual showcase", "One killer benefit", "Quick hack", "Punchy CTA"]
    }
}

# 3. DYNAMIC HOOK AND TRANSITION TEMPLATES BY STYLE
HOOK_TEMPLATES = {
    "question": [
        "Did you know this plant is actually secret royalty in the indoor plant world?",
        "Have you ever wondered why some plants seem to thrive while others die in a week?",
        "Is your home missing a touch of natural elegance?",
        "Can this one plant really improve your sleep quality?",
        "What happens if you stop watering your plant for 3 weeks?"
    ],
    "mistake": [
        "Most people kill this plant because they love it way too much...",
        "This one simple mistake ruins your plant's leaves instantly.",
        "Stop buying expensive artificial decor when you can get this.",
        "Please stop watering your plants like this..."
    ],
    "aesthetic": [
        "Your bedroom is missing this green masterpiece...",
        "If you want that luxury organic aesthetic, start here.",
        "Transform that boring empty corner into a tropical sanctuary."
    ],
    "intrigue": [
        "NASA studied this plant for years, and what they found is amazing...",
        "This tiny botanical secret is going to change your living space.",
        "Watch what happens when you propagate this in plain water..."
    ]
}

TRANSITIONS = [
    "But here's where it gets interesting.",
    "Now, look closely at these gorgeous details.",
    "So, how do we keep it happy?",
    "That is where the real magic happens.",
    "But don't worry, the solution is incredibly simple.",
    "Check out this cool botanical secret."
]

CTAS_BY_PLATFORM = {
    "youtube_shorts": [
        "If you're ready to grow your own, comment 'Link' below to get our direct garden catalog!",
        "Comment the word 'Link' below to get our step-by-step care guide sent straight to your inbox!",
        "Want this plant in your home? Comment 'Link' and we'll reply with all nursery details!"
    ],
    "instagram_reels": [
        "If you are interested, comment 'Link' below and we'll DM you the nursery pricing!",
        "Drop a comment saying 'Link' below to get a direct WhatsApp checkout link!",
        "Comment the word 'Link' to get this premium plant shipped to your home!"
    ],
    "facebook_reels": [
        "Comment 'Link' below, and we'll send you our current availability and discount code!",
        "If you are interested in ordering, comment 'Link' below to chat with our botanical experts!",
        "Comment the word 'Link' below to check pricing and get free nursery shipping!"
    ]
}

SYNONYMS = {
    "beautiful": ["stunning", "gorgeous", "magnificent", "exquisite", "breath-taking", "luxurious", "striking"],
    "healthy": ["robust", "thriving", "vigorous", "strong", "lush", "flourishing", "premium-grade"],
    "grow": ["thrive", "bloom", "propagate", "accelerate", "expand", "flourish"],
    "simple": ["effortless", "breeze", "beginner-friendly", "fail-proof", "low-effort", "straightforward"]
}

class ScriptGeneratorEngine:
    def __init__(self):
        self.supabase = supabase_svc

    def analyze_product_characteristics(self, name: str, description: str) -> Dict[str, Any]:
        """Analyzes product name and description to extract botanical categories."""
        text = f"{name} {description}".lower()
        traits = {
            "indoor_outdoor": "Indoor" if any(kw in text for kw in ["indoor", "bedroom", "living room", "office", "shade", "desk"]) else "Outdoor",
            "is_flowering": any(kw in text for kw in ["flower", "bloom", "fragrance", "petal", "jasmine", "rose", "orchid", "spathe", "lily"]),
            "is_foliage": any(kw in text for kw in ["foliage", "leaves", "leaf", "palm", "fern", "ivy", "fronds", "pothos"]),
            "is_medicinal": any(kw in text for kw in ["medicinal", "heal", "skin", "burns", "aloe", "herb", "ayurveda"]),
            "is_air_purifying": any(kw in text for kw in ["air-purifying", "air purifier", "nasa", "toxin", "benzene", "oxygen"]),
            "is_succulent": any(kw in text for kw in ["succulent", "cactus", "cacti", "drought", "arid", "aloe"]),
            "is_bonsai": "bonsai" in text,
            "is_climber": any(kw in text for kw in ["climber", "vine", "trellis", "moss stick", "money plant"]),
            "is_hanging": any(kw in text for kw in ["hanging", "basket", "droop", "trail"]),
            "is_low_maintenance": any(kw in text for kw in ["low maintenance", "easy care", "indestructible", "hardy", "beginner"]),
            "is_rare": any(kw in text for kw in ["rare", "exotic", "premium", "collector", "variegated"]),
            "care_level": "Low" if any(kw in text for kw in ["low maintenance", "easy", "neglect", "drought"]) else "Medium"
        }
        
        # Determine category tags
        tags = []
        if traits["indoor_outdoor"] == "Indoor":
            tags.append("Indoor Plant")
        else:
            tags.append("Outdoor Garden")
        if traits["is_flowering"]:
            tags.append("Flowering Plant")
        if traits["is_foliage"]:
            tags.append("Foliage Plant")
        if traits["is_medicinal"]:
            tags.append("Medicinal Plant")
        if traits["is_air_purifying"]:
            tags.append("Air Purifying")
        if traits["is_succulent"]:
            tags.append("Succulent/Cactus")
        if traits["is_bonsai"]:
            tags.append("Bonsai Art")
        if traits["is_climber"]:
            tags.append("Climber/Vine")
        if traits["is_hanging"]:
            tags.append("Hanging Plant")
        if traits["is_low_maintenance"]:
            tags.append("Low Maintenance")
        if traits["is_rare"]:
            tags.append("Premium Collection")
            
        traits["tags"] = tags
        return traits

    def get_style_probabilities_from_analytics(self) -> Dict[str, float]:
        """Reads youtube_analytics to dynamically weight script styles based on performance."""
        # Setup baseline probabilities
        base_weight = 1.0 / len(SCRIPT_STYLES)
        weights = {style: base_weight for style in SCRIPT_STYLES.keys()}
        
        try:
            # Fetch channels to get analytics
            if self.supabase.is_mock:
                from backend.services.supabase_service import MOCK_DB
                analytics_data = MOCK_DB.get("youtube_analytics", [])
            else:
                res = self.supabase.client.table("youtube_analytics").select("*").execute()
                analytics_data = res.data or []
                
            if not analytics_data:
                return weights
                
            # Iterate through analytics to aggregate performance of top videos
            style_perf = {style: {"views": 0, "count": 0} for style in SCRIPT_STYLES.keys()}
            
            # Retrieve scripts to cross-reference style metadata
            all_scripts = []
            if self.supabase.is_mock:
                from backend.services.supabase_service import MOCK_DB
                all_scripts = MOCK_DB.get("scripts", [])
            else:
                res_s = self.supabase.client.table("scripts").select("*").execute()
                all_scripts = res_s.data or []
                
            # Map script titles to style used (stored in scene_breakdown meta)
            title_to_style = {}
            for s in all_scripts:
                # Find style in scene_breakdown metadata if present
                style_name = None
                sb = s.get("scene_breakdown") or []
                if isinstance(sb, list) and len(sb) > 0:
                    last_scene = sb[-1]
                    if isinstance(last_scene, dict) and "meta" in last_scene:
                        style_name = last_scene["meta"].get("style")
                if style_name and style_name in SCRIPT_STYLES:
                    title_to_style[s.get("title")] = style_name
            
            # Accumulate views
            total_performance_views = 0
            for item in analytics_data:
                top_vids = item.get("top_videos") or []
                for v in top_vids:
                    title = v.get("title", "")
                    views = int(v.get("views", 0))
                    
                    # Match title to find style
                    matched_style = None
                    for t_key, s_key in title_to_style.items():
                        if t_key and t_key.lower() in title.lower():
                            matched_style = s_key
                            break
                            
                    if matched_style:
                        style_perf[matched_style]["views"] += views
                        style_perf[matched_style]["count"] += 1
                        total_performance_views += views
            
            # Recalculate weights if we have data
            if total_performance_views > 0:
                for style, data in style_perf.items():
                    if data["count"] > 0:
                        # Give performance weight + baseline weight to ensure exploration
                        perf_ratio = data["views"] / total_performance_views
                        weights[style] = (0.7 * perf_ratio) + (0.3 * base_weight)
                
                # Normalize weights
                total_w = sum(weights.values())
                weights = {k: v / total_w for k, v in weights.items()}
                logger.info(f"Dynamic Style Learning Weights updated successfully! Top style: {max(weights, key=weights.get)}")
        except Exception as e:
            logger.warning(f"Failed to calculate style probabilities from analytics: {e}. Using uniform weights.")
            
        return weights

    def select_script_parameters(self) -> tuple:
        """Selects style and platform using performance weighting."""
        style_weights = self.get_style_probabilities_from_analytics()
        styles = list(style_weights.keys())
        probs = list(style_weights.values())
        
        # Safeguard sum to 1.0
        s_prob = sum(probs)
        if abs(s_prob - 1.0) > 1e-5:
            probs = [p / s_prob for p in probs]
            
        chosen_style = random.choices(styles, weights=probs, k=1)[0]
        chosen_platform = random.choice(["YouTube Shorts", "Instagram Reels", "Facebook Reels"])
        return chosen_style, chosen_platform

    def compute_similarity(self, s1: str, s2: str) -> float:
        """Computes text similarity using SequenceMatcher."""
        # Strip punctuation and lower-case to compare raw text content
        s1_clean = re.sub(r'[^\w\s]', '', s1.lower()).strip()
        s2_clean = re.sub(r'[^\w\s]', '', s2.lower()).strip()
        return difflib.SequenceMatcher(None, s1_clean, s2_clean).ratio()

    def check_duplicate_threshold(self, script_text: str) -> bool:
        """Checks if the script has > 70% similarity with any previously generated script."""
        try:
            if self.supabase.is_mock:
                from backend.services.supabase_service import MOCK_DB
                all_scripts = MOCK_DB.get("scripts", [])
            else:
                res = self.supabase.client.table("scripts").select("script_text").execute()
                all_scripts = res.data or []
                
            for s in all_scripts:
                prev_text = s.get("script_text")
                if prev_text:
                    sim = self.compute_similarity(script_text, prev_text)
                    if sim > 0.70:
                        logger.warning(f"Duplicate script detected! Similarity: {sim:.2f} with previous script.")
                        return True
        except Exception as e:
            logger.error(f"Error querying duplicate scripts: {e}")
        return False

    def get_plant_database_facts(self, name: str) -> Optional[Dict[str, Any]]:
        """Matches product name against botanical database to fetch product-specific content."""
        n_clean = name.lower().strip()
        # Find partial match in database keys
        for key, value in BOTANICAL_DB.items():
            if key in n_clean or n_clean in key:
                return value
        return None

    def deduplicate_script_text(self, text: str) -> str:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        unique_sentences = []
        for s in sentences:
            s_clean = re.sub(r'[^\w\s]', '', s.lower()).strip()
            if not s_clean:
                continue
            is_dup = False
            for prev in unique_sentences:
                prev_clean = re.sub(r'[^\w\s]', '', prev.lower()).strip()
                sim = difflib.SequenceMatcher(None, s_clean, prev_clean).ratio()
                if sim > 0.75:
                    is_dup = True
                    break
            if not is_dup:
                unique_sentences.append(s)
        return " ".join(unique_sentences)

    def validate_botanical_script(self, plant_name: str, script_text: str) -> bool:
        text_lower = script_text.lower()
        matched_key = None
        for key in BOTANICAL_VALIDATION_RULES.keys():
            if key in plant_name.lower() or plant_name.lower() in key:
                matched_key = key
                break
        if not matched_key:
            return True
            
        rules = BOTANICAL_VALIDATION_RULES[matched_key]
        for kw in rules["forbidden_keywords"]:
            if kw in text_lower:
                logger.warning(f"Botanical Validation FAILED: Forbidden term '{kw}' found in script for {plant_name}.")
                return False
        
        matches = [kw for kw in rules["allowed_keywords"] if kw in text_lower]
        if len(matches) < 1:
            logger.warning(f"Botanical Validation FAILED: No specific allowed features found in script for {plant_name}.")
            return False
            
        return True

    def procedural_generate(
        self, 
        product_name: str, 
        description: str, 
        style: str, 
        platform: str, 
        rag_context: str = "",
        product_context: dict = None
    ) -> Dict[str, Any]:
        """Generates a highly diverse, unique script using combinatorial procedural generation.

        This acts as a solid, high-quality fallback that guarantees <70% similarity.
        """
        logger.info(f"Triggering Combinatorial Procedural Generator for {product_name} in {style} style.")
        
        # 1. Product extraction
        traits = self.analyze_product_characteristics(product_name, description)
        plant_facts = self.get_plant_database_facts(product_name)
        
        # 2. Setup synonyms and vocabulary diversity helper
        def diversify_word(word: str) -> str:
            if word in SYNONYMS:
                return random.choice(SYNONYMS[word])
            return word

        # 3. Pull product-specific details
        category_desc = traits["tags"][0] if traits["tags"] else "beautiful home plant"
        if product_context:
            scientific = product_context.get("botanical_name", product_name)
            category_desc = product_context.get("category", category_desc)
            care = product_context.get("watering", "water when dry")
            fun_fact = product_context.get("unique_features", "highly valued for decor")
            mistake = product_context.get("common_mistakes", "overwatering")
            faq = product_context.get("FAQs", "easy to grow")
            specific_benefits = [product_context.get("customer_benefits", "beautiful garden feel")]
            uses_desc = product_context.get("target_audience", "indoor styling")
        elif plant_facts:
            specific_benefits = plant_facts["benefits"]
            care = plant_facts["care_instructions"]
            fun_fact = plant_facts["interesting_facts"]
            mistake = plant_facts["common_mistakes"]
            faq = f"{plant_facts['faqs'][0]['q']} - {plant_facts['faqs'][0]['a']}"
            scientific = plant_facts["scientific_name"]
            uses_desc = plant_facts["uses"]
        else:
            specific_benefits = [
                f"Brings a {diversify_word('beautiful')} green freshness into your space",
                f"Serves as an organic, {diversify_word('simple')} care design element",
                f"Supports a healthier and natural green lifestyle"
            ]
            care = f"Place in medium light conditions and water when the soil feels dry."
            fun_fact = f"This plant is highly valued for its resilient and decorative traits."
            mistake = "Overwatering and placing in direct hot midday sunlight."
            faq = f"Is it easy to care for? Yes, it is perfect for beginner plant parents."
            scientific = f"{product_name.replace(' ', '')} flora"
            uses_desc = "indoor styling and balcony garden enhancement"
            
        # Convert any list attributes to clean strings
        if isinstance(category_desc, list):
            category_desc = ", ".join(category_desc)
        if isinstance(scientific, list):
            scientific = ", ".join(scientific)
        if isinstance(care, list):
            care = ", ".join(care)
        if isinstance(fun_fact, list):
            fun_fact = ", ".join(fun_fact)
        if isinstance(mistake, list):
            mistake = ", ".join(mistake)
        if isinstance(faq, list):
            faq = ", ".join(faq)
        if isinstance(uses_desc, list):
            uses_desc = ", ".join(uses_desc)
            
        if isinstance(specific_benefits, list):
            cleaned_benefits = []
            for b in specific_benefits:
                if isinstance(b, list):
                    cleaned_benefits.extend([str(item) for item in b if item])
                elif b:
                    cleaned_benefits.append(str(b))
            specific_benefits = cleaned_benefits if cleaned_benefits else ["beautiful green growth"]

        # 4. Craft dynamic hook
        hook_category = random.choice(list(HOOK_TEMPLATES.keys()))
        hook_tpl = random.choice(HOOK_TEMPLATES[hook_category])
        hook_tpl = hook_tpl.replace("this plant", f"the {product_name}")
        hook_tpl = hook_tpl.replace("plants", f"{product_name}s")
        hook_tpl = hook_tpl.replace("your plant", f"your {product_name}")
        
        # 5. Assemble randomized structure flow
        style_info = SCRIPT_STYLES.get(style, SCRIPT_STYLES["educational"])
        structure = style_info["structure"]
        
        body_parts = []
        scene_breakdown = []
        t_phrase = random.choice(TRANSITIONS)
        
        # Build narrative pieces based on structure
        for step in structure:
            if "hook" in step.lower() or "opener" in step.lower() or "pain point" in step.lower():
                part_text = f"Hey plant lovers! {hook_tpl}"
                instr = f"Show a high-quality visual of the fresh {product_name} in a beautiful setting."
                body_parts.append(part_text)
                scene_breakdown.append({
                    "scene": len(scene_breakdown) + 1,
                    "instruction": instr,
                    "voiceover": part_text
                })
            elif "cta" in step.lower() or "action" in step.lower():
                part_text = random.choice(CTA_STYLES)
                instr = f"Show checkout link, product catalog, or contact phone on screen."
                body_parts.append(part_text)
                scene_breakdown.append({
                    "scene": len(scene_breakdown) + 1,
                    "instruction": instr,
                    "voiceover": part_text
                })
            elif "story" in step.lower() or "adaptation" in step.lower() or "habitat" in step.lower():
                part_text = f"Originally, this plant thrived in specialized conditions, adapting to conserve every drop of water. {t_phrase} Now, it brings that same wild resilience right into your home."
                instr = f"Slow pan close-up showing detail of the leaves or soil texture of {product_name}."
                body_parts.append(part_text)
                scene_breakdown.append({
                    "scene": len(scene_breakdown) + 1,
                    "instruction": instr,
                    "voiceover": part_text
                })
            elif "fact" in step.lower() or "concept" in step.lower() or "benefit" in step.lower() or "adaptation" in step.lower():
                benefit = random.choice(specific_benefits)
                part_text = f"Did you know? {scientific} actually {benefit.lower()}. It's scientifically proven to help."
                instr = f"Focus on leaf nodes or flowers with a clean sunlight highlight."
                body_parts.append(part_text)
                scene_breakdown.append({
                    "scene": len(scene_breakdown) + 1,
                    "instruction": instr,
                    "voiceover": part_text
                })
            elif "tip" in step.lower() or "care" in step.lower() or "hack" in step.lower() or "setup" in step.lower() or "material" in step.lower():
                part_text = f"Our nursery plants are root-conditioned and pre-potted in a rich, organic soil mix so they thrive in your home from day one. Place your {product_name} in bright light, water when topsoil feels dry, and avoid heavy pruning in bloom season so fresh flower buds open!"
                instr = f"Demonstrate healthy potted {product_name} with green leaves and soil inspection."
                body_parts.append(part_text)
                scene_breakdown.append({
                    "scene": len(scene_breakdown) + 1,
                    "instruction": instr,
                    "voiceover": part_text
                })
            elif "aesthetic" in step.lower() or "design" in step.lower() or "decor" in step.lower() or "lifestyle" in step.lower():
                part_text = f"If you want that perfect, {diversify_word('beautiful')} organic feel, place your {product_name} on a wooden stand. It fits perfectly with {uses_desc}."
                instr = f"Show the {product_name} styled on a shelf or tabletop in a modern living space."
                body_parts.append(part_text)
                scene_breakdown.append({
                    "scene": len(scene_breakdown) + 1,
                    "instruction": instr,
                    "voiceover": part_text
                })
            elif "myth" in step.lower():
                part_text = f"Myth: many think this requires heavy daily care. Reality: it's actually extremely {diversify_word('simple')} and thrives on neglect!"
                instr = f"Show comparison graphic or side-by-side view."
                body_parts.append(part_text)
                scene_breakdown.append({
                    "scene": len(scene_breakdown) + 1,
                    "instruction": instr,
                    "voiceover": part_text
                })
            elif "trivia" in step.lower():
                part_text = f"Here is a mind-blowing fact: {fun_fact}"
                instr = f"Zoom in to show leaf close-up or root design."
                body_parts.append(part_text)
                scene_breakdown.append({
                    "scene": len(scene_breakdown) + 1,
                    "instruction": instr,
                    "voiceover": part_text
                })
            elif "emotional" in step.lower() or "wellness" in step.lower() or "sensory" in step.lower():
                if "rose" in product_name.lower():
                    part_text = "There's something deeply peaceful about the classic, elegant scent of fresh roses blooming in the sun."
                elif "jasmine" in product_name.lower():
                    part_text = "There's something deeply peaceful about the sweet, starry fragrance of fresh jasmine climbing on the balcony."
                elif traits.get("is_flowering") or traits.get("fragrance"):
                    part_text = f"There's something deeply peaceful about the sweet fragrance and beautiful blooms of the {product_name}."
                elif traits.get("is_succulent") or traits.get("is_foliage"):
                    part_text = f"There's something deeply peaceful about touching the cool, fresh green leaves of the {product_name}."
                else:
                    part_text = f"There's something deeply peaceful about connecting with nature and caring for your {product_name}."
                
                part_text += " It instantly reduces daily stress and builds focus."
                instr = f"A hand gently touching or inspecting the {product_name} in slow motion."
                body_parts.append(part_text)
                scene_breakdown.append({
                    "scene": len(scene_breakdown) + 1,
                    "instruction": instr,
                    "voiceover": part_text
                })
                
        if not any("cta" in s.lower() or "action" in s.lower() for s in structure):
            part_text = random.choice(CTA_STYLES)
            instr = f"Show checkout link, product catalog, or contact phone on screen."
            body_parts.append(part_text)
            scene_breakdown.append({
                "scene": len(scene_breakdown) + 1,
                "instruction": instr,
                "voiceover": part_text
            })

        if rag_context:
            rag_clean = rag_context.replace("\n", " ").strip()
            if len(rag_clean) > 120:
                rag_clean = rag_clean[:120] + "..."
            mid_idx = len(scene_breakdown) // 2
            if mid_idx > 0 and mid_idx < len(scene_breakdown):
                original_vo = scene_breakdown[mid_idx]["voiceover"]
                scene_breakdown[mid_idx]["voiceover"] = f"By the way, did you know that {rag_clean} Also, {original_vo}"
                body_parts[mid_idx] = scene_breakdown[mid_idx]["voiceover"]

        scene_breakdown[-1]["meta"] = {
            "style": style,
            "platform": platform,
            "hook_category": hook_category
        }
        
        full_script_text = " ".join(body_parts)
        
        caption_timeline = []
        current_time = 0.0
        for item in scene_breakdown:
            words_count = len(item["voiceover"].split())
            duration = min(7.0, max(2.5, words_count * 0.35))
            caption_timeline.append({
                "start": round(current_time, 1),
                "end": round(current_time + duration, 1),
                "text": item["voiceover"]
            })
            current_time += duration
            
        clean_name = "".join(c for c in product_name if c.isalnum())
        tags = [clean_name, category_desc.replace(" ", ""), "Gardening", "GreenHavenNursery"]
        
        title_options = [
            f"Transform your space with the gorgeous {product_name}! 🌿",
            f"The secret care hacks for your {product_name} ✨",
            f"How to keep your {product_name} thriving effortlessly! 🏡",
            f"Is the {product_name} really NASA-approved? Let's check 🔍"
        ]
        
        return {
            "title": random.choice(title_options),
            "hook": hook_tpl,
            "script_text": full_script_text,
            "scene_breakdown": scene_breakdown,
            "caption_timeline": caption_timeline,
            "thumbnail_text": f"Grow {product_name}!",
            "seo_description": f"Buy premium healthy {product_name} online with plant care guides and secure nationwide delivery direct from Green Haven Nursery.",
            "hashtags": tags
        }

    def generate(
        self, 
        product_name: str, 
        description: str, 
        product_images: List[str] = None, 
        force_feedback: str = None,
        product_context: dict = None
    ) -> Dict[str, Any]:
        """Generates a highly diverse, unique script using LLM with duplicate checks and retry loops.

        Falls back to combinatorial procedural generation if needed.
        """
        logger.info(f"Initiating script generation for product: {product_name}")
        
        style, platform = self.select_script_parameters()
        style_info = SCRIPT_STYLES[style]
        
        rag_context = ""
        try:
            rag_context = rag_svc.retrieve(f"{product_name} {description}")
            logger.info(f"Retrieved RAG context (first 100 chars): {rag_context[:100]}")
        except Exception as e:
            logger.warning(f"RAG Retrieval failed during script generation: {e}")
            
        botanical_details = ""
        if product_context:
            botanical_details = f"""
STRUCTURED PRODUCT CONTEXT PROFILE:
- Product Name: {product_context.get('product_name')}
- Botanical Name: {product_context.get('botanical_name')}
- Category: {product_context.get('category')}
- Sunlight: {product_context.get('sunlight')}
- Watering: {product_context.get('watering')}
- Soil: {product_context.get('soil')}
- Fertilizer: {product_context.get('fertilizer')}
- Propagation: {product_context.get('propagation')}
- Care Level: {product_context.get('care_level')}
- Unique Features: {product_context.get('unique_features')}
- Customer Benefits: {product_context.get('customer_benefits')}
- Emotional Benefits: {product_context.get('emotional_benefits')}
- Common Mistakes to Avoid: {product_context.get('common_mistakes')}
- FAQs: {product_context.get('FAQs')}
- Target Audience: {product_context.get('target_audience')}
"""
        else:
            plant_facts = self.get_plant_database_facts(product_name)
            if plant_facts:
                botanical_details = f"""
BOTANICAL FACT SHEET FOR THIS PRODUCT:
- Scientific Name: {plant_facts['scientific_name']}
- Air purification/Benefits: {', '.join(plant_facts['benefits'])}
- Care Instructions: {plant_facts['care_instructions']}
- Interesting Facts: {plant_facts['interesting_facts']}
- Common Care Mistakes to Avoid: {plant_facts['common_mistakes']}
"""
            
        rag_details = f"KNOWLEDGE BASE DETAILS (RAG):\n{rag_context}" if rag_context else ""
        chosen_cta_instruction = random.choice(CTA_STYLES)

        llm = get_ollama_llm()
        if hasattr(llm, "model_name") and llm.model_name.startswith("ollama/"):
            llm.model_name = llm.model_name.replace("ollama/", "", 1)
        elif hasattr(llm, "model") and llm.model.startswith("ollama/"):
            llm.model = llm.model.replace("ollama/", "", 1)
        for attempt in range(1, 4):
            try:
                structure_layout = " -> ".join(style_info["structure"])
                hook_recs = "\n".join([f"- {h}" for h in random.sample(HOOK_TEMPLATES[random.choice(list(HOOK_TEMPLATES.keys()))], 2)])
                
                prompt = f"""
You are an expert botanical copywriter and social media influencer writing a video script for the plant product: '{product_name}'.
Description: {description}

PLATFORM ENVIRONMENT: {platform}
SCRIPT WRITING STYLE: {style.upper()} ({style_info['desc']})
SCRIPT TONE: {style_info['tone']}
EXPECTED STRUCTURE: {structure_layout}

{botanical_details}
{rag_details}

INSTRUCTIONS:
1. RETAIL COPYWRITING: You are writing a video script to SELL this plant product to retail customers. Highlighting product value is MANDATORY (e.g., pre-potted in organic mix, healthy root system, heavy bloom buds, nursery guarantee, fast delivery).
2. CONVERSATIONAL SALES TONE: Write in a warm, human, conversational voice. NEVER write a dry Wikipedia care manual or textbook bullet list (avoid robotic phrases like 'Requires full sun... Prefers well-draining soil').
3. PUNCHY SELLING HOOK: The opening hook MUST grab attention instantly with a curiosity or desire-driven pattern interrupt. Inspired by:
{hook_recs}
4. RETAIL CALL TO ACTION: The ending CALL TO ACTION voiceover must explicitly instruct viewers to comment 'Link' or 'BUY' to receive nursery pricing, direct WhatsApp catalog link, or special price discount: '{chosen_cta_instruction}'.
5. Follow this layout structure strictly to keep the narrative logical: {structure_layout}.
6. CRITICAL: Enforce strict duplicate sentence prevention. Do NOT repeat the same thought, phrase, or sentence anywhere in the script.
7. CRITICAL: Zero-tolerance for incorrect botanical context:
   - For Jasmine: focus on starry white flowers, sweet evening fragrance, climbers, ready-to-bloom nursery quality. NEVER mention 'thick cool leaves', 'gel', or 'succulent'.
   - For Snake Plant: focus on air-purifying, NASA clean air, bedroom low-light. NEVER mention 'blooming flowers' or 'sweet scents'.
   - For Aloe Vera: focus on soothing medicinal gel, succulents, drought-resistant. NEVER describe it as a climber.
8. Weave plant care tips naturally into a compelling sales narrative rather than listing raw parameters.
9. Provide a complete timeline of captions with start and end times in seconds, aligning with scenes.

Output MUST be a strict, valid JSON object containing EXACTLY these keys:
- "title": (Catchy video title)
- "hook": (Catchy opening hook phrase, 0-10 seconds)
- "script_text": (The full spoken narrative, smooth and conversational, no brackets or stage directions)
- "scene_breakdown": (Array of objects with "scene" number, "instruction" for visuals, and "voiceover" text matching script_text)
- "caption_timeline": (Array of objects with "start", "end" in seconds, and "text" of the voiceover)
- "thumbnail_text": (Short bold overlay text for thumbnail, 2-4 words)
- "seo_description": (SEO-friendly description with relevant search keywords naturally integrated)
- "hashtags": (Array of 3-4 trending hashtags, e.g. ["#PlantCare", "#ArecaPalm"])
"""
                if force_feedback:
                    prompt += f"\n\nFEEDBACK FROM PREVIOUS RUN: {force_feedback}. Adjust the script to resolve these issues."

                logger.info(f"Ollama script generation attempt {attempt} using style '{style}'...")
                import json
                response = llm.invoke(prompt)
                
                raw_content = response.content.strip()
                if raw_content.startswith("```"):
                    raw_content = re.sub(r'^```(?:json)?\s*', '', raw_content)
                    raw_content = re.sub(r'\s*```$', '', raw_content)
                    raw_content = raw_content.strip()
                
                script_data = json.loads(raw_content)
                required_keys = ["title", "hook", "script_text", "scene_breakdown", "caption_timeline", "thumbnail_text", "seo_description", "hashtags"]
                if all(k in script_data for k in required_keys):
                    
                    # Programmatic Self-Healing Deduplication
                    cleaned_scenes = []
                    seen_sentences = []
                    for item in script_data.get("scene_breakdown", []):
                        vo = item.get("voiceover", "")
                        if not vo:
                            continue
                        vo_sentences = re.split(r'(?<=[.!?])\s+', vo)
                        cleaned_vo_parts = []
                        for s in vo_sentences:
                            s_clean = re.sub(r'[^\w\s]', '', s.lower()).strip()
                            if not s_clean:
                                continue
                            is_dup = False
                            for prev in seen_sentences:
                                if difflib.SequenceMatcher(None, s_clean, prev).ratio() > 0.75:
                                    is_dup = True
                                    break
                            if not is_dup:
                                seen_sentences.append(s_clean)
                                cleaned_vo_parts.append(s)
                        
                        if cleaned_vo_parts:
                            item["voiceover"] = " ".join(cleaned_vo_parts)
                            cleaned_scenes.append(item)
                    
                    script_data["scene_breakdown"] = cleaned_scenes
                    script_data["script_text"] = " ".join(s["voiceover"] for s in cleaned_scenes)
                    
                    # Rebuild timeline
                    caption_timeline = []
                    current_time = 0.0
                    for item in cleaned_scenes:
                        words_count = len(item["voiceover"].split())
                        duration = min(7.0, max(2.5, words_count * 0.35))
                        caption_timeline.append({
                            "start": round(current_time, 1),
                            "end": round(current_time + duration, 1),
                            "text": item["voiceover"]
                        })
                        current_time += duration
                    script_data["caption_timeline"] = caption_timeline
                    
                    # Botanical statement validation
                    is_valid_facts = self.validate_botanical_script(product_name, script_data["script_text"])
                    is_duplicate = self.check_duplicate_threshold(script_data["script_text"])
                    
                    if is_valid_facts and not is_duplicate:
                        if isinstance(script_data["scene_breakdown"], list) and len(script_data["scene_breakdown"]) > 0:
                            script_data["scene_breakdown"][-1]["meta"] = {
                                "style": style,
                                "platform": platform,
                                "hook_category": "llm_generated"
                            }
                        logger.info(f"Successfully generated unique script via LLM in style: {style}")
                        return script_data
                    else:
                        logger.info(f"LLM script rejected. Facts valid: {is_valid_facts}, Duplicate: {is_duplicate}. Retrying...")
                        style, platform = self.select_script_parameters()
                        style_info = SCRIPT_STYLES[style]
                        chosen_cta_instruction = random.choice(CTA_STYLES)
                else:
                    logger.warning(f"LLM output missing required keys: {[k for k in required_keys if k not in script_data]}")
            except Exception as e:
                logger.error(f"Error on LLM script generation attempt {attempt}: {e}")
                
        logger.info("LLM script generation failed or returned duplicates. Falling back to Combinatorial Procedural Generator...")
        proc_script = self.procedural_generate(product_name, description, style, platform, rag_context, product_context)
        return proc_script

# Global instance
script_generator_svc = ScriptGeneratorEngine()
