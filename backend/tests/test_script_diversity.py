# backend/tests/test_script_diversity.py
import pytest
from backend.services.script_generator import script_generator_svc, BOTANICAL_DB

# Define the 10 target plants and their details for validation
TARGET_PLANTS = [
    {
        "name": "Rose Plant",
        "description": "Healthy flowering rose plant available in multiple colors such as red, pink, yellow, and white.",
        "expected_keywords": ["rose", "bloom", "fragran", "flower", "garden", "color"]
    },
    {
        "name": "Aloe Vera",
        "description": "Nursery-grown aloe vera succulent with medicinal properties, ideal for skin care and minor burns.",
        "expected_keywords": ["aloe", "gel", "skin", "medicinal", "burn", "succulent"]
    },
    {
        "name": "Snake Plant",
        "description": "Air-purifying snake plant, highly recommended by NASA studies, ideal for bedrooms and low maintenance.",
        "expected_keywords": ["snake", "bedroom", "oxygen", "nasa", "toxin", "purif"]
    },
    {
        "name": "Money Plant",
        "description": "Lush money plant climber, perfect for indoor decor, water propagation, and bringing good luck.",
        "expected_keywords": ["money", "feng", "luck", "water", "propagat", "grow"]
    },
    {
        "name": "Orchid",
        "description": "Exquisite flowering orchid plant with unique air roots, humidity loving, bringing premium luxury style.",
        "expected_keywords": ["orchid", "bloom", "air root", "humidity", "luxury", "exotic"]
    },
    {
        "name": "Jasmine",
        "description": "Intense fragrant night blooming jasmine climber, perfect for trellises and natural calming essential oils.",
        "expected_keywords": ["jasmine", "fragran", "sweet", "climb", "night", "calm"]
    },
    {
        "name": "Bonsai",
        "description": "Zen miniature bonsai tree trained using traditional ancient Japanese wiring and pruning techniques.",
        "expected_keywords": ["bonsai", "zen", "miniature", "prun", "wir", "patience"]
    },
    {
        "name": "Areca Palm",
        "description": "Elegant indoor areca palm, pet safe for cats and dogs, acting as a natural air humidifier and purifier.",
        "expected_keywords": ["palm", "areca", "pet", "humidifier", "toxin", "tropical"]
    },
    {
        "name": "Peace Lily",
        "description": "Beautiful shade loving peace lily with white spathes, filters mold spores and droops leaves when thirsty.",
        "expected_keywords": ["peace", "lily", "droop", "thirsty", "spathe", "shade"]
    },
    {
        "name": "Cactus",
        "description": "Low maintenance succulent cactus with beautiful needles, perfect for bright sunny windowsills.",
        "expected_keywords": ["cactus", "spine", "needle", "desert", "water", "sunny"]
    }
]

def test_script_generation_keys_and_customization():
    """Verify that every generated script contains all necessary keys, unique hooks/CTAs,

    and product-specific knowledge.
    """
    generated_scripts = []
    
    for plant in TARGET_PLANTS:
        # Generate script using our service
        script = script_generator_svc.generate(
            product_name=plant["name"],
            description=plant["description"]
        )
        
        # 1. Assert keys exist
        required_keys = ["title", "hook", "script_text", "scene_breakdown", "caption_timeline", "thumbnail_text", "seo_description", "hashtags"]
        for key in required_keys:
            assert key in script, f"Missing key '{key}' in generated script for {plant['name']}"
            
        # 2. Check hook is unique/populated
        assert len(script["hook"].strip()) > 10, f"Hook is too short for {plant['name']}"
        
        # 3. Check call to action has 'Link' requirement
        script_text = script["script_text"].lower()
        assert "link" in script_text, f"CTA does not instruct viewers to comment 'Link' in {plant['name']} script"
        
        # 4. Check product-specific botanical knowledge is present
        found_kw = False
        for kw in plant["expected_keywords"]:
            if kw in script_text or kw in script["hook"].lower() or kw in script["title"].lower():
                found_kw = True
                break
        assert found_kw, f"Script for {plant['name']} lacks product-specific botanical keywords: {plant['expected_keywords']}. Script: {script_text}"
        
        # 5. Check pacing/timeline durations are valid and incremental
        timeline = script["caption_timeline"]
        assert len(timeline) > 0
        last_end = 0.0
        for entry in timeline:
            assert entry["start"] >= last_end, "Timeline start should be sequential"
            assert entry["end"] > entry["start"], "Timeline entry duration should be positive"
            last_end = entry["end"]
            
        generated_scripts.append(script)
        
    # Verify pairwise similarity between all generated scripts is less than 70%
    for i in range(len(generated_scripts)):
        for j in range(i + 1, len(generated_scripts)):
            s1 = generated_scripts[i]["script_text"]
            s2 = generated_scripts[j]["script_text"]
            sim = script_generator_svc.compute_similarity(s1, s2)
            assert sim < 0.70, f"Scripts between {TARGET_PLANTS[i]['name']} and {TARGET_PLANTS[j]['name']} have similarity {sim:.2f} which exceeds the 70% limit."

def test_duplicate_detection_and_similarity():
    """Verify that compute_similarity correctly identifies high similarity and

    triggers duplicate rejection rules.
    """
    s1 = "This is a beautiful Rose Plant for your garden. It has amazing flowers and fragrance."
    s2 = "This is a beautiful Rose Plant for your garden! It has amazing flowers and fragrance!"
    s3 = "Want to keep a Snake Plant in your bedroom? NASA studies show it helps filter out indoor toxins and xylene."
    
    # High similarity (>70%)
    sim_high = script_generator_svc.compute_similarity(s1, s2)
    assert sim_high > 0.90
    
    # Low similarity (<70%)
    sim_low = script_generator_svc.compute_similarity(s1, s3)
    assert sim_low < 0.55

def test_botanical_validation_and_leakage():
    from backend.crews.marketing_crew import MarketingCrew
    crew = MarketingCrew()
    
    # Generate Aloe Vera (succulent)
    aloe_ctx = crew.run_product_agent("Aloe Vera", "Medicinal gel succulent plant")
    aloe_script = crew.run_script_agent_with_validation(aloe_ctx)
    aloe_text = aloe_script["script_text"].lower()
    assert "gel" in aloe_text or "succulent" in aloe_text
    
    # Generate Jasmine (climber, flower, fragrance)
    jasmine_ctx = crew.run_product_agent("Jasmine", "Intense fragrant flowering climber")
    jasmine_script = crew.run_script_agent_with_validation(jasmine_ctx)
    jasmine_text = jasmine_script["script_text"].lower()
    
    # Assert zero leakage of succulent-related terms into Jasmine
    forbidden = ["gel", "succulent", "aloe", "water storage", "thick cool leaves"]
    for word in forbidden:
        assert word not in jasmine_text, f"Leakage detected: '{word}' found in Jasmine script!"

def test_deduplication_and_cta_rotation():
    from backend.crews.marketing_crew import MarketingCrew
    crew = MarketingCrew()
    
    # Check that sentence deduplication works
    text_with_dups = "There is a beautiful rose. There is a beautiful rose! Grow your plants today."
    cleaned = script_generator_svc.deduplicate_script_text(text_with_dups)
    assert cleaned.count("beautiful rose") == 1
    
    # Check CTA rotation
    jasmine_ctx = crew.run_product_agent("Jasmine", "Intense fragrant flowering climber")
    cta_set = set()
    for _ in range(5):
        script = crew.run_script_agent_with_validation(jasmine_ctx)
        vo = script["script_text"]
        # Try to find matching CTA phrase
        cta_set.add(script["scene_breakdown"][-1]["voiceover"].strip())
    
    # Verification of CTA rotation
    assert len(cta_set) > 1, f"No CTA rotation detected: only got {cta_set}"
