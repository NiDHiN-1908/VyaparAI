# backend/crews/marketing_crew.py
import os
import json
import logging
import random
from typing import Dict, Any, List
from crewai import Crew, Task, Process

from backend.agents.keyword_agent import make_keyword_agent
from backend.agents.trend_agent import make_trend_agent, get_trending_keywords
from backend.agents.script_agent import make_script_agent
from backend.agents.thumbnail_agent import make_thumbnail_agent
from backend.agents.quality_agent import make_quality_agent, audit_campaign_quality
from backend.agents.publishing_agent import make_publishing_agent

from backend.services.voice_service import voice_svc
from backend.services.video_service import video_svc
from backend.services.youtube_publishing_service import youtube_publish_svc
from backend.services.supabase_service import supabase_svc
from backend.config import settings

logger = logging.getLogger("vyaparai.crews.marketing_crew")

def get_randomized_script_data(product_name: str, description: str) -> dict:
    text = (product_name + " " + description).lower()
    
    # Classify product category
    if any(kw in text for kw in ["paint", "coating", "emulsion", "varnish", "primer", "acrylic", "wall painting"]):
        category = "Paint"
    elif any(kw in text for kw in ["phone", "laptop", "battery", "led", "screen", "sensor", "camera", "headphone", "device", "charge", "electronics"]):
        category = "Electronics"
    elif any(kw in text for kw in ["saree", "shirt", "pant", "shoe", "dress", "clothing", "fabric", "silk", "cotton", "wear", "fashion"]):
        category = "Fashion"
    elif any(kw in text for kw in ["table", "chair", "sofa", "desk", "bed", "furniture", "woodwork", "cabinet"]):
        category = "Furniture"
    elif any(kw in text for kw in ["cream", "lotion", "serum", "lipstick", "soap", "shampoo", "beauty", "cosmetic", "skincare"]):
        category = "Beauty"
    elif any(kw in text for kw in ["car", "bike", "engine", "motor", "tyre", "automotive", "vehicle", "brake"]):
        category = "Automotive"
    elif any(kw in text for kw in ["software", "app", "saas", "dashboard", "platform", "database", "crm", "automation"]):
        category = "Software"
    elif any(kw in text for kw in ["medicine", "tablet", "health", "clinical", "capsule", "doctor", "care", "supplement"]):
        category = "Healthcare"
    elif any(kw in text for kw in ["cardamom", "coconut", "oil", "food", "beverage", "tea", "coffee", "spice", "honey", "juice", "fresh", "organic", "farm", "harvest", "fruit", "vegetable"]):
        category = "Food"
    else:
        category = "Other"

    # Define pool arrays according to category
    if category == "Paint":
        titles = [
            f"Transform your space with premium {product_name}! 🎨",
            f"The secret to a flawless {product_name} finish ✨",
            f"Say goodbye to fading walls! Meet our {product_name} 🏡",
            f"Achieve perfect coverage with {product_name} today! 🖌️"
        ]
        hooks = [
            f"Tired of fading walls and uneven finish? 🚫 Experience the incredible coverage and color richness of our {product_name}!",
            f"Want to protect your home from harsh weather? 🌧️ Here is why our premium {product_name} is the ultimate shield.",
            f"Looking for long-lasting durability on your walls? ✨ Meet the next generation of wall protection: {product_name}."
        ]
        bodies = [
            f"Introducing our eco-friendly, low-odor {product_name}. Formulated for outstanding washability and protection, it ensures value for money with high coverage.",
            f"Our premium {product_name} provides a rich, smooth finish with extreme weather resistance. Easy to apply, quick-drying, and designed to protect your surfaces."
        ]
        ctas = [
            f"Reply now to get a professional shade consultation and 10% off your first order!",
            f"Message us today to check available colors and claim free delivery across India!",
            f"Comment below or DM us now to get direct catalog pricing and save big!"
        ]
        thumbnail_texts = [
            f"Premium {product_name}!",
            "Flawless Finish!",
            "100% Durable Paint!"
        ]
        seo_descriptions = [
            f"Buy premium quality {product_name} online. High coverage, long-lasting durability, and rich finish quality.",
            f"Get weather-resistant and washable {product_name} at the best price. Low odor and eco-friendly formulation."
        ]
        hashtags_pool = [
            ["PremiumPaint", "WallDecor", "HomeImprovement"],
            ["ColorRichness", "PaintDesign", "EcoFriendlyPaint"]
        ]
        scene1_instr = f"Show a high-quality visual of the fresh coat of {product_name} being applied on a wall."
        scene2_instr = f"Show close-up highlights of the smooth wall finish and label details."
        scene3_instr = f"Show a clean call-to-action screen with order instructions."

    elif category == "Electronics":
        titles = [
            f"Why this {product_name} is the ultimate tech upgrade! ⚡",
            f"Experience next-gen innovation with {product_name} 📱",
            f"Unboxing the most reliable {product_name} in India 🇮🇳",
            f"Is this the best performance {product_name}? Let's check 🔍"
        ]
        hooks = [
            f"Struggling with slow performance and short battery life? 🔋 Step up to the future of innovation with {product_name}!",
            f"Want a device you can count on? ⚙️ Discover the unmatched reliability and premium features of {product_name}.",
            f"Did you know this {product_name} packs industry-leading speed? ⚡ Let's look at its advanced tech connectivity."
        ]
        bodies = [
            f"Discover the power of {product_name}. Featuring industry-leading performance, long-lasting battery life, and innovative connectivity designed to streamline your daily tasks.",
            f"Engineered for ultimate reliability, {product_name} brings cutting-edge tech features to your fingertips with a sleek design and blazing-fast performance."
        ]
        ctas = [
            f"Reply now to get the full specifications sheet and a special launch discount!",
            f"Message us today to secure your order with a 1-year warranty!",
            f"Comment below or DM us now to buy with free shipping and cash on delivery!"
        ]
        thumbnail_texts = [
            f"Smart {product_name}!",
            "Next-Gen Tech!",
            "Max Performance!"
        ]
        seo_descriptions = [
            f"Order the highly reliable and high-performance {product_name} online with a warranty.",
            f"Discover next-gen features and outstanding battery life with premium {product_name}."
        ]
        hashtags_pool = [
            ["SmartTech", "Innovation", "Electronics"],
            ["HighPerformance", "GadgetReview", "ReliableTech"]
        ]
        scene1_instr = f"Show a sleek close-up of {product_name} highlighting its premium build."
        scene2_instr = f"Show the device in action highlighting interface and screen details."
        scene3_instr = f"Show order options and discount code."

    elif category == "Fashion":
        titles = [
            f"Elevate your daily style with {product_name}! 👗",
            f"The perfect blend of style and comfort: {product_name} ✨",
            f"Unboxing the finest quality {product_name} in India 🇮🇳"
        ]
        hooks = [
            f"Tired of stiff clothing that doesn't fit right? 🚫 Experience the premium material quality and comfort of {product_name}!",
            f"Want to stand out with timeless style? 🌟 Dress to impress in our custom-designed {product_name}.",
            f"Looking for the softest fabric and a perfect fit? 🧵 Meet the premium selection of {product_name}."
        ]
        bodies = [
            f"Upgrade your wardrobe with {product_name}. Crafted from premium quality material, it features a comfortable fit and modern style that is perfect for any occasion.",
            f"Experience fashion that moves with you. Our {product_name} combines breathable fabrics, superior fit, and exquisite craftsmanship for all-day comfort."
        ]
        ctas = [
            f"Reply now to see our complete size chart and get 15% off!",
            f"Message us to check availability and get free custom fitting!",
            f"Comment 'STYLE' below to get catalog access and special pricing!"
        ]
        thumbnail_texts = [
            f"Stylish {product_name}!",
            "Premium Fit!",
            "Top Comfort!"
        ]
        seo_descriptions = [
            f"Shop stylish and comfortable {product_name} online. Premium material quality and perfect fit.",
            f"Upgrade your look with the finest {product_name} available in multiple sizes and custom designs."
        ]
        hashtags_pool = [
            ["FashionStyle", "Ootd", "PremiumQuality"],
            ["ComfortFit", "WearLocal", "SareeFashion"]
        ]
        scene1_instr = f"Show a beautiful model wearing the elegant {product_name} in clean lighting."
        scene2_instr = f"Show close-up of the fabric texture and high-quality stitch work."
        scene3_instr = f"Show sizing details and purchase buttons."

    elif category == "Furniture":
        titles = [
            f"Upgrade your home with custom {product_name}! 🛋️",
            f"Craftsmanship meets durability: {product_name} ✨",
            f"Say goodbye to flimsy furniture! Meet {product_name} 🏡"
        ]
        hooks = [
            f"Looking for the perfect combination of comfort and design? 🏡 Transform your living space with our elegant {product_name}!",
            f"Want furniture that lasts for generations? 🪵 Discover the robust durability and premium craftsmanship of {product_name}."
        ]
        bodies = [
            f"Introducing {product_name}. Expertly crafted with premium materials, it ensures lifelong durability, stunning aesthetic design, and comfort that welcomes you home.",
            f"Maximize your home comfort with {product_name}. Handcrafted using select wood and premium fabrics to ensure superior support and custom design."
        ]
        ctas = [
            f"Reply now to get custom measurements and free home delivery!",
            f"Message us today to claim our special housewarming bundle offer!",
            f"Comment below or DM us to get custom color and wood stain options!"
        ]
        thumbnail_texts = [
            f"Elegant {product_name}!",
            "Handcrafted!",
            "Top Comfort!"
        ]
        seo_descriptions = [
            f"Buy custom handcrafted {product_name} online. Durable design, premium wood, and maximum comfort.",
            f"Enhance your home decor with premium {product_name} crafted to perfection with high durability."
        ]
        hashtags_pool = [
            ["HomeFurniture", "InteriorDesign", "Craftsmanship"],
            ["LivingRoomDecor", "CustomFurniture", "DurableDesign"]
        ]
        scene1_instr = f"Show {product_name} beautifully arranged in a modern living space."
        scene2_instr = f"Show detailed close-ups of the joints, woodwork, or cushion textures."
        scene3_instr = f"Show customization choices and contact details."

    elif category == "Beauty":
        titles = [
            f"Get the ultimate natural glow with {product_name}! ✨",
            f"Say goodbye to dry skin! Meet {product_name} 💧",
            f"Secrets of the highest quality skincare with {product_name} 🤫"
        ]
        hooks = [
            f"Tired of dry, dull skin? 💧 Experience the deep hydration and active skin benefits of {product_name}!",
            f"Want to unlock your skin's natural glow? 🌟 Discover the premium formulation of our {product_name}."
        ]
        bodies = [
            f"Reveal your skin's natural glow with {product_name}. Powered by nourishing ingredients, it provides intense hydration and targeted skincare benefits for a radiant complexion.",
            f"Pamper your skin with the ultimate care. Our {product_name} is designed to soothe, hydrate, and nourish with dermatologically tested ingredients."
        ]
        ctas = [
            f"Reply now to get a free dermatologist recommendation and 10% off!",
            f"Message us to check availability and get free shipping on your bottle!",
            f"Comment 'GLOW' below to get ordering details and special discounts!"
        ]
        thumbnail_texts = [
            f"Radiant {product_name}!",
            "Natural Glow!",
            "Pure Hydration!"
        ]
        seo_descriptions = [
            f"Shop premium {product_name} online. Nourishing ingredients, hydration, and natural glow skincare.",
            f"Dermatologist tested {product_name} for hydration and anti-aging benefits. Order online."
        ]
        hashtags_pool = [
            ["SkincareGlow", "BeautyTips", "Hydration"],
            ["SelfCareRoutine", "NourishSkin", "HealthyGlow"]
        ]
        scene1_instr = f"Show soft lighting hitting a clean bottle of {product_name}."
        scene2_instr = f"Show smooth application of the product on clean skin."
        scene3_instr = f"Show checkout link and discount details."

    elif category == "Automotive":
        titles = [
            f"Enhance your vehicle's performance with {product_name}! 🚗",
            f"Maximum protection for your ride: {product_name} 🛠️",
            f"Why everyone is switching to our {product_name} today! ⚡"
        ]
        hooks = [
            f"Want to extend your engine's lifespan and improve reliability? 🛠️ Protect your ride with premium {product_name}.",
            f"Tired of poor fuel efficiency and high maintenance? ⛽ Discover how {product_name} optimizes performance."
        ]
        bodies = [
            f"Give your vehicle the care it deserves. {product_name} is engineered to optimize performance, enhance fuel efficiency, and provide complete protection under extreme conditions.",
            f"Keep your engine running like new. Our {product_name} provides superior wear protection, reducing friction and maximizing thermal reliability."
        ]
        ctas = [
            f"Reply now to check compatibility with your vehicle model!",
            f"Message us today to claim our engine diagnostic voucher!",
            f"Comment below to find authorized retailers and workshop pricing!"
        ]
        thumbnail_texts = [
            f"High Performance!",
            "Max Protection!",
            "Engine Reliability!"
        ]
        seo_descriptions = [
            f"Buy high-performance {product_name} for your vehicle. Extreme wear protection and fuel efficiency.",
            f"Improve engine life and vehicle reliability with premium {product_name} online."
        ]
        hashtags_pool = [
            ["CarMaintenance", "Automotive", "Performance"],
            ["Reliability", "EngineCare", "VehicleProtection"]
        ]
        scene1_instr = f"Show a high-quality visual of a modern engine bay or vehicle in action."
        scene2_instr = f"Show the detailed installation or application of {product_name}."
        scene3_instr = f"Show application guide and ordering contact."

    elif category == "Software":
        titles = [
            f"Streamline your workflow with {product_name}! 💻",
            f"Boost your business productivity using {product_name} 🚀",
            f"Why everyone is switching to {product_name} today! 🔥"
        ]
        hooks = [
            f"Wasting hours on manual processes? ⚙️ Boost your team's productivity and efficiency with {product_name}!",
            f"Struggling to sync your tools? 🔗 Discover the powerful automation and seamless integrations of {product_name}."
        ]
        bodies = [
            f"Take control of your operations with {product_name}. Our platform offers powerful automation, seamless integration, and advanced analytics to supercharge your business efficiency.",
            f"Simplify your workflow with our secure cloud software. {product_name} automates repetitive admin work, giving your team hours back every week."
        ]
        ctas = [
            f"Reply now to book a free 15-minute demo and start a free trial!",
            f"Message us to get a custom onboarding plan for your business!",
            f"Comment below or DM us 'DEMO' to get a direct signup link!"
        ]
        thumbnail_texts = [
            f"Smart {product_name}!",
            "10x Efficiency!",
            "Automation Software!"
        ]
        seo_descriptions = [
            f"Boost productivity and automate your business operations with {product_name} software.",
            f"Start your free trial of {product_name} for seamless integrations and workflow efficiency."
        ]
        hashtags_pool = [
            ["BusinessAutomation", "SaaS", "Productivity"],
            ["WorkflowEfficiency", "TechTools", "SoftwarePlatform"]
        ]
        scene1_instr = f"Show a clean, modern dashboard interface of {product_name}."
        scene2_instr = f"Show screens highlighting automation tasks and analytics details."
        scene3_instr = f"Show details on how to book a demo."

    elif category == "Healthcare":
        titles = [
            f"Prioritize your well-being with premium {product_name} 🩺",
            f"Support your daily health routine with {product_name} ✨",
            f"Why doctors recommend our {product_name}! 🔍"
        ]
        hooks = [
            f"Looking for reliable support for your daily vitality? 🌟 Discover the advanced formulation of {product_name}.",
            f"Tired of low energy and wellness products that don't deliver? 💊 Try the trusted support of {product_name}."
        ]
        bodies = [
            f"Help support your active lifestyle with {product_name}. Our formula features premium, clinically tested ingredients designed to aid recovery and general well-being.",
            f"Crafted to meet the highest safety standards, {product_name} offers reliable daily protection and vitality support for your whole family."
        ]
        ctas = [
            f"Reply now to check safety credentials and get a 10% discount!",
            f"Message us today to view lab reports and claim free delivery!",
            f"Comment below or DM us to ask our wellness specialists any questions!"
        ]
        thumbnail_texts = [
            f"Healthy {product_name}!",
            "Clinically Approved!",
            "Daily Wellness!"
        ]
        seo_descriptions = [
            f"Buy clinically tested {product_name} online. Daily health support, safety checked, and premium ingredients.",
            f"Support your health and wellness goals with doctor-recommended {product_name}."
        ]
        hashtags_pool = [
            ["HealthWellness", "Supplement", "DailyCare"],
            ["DoctorRecommended", "WellnessJourney", "HealthyLiving"]
        ]
        scene1_instr = f"Show clean, professional packaging of {product_name} in a clinical setting."
        scene2_instr = f"Show detailed labels and quality control seals."
        scene3_instr = f"Show links to medical disclaimer and checkout page."

    elif category == "Food":
        titles = [
            f"The secret behind pure, fresh {product_name} 🍃",
            f"Sourced fresh: premium {product_name} direct to your home 🏡",
            f"Say goodbye to stale {product_name}! Sourced fresh 📦",
            f"Is your {product_name} actually pure? Let's check 🔍",
            f"From local farms to your home: {product_name} 🏡"
        ]
        hooks = [
            f"Are you tired of artificial, preservative-filled foods? 🚫 Sourced directly from fresh local farms, our {product_name} is as pure and organic as it gets!",
            f"If you're still buying normal market products, stop! 🛑 Here is why our premium {product_name} is completely different.",
            f"Want to know what real quality feels like? ✨ Let's talk about our fresh, handpicked {product_name}."
        ]
        bodies = [
            f"Experience the natural goodness of pure {product_name}. Handpicked by local farmers, vacuum-sealed, and shipped fresh to preserve active nutrients and flavor. No preservatives or additives.",
            f"Experience the rich aroma of pure {product_name}. Cold-pressed and traditionally harvested under organic controls to guarantee maximum potency and freshness in every pack."
        ]
        ctas = [
            f"Reply now to get an exclusive 10% discount and free shipping on your first pack!",
            f"Message us today to claim our special launch offer: Buy 2 Get 1 Free!",
            f"Hurry! Tap the link or reply to this post to order your pack before stocks run out."
        ]
        thumbnail_texts = [
            f"Pure {product_name}!",
            "100% Organic!",
            "Farm Fresh!"
        ]
        seo_descriptions = [
            f"Buy premium quality organic {product_name} online with nationwide shipping. Cash on delivery available.",
            f"Order fresh, preservative-free {product_name} directly from local farms. Best price and guaranteed authenticity."
        ]
        hashtags_pool = [
            ["FarmFresh", "OrganicSpices", "HealthyLiving"],
            ["PureNatural", "DirectToConsumer", "FreshHarvest"]
        ]
        scene1_instr = f"Show a high-quality visual of the fresh {product_name} in a beautiful rustic setting."
        scene2_instr = f"Show product packaging with close-up highlights of the organic labels and fresh seal."
        scene3_instr = f"Show a clean call-to-action screen with order instructions and a discount badge."

    else:  # Other / Generic / Neutral
        titles = [
            f"Why this {product_name} is a game changer! 💥",
            f"Unboxing the best {product_name} in India 🇮🇳",
            f"Why everyone is switching to our {product_name} today! 🔥",
            f"Secrets of the highest quality {product_name} revealed! 🤫"
        ]
        hooks = [
            f"Looking for a reliable solution? 🌟 Discover the unmatched quality and premium features of our {product_name}.",
            f"Tired of compromises? 🛑 Here is why our premium {product_name} stands out from other market options."
        ]
        bodies = [
            f"Introducing our premium {product_name}. Sourced with high quality standards, it is designed to offer exceptional performance, value, and reliability.",
            f"Experience the next level of quality with {product_name}. Engineered to meet strict standards and ensure a superior experience."
        ]
        ctas = [
            f"Reply now to get an exclusive launch discount and order yours today!",
            f"Message us today to ask any questions or check pricing options!",
            f"Comment below or DM us 'ORDER' to get instant delivery updates!"
        ]
        thumbnail_texts = [
            f"Premium {product_name}!",
            "Best Quality!",
            "Top Choice!"
        ]
        seo_descriptions = [
            f"Buy premium {product_name} online. Trusted quality, outstanding value, and nationwide shipping.",
            f"Get high quality {product_name} at the best price. Cash on delivery and warranty available."
        ]
        hashtags_pool = [
            ["LocalVyapar", "PremiumQuality", "IndianMade"],
            ["VocalForLocal", "BusinessOwner", "HealthyChoices"]
        ]
        scene1_instr = f"Show a high-quality visual of the {product_name}."
        scene2_instr = f"Show close-ups of product build and quality features."
        scene3_instr = f"Show purchase details and link."

    title = random.choice(titles)
    hook = random.choice(hooks)
    body = random.choice(bodies)
    cta = random.choice(ctas)
    thumbnail_text = random.choice(thumbnail_texts)
    seo_desc = random.choice(seo_descriptions)
    
    full_script_text = f"{hook} {body} {cta}"
    
    scene_breakdown = [
        {
            "scene": 1,
            "instruction": scene1_instr,
            "voiceover": hook
        },
        {
            "scene": 2,
            "instruction": scene2_instr,
            "voiceover": body
        },
        {
            "scene": 3,
            "instruction": scene3_instr,
            "voiceover": cta
        }
    ]
    
    cap1_end = min(7.0, len(hook.split()) * 0.4)
    cap2_end = cap1_end + min(7.0, len(body.split()) * 0.4)
    cap3_end = cap2_end + min(7.0, len(cta.split()) * 0.4)
    
    caption_timeline = [
        {"start": 0.0, "end": round(cap1_end, 1), "text": hook},
        {"start": round(cap1_end, 1), "end": round(cap2_end, 1), "text": body},
        {"start": round(cap2_end, 1), "end": round(cap3_end, 1), "text": cta}
    ]
    
    clean_product_name = "".join(c for c in product_name if c.isalnum())
    tags = [clean_product_name] + random.choice(hashtags_pool)
    
    return {
        "title": title,
        "hook": hook,
        "script_text": full_script_text,
        "scene_breakdown": scene_breakdown,
        "caption_timeline": caption_timeline,
        "thumbnail_text": thumbnail_text,
        "seo_description": seo_desc,
        "hashtags": tags
    }

class MarketingCrew:
    def __init__(self):
        self.keyword_agent = make_keyword_agent()
        self.trend_agent = make_trend_agent()
        self.script_agent = make_script_agent()
        self.thumbnail_agent = make_thumbnail_agent()
        self.quality_agent = make_quality_agent()
        self.publishing_agent = make_publishing_agent()

    def run(
        self, 
        product_name: str, 
        description: str, 
        location: str, 
        product_images: List[str] = None,
        force_feedback: str = None,
        version: int = 1
    ) -> Dict[str, Any]:
        """
        Executes the expanded 8-agent CrewAI pipeline.
        Implements QualityAgent scoring and dynamic regeneration loop.
        """
        logger.info(f"Initiating Expanded Marketing Crew for product: {product_name} (Version: {version})")
        
        # Define image count string for prompt
        image_count = len(product_images) if product_images else 0
        img_info = f"Product has {image_count} visual images uploaded."

        # Step 1: Keyword Classification Task
        keyword_task = Task(
            description=f"""Analyze the product name: '{product_name}' and description: '{description}'.
Determine the target market. Categorize and generate:
- Primary Keywords (core product terms)
- Secondary Keywords (associated snack/craft tags)
- Long Tail Keywords (longer search phrases)
- Purchase Intent Keywords (e.g. 'buy', 'order')
- Regional Keywords (relating to local Indian regions/states)""",
            expected_output="JSON structure mapping: primary, secondary, long_tail, intent, regional",
            agent=self.keyword_agent
        )

        # Step 2: Trend Analysis Task
        trend_task = Task(
            description=f"Analyze search demand signals in location '{location}' for product '{product_name}'. List 10 viral video topics and 3 optimized SEO titles.",
            expected_output="JSON structure mapping: trending_topics, seo_titles",
            agent=self.trend_agent
        )

        # Step 3: Script Generation Task
        styles = [
            "storytelling (narrating a journey of how the product was created)",
            "highly energetic (hooking the viewer with fast-paced, high impact benefits)",
            "dramatic unboxing (focusing on the visual details and first impressions of the package)",
            "problem-solving (starting directly with a severe pain point the product solves)",
            "customer-testimony (speaking from the perspective of a passionate, satisfied buyer)",
            "educational (sharing an interesting fact or secret tip about the product category)",
            "casual local recommendation (speaking like a friendly neighbor sharing a great discovery)"
        ]
        chosen_style = random.choice(styles)
        
        script_desc = f"""Create a promotional script bundle for the specific product: '{product_name}'.
Product Description: {description}

IMPORTANT DIRECTIVES:
1. Identify the core product and exactly what makes it unique.
2. Formulate a unique sales strategy tailored to THIS exact product. Do not use generic templates.
3. Write completely innovative dialogues and hooks for this video. Avoid repeating past formats.
4. Write in a '{chosen_style}' style. Make it extremely unique and distinct from standard copies.

Output MUST be a JSON object containing EXACTLY these keys:
- "title"
- "hook" (0-10 sec, attention grabber)
- "script_text" (The full spoken narrative)
- "scene_breakdown" (Array of objects with "scene", "instruction", "voiceover")
- "caption_timeline" (Array of objects with "start", "end", "text")
- "thumbnail_text"
- "seo_description"
- "hashtags" (Array of strings)

Ensure the voice is warm, clear, and engaging.
{img_info}"""
        
        if force_feedback:
            script_desc += f"\n\nREGENERATION FEEDBACK FROM PREVIOUS AUDIT: {force_feedback}. Make sure to fix these points in this version."

        script_task = Task(
            description=script_desc,
            expected_output="JSON structure matching script layout tags.",
            agent=self.script_agent
        )

        # Step 4: Thumbnail Creation Task
        thumbnail_task = Task(
            description=f"Design a high-CTR thumbnail for '{product_name}'. Suggest a layout configuration, overlay text, and a prompt for image generation models.",
            expected_output="JSON structure mapping: layout, text, prompt",
            agent=self.thumbnail_agent
        )

        # Create Sequential Crew
        crew = Crew(
            agents=[self.keyword_agent, self.trend_agent, self.script_agent, self.thumbnail_agent],
            tasks=[keyword_task, trend_task, script_task, thumbnail_task],
            process=Process.sequential,
            verbose=True
        )

        # Kickoff Crew
        try:
            crew.kickoff()
            logger.info("Crew execution completed. Compiling and auditing results...")
        except Exception as e:
            logger.warning(f"CrewAI execution failed: {e}. Falling back to default campaign assets.")

        # Formulate fallback records to ensure resilient executions
        primary_kws = [f"{product_name} online", f"buy {product_name}"]
        secondary_kws = [f"handmade {product_name}", f"traditional {product_name}"]
        long_tail_kws = [f"best {product_name} in India", f"order organic {product_name} online"]
        intent_kws = [f"buy {product_name}", f"order {product_name} price"]
        regional_kws = [f"{product_name} south india", f"{product_name} kerala"]

        topics = [
            f"Why this {product_name} is going viral",
            f"How traditional {product_name} is made",
            f"Top 5 benefits of {product_name}"
        ]
        
        # Helper to parse agent output
        def extract_json(task_output):
            if not task_output:
                logger.warning("extract_json received None task_output")
                return None
            
            # Check for json_dict first
            json_dict = getattr(task_output, "json_dict", None)
            if json_dict and isinstance(json_dict, dict):
                logger.info("Found parsed json_dict in task_output")
                return json_dict
            
            # Retrieve raw text
            raw_text = getattr(task_output, "raw", None)
            if not raw_text:
                raw_text = getattr(task_output, "raw_output", None)
            
            if not raw_text:
                if isinstance(task_output, str):
                    raw_text = task_output
                else:
                    logger.warning(f"task_output has no raw or raw_output. Type: {type(task_output)}")
                    return None
            
            logger.info(f"Extracted raw text (first 200 chars): {raw_text[:200]}")
            
            import re
            cleaned = raw_text.strip()
            # Clean markdown code block wraps
            if cleaned.startswith("```"):
                cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
                cleaned = re.sub(r'\s*```$', '', cleaned)
                cleaned = cleaned.strip()
            
            try:
                parsed = json.loads(cleaned)
                logger.info("Successfully parsed cleaned raw JSON directly")
                return parsed
            except Exception as e:
                logger.info(f"Direct JSON load failed: {e}. Trying regex extraction...")
            
            # Try finding a JSON object using regex
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                    logger.info("Successfully parsed regex-matched JSON")
                    return parsed
                except Exception as e:
                    logger.warning(f"Regex JSON loads failed: {e}")
            
            return None

        # Attempt to parse keywords from agent output
        keyword_data = extract_json(keyword_task.output)
        if keyword_data:
            primary_kws = keyword_data.get("primary", primary_kws)
            secondary_kws = keyword_data.get("secondary", secondary_kws)
            long_tail_kws = keyword_data.get("long_tail", long_tail_kws)
            intent_kws = keyword_data.get("intent", intent_kws)
            regional_kws = keyword_data.get("regional", regional_kws)
            logger.info(f"Successfully extracted custom keywords: {primary_kws}")
        else:
            logger.warning("Using hardcoded fallback keywords")

        # Attempt to parse trending topics from agent output
        trend_data = extract_json(trend_task.output)
        if trend_data:
            topics = trend_data.get("trending_topics", topics)
            logger.info(f"Successfully extracted custom trending topics: {topics}")
        else:
            logger.warning("Using hardcoded fallback topics")

        # Attempt to parse script data from agent output
        script_data = extract_json(script_task.output)

        if script_data and isinstance(script_data, dict):
            # Ensure all required keys exist to prevent KeyError
            required_keys = ["title", "hook", "script_text", "scene_breakdown", "caption_timeline", "thumbnail_text", "seo_description", "hashtags"]
            missing_keys = [k for k in required_keys if k not in script_data]
            if missing_keys:
                logger.warning(f"Script data is missing keys: {missing_keys}. Filling with dynamic fallback values.")
                rand_data = get_randomized_script_data(product_name, description)
                for k in missing_keys:
                    script_data[k] = rand_data[k]
        else:
            logger.warning("Failed to parse script JSON from agent. Using default fallback template.")
            script_data = get_randomized_script_data(product_name, description)

        thumbnail_data = extract_json(thumbnail_task.output)
        
        if thumbnail_data and isinstance(thumbnail_data, dict):
            if "layout" not in thumbnail_data:
                thumbnail_data["layout"] = "Product centered with bold yellow text overlay on dark slate background"
            if "text" not in thumbnail_data:
                thumbnail_data["text"] = script_data.get("thumbnail_text", f"Pure {product_name}!")
            if "prompt" not in thumbnail_data:
                thumbnail_data["prompt"] = f"Close-up photo of {product_name} on a wooden table, soft warm lighting, 8k resolution"
        else:
            thumbnail_data = {
                "layout": random.choice([
                    "Product centered with bold yellow text overlay on dark slate background",
                    "Premium packaging showcase with clean minimalist typography",
                    "Rustic close-up with bold organic badges and text overlay"
                ]),
                "text": script_data.get("thumbnail_text", f"Pure {product_name}!"),
                "prompt": random.choice([
                    f"Close-up photo of {product_name} on a wooden table, soft warm lighting, 8k resolution",
                    f"A beautiful rustic bowl overflowing with fresh {product_name}, dark moody background, studio lighting",
                    f"Premium packaging of {product_name} standing elegantly on a marble slab, natural sun rays"
                ])
            }

        # Quality Check Loop
        qa_result = audit_campaign_quality(script_data, primary_kws + long_tail_kws, product_name=product_name)
        
        # Simulate regeneration once if QA score fails (or if forced for loop testing)
        if qa_result["status"] == "REGENERATE" and version < 2:
            logger.warning("Quality score < 80. Triggering automatic regeneration loop...")
            return self.run(
                product_name=product_name,
                description=description,
                location=location,
                product_images=product_images,
                force_feedback=qa_result["feedback"],
                version=version + 1
            )

        # Generate physical custom thumbnail image file
        thumbnail_filename = f"thumbnail_v{version}_{os.urandom(4).hex()}.png"
        try:
            thumbnail_url = video_svc.generate_thumbnail(
                image_paths=product_images or [],
                text=thumbnail_data["text"],
                output_filename=thumbnail_filename
            )
            thumbnail_data["image_url"] = thumbnail_url
            logger.info(f"Custom thumbnail image generated: {thumbnail_url}")
        except Exception as e:
            logger.error(f"Failed to generate physical thumbnail image: {e}")
            thumbnail_data["image_url"] = None

        # Translations, voiceovers and video rendering pipeline in parallel
        from concurrent.futures import ThreadPoolExecutor

        languages = ["English", "Hindi", "Tamil", "Telugu", "Malayalam"]
        translations_dict = {}
        voiceovers_dict = {}
        videos_dict = {}

        def process_lang(lang):
            logger.info(f"Starting pipeline for language: {lang}")
            try:
                # Generate translated script texts (mock / IndicTrans2 wrapper fallback)
                from backend.agents.translation_agent import translate_content_indictrans2
                translated_reel = translate_content_indictrans2(script_data["script_text"], lang)
                
                lang_translations = {
                    "youtube_script": translate_content_indictrans2(script_data["script_text"], lang),
                    "reel_script": translated_reel,
                    "whatsapp_post": translate_content_indictrans2(script_data["seo_description"], lang),
                    "google_business_post": translate_content_indictrans2(script_data["title"], lang)
                }

                # Generate Voiceover MP3
                audio_filename = f"voiceover_{lang.lower()}_v{version}_{os.urandom(4).hex()}.mp3"
                audio_path = voice_svc.generate_voiceover(translated_reel, lang, audio_filename)
                
                # Dynamically load audio duration to ensure precise metadata sync
                try:
                    from moviepy.editor import AudioFileClip
                    audio_clip = AudioFileClip(audio_path)
                    audio_duration = audio_clip.duration
                    audio_clip.close()
                except Exception:
                    audio_duration = 10.0

                lang_voiceover = {
                    "audio_url": f"/static/media/{audio_filename}",
                    "local_path": audio_path,
                    "duration": audio_duration
                }

                # Generate Video MP4 with multi-photo support and subtitle timed rendering
                video_filename = f"video_{lang.lower()}_v{version}_{os.urandom(4).hex()}.mp4"
                video_path = video_svc.generate_marketing_video(
                    audio_path=audio_path,
                    image_paths=product_images,
                    voiceover_text=translated_reel,
                    output_filename=video_filename
                )

                lang_video = {
                    "video_url": f"/static/media/{video_filename}",
                    "local_path": video_path
                }
                
                logger.info(f"Finished pipeline successfully for language: {lang}")
                return lang, lang_translations, lang_voiceover, lang_video
            except Exception as e:
                logger.error(f"Error in processing pipeline for language {lang}: {e}")
                # Return fallbacks so the entire pipeline doesn't crash if one language fails
                fallback_audio = f"voiceover_{lang.lower()}_v{version}_fallback.mp3"
                fallback_video = f"video_{lang.lower()}_v{version}_fallback.mp4"
                return (
                    lang,
                    {
                        "youtube_script": script_data["script_text"],
                        "reel_script": script_data["script_text"],
                        "whatsapp_post": script_data["seo_description"],
                        "google_business_post": script_data["title"]
                    },
                    {
                        "audio_url": f"/static/media/{fallback_audio}",
                        "local_path": "",
                        "duration": 10.0
                    },
                    {
                        "video_url": f"/static/media/{fallback_video}",
                        "local_path": ""
                    }
                )

        # Run translations, voiceovers, and videos in parallel threads
        with ThreadPoolExecutor(max_workers=len(languages)) as executor:
            results = list(executor.map(process_lang, languages))

        for lang, lang_translations, lang_voiceover, lang_video in results:
            translations_dict[lang] = lang_translations
            voiceovers_dict[lang] = lang_voiceover
            videos_dict[lang] = lang_video

        return {

            "version": version,
            "qa_score": qa_result["score"],
            "qa_status": qa_result["status"],
            "keywords": {
                "primary": primary_kws,
                "secondary": secondary_kws,
                "long_tail": long_tail_kws,
                "intent": intent_kws,
                "regional": regional_kws
            },
            "topics": topics,
            "script": script_data,
            "thumbnail": thumbnail_data,
            "translations": translations_dict,
            "voiceovers": voiceovers_dict,
            "videos": videos_dict
        }

marketing_crew = MarketingCrew()
