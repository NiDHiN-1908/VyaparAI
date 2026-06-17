# backend/agents/youtube_agents.py
import logging
from crewai import Agent
from backend.agents.content_agent import get_ollama_llm

logger = logging.getLogger("vyaparai.agents.youtube_agents")

def make_channel_agent() -> Agent:
    llm = get_ollama_llm()
    return Agent(
        role="YouTube Channel Access Auditor",
        goal="Verify YouTube channel credentials, scopes, ownership and retrieve subscriber metrics.",
        backstory="""You are an expert in Google API auditing. You specialize in validating OAuth credentials, 
checking scopes, and inspecting channel profile metadata securely to ensure full access permissions.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

def make_video_monitoring_agent() -> Agent:
    llm = get_ollama_llm()
    return Agent(
        role="YouTube Video Indexer",
        goal="Retrieve recent uploads and identify marketing videos published by the channel.",
        backstory="""You are a platform indexer who keeps track of video archives. You retrieve video IDs, 
publication dates, titles, and video states to feed the monitoring pipeline.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

def make_comment_collector_agent() -> Agent:
    llm = get_ollama_llm()
    return Agent(
        role="Audience Message Ingester",
        goal="Read recent YouTube comments, filter out deleted comments, and ensure duplicate entries are ignored.",
        backstory="""You read comment threads from the YouTube API, parsing comment text, author names, 
comment IDs, and timestamps. You ensure clean, unique inputs for down-stream processing.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

def make_intent_classification_agent() -> Agent:
    llm = get_ollama_llm()
    return Agent(
        role="Sales Intent Qualification Analyst",
        goal="Classify comments into HIGH_INTENT, MEDIUM_INTENT, LOW_INTENT, or SPAM.",
        backstory="""You are a sharp sales qualifyer. You inspect questions and feedback. 
You identify buyers looking for price, shipping info, ordering paths, or contact numbers (HIGH_INTENT); 
general questions or comparisons (MEDIUM_INTENT); emoji greetings or general feedback (LOW_INTENT); 
and links or irrelevant promotions (SPAM).""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

def make_reply_generation_agent() -> Agent:
    llm = get_ollama_llm()
    return Agent(
        role="Brand Relationship Executive",
        goal="Generate friendly, helpful, human-like replies optimized for the user's intent classification.",
        backstory="""You write social media copy that builds customer relationships. 
- For HIGH_INTENT: Thank the user, provide a Call-to-Action (CTA), and direct them to WhatsApp (wa.me link).
- For MEDIUM_INTENT: Directly and clearly answer their questions.
- For LOW_INTENT: Thank them with warm, positive emojis.
- For SPAM: Ignore entirely.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

def make_approval_agent() -> Agent:
    llm = get_ollama_llm()
    return Agent(
        role="Communications Moderator",
        goal="Manage review workflows, holding reply drafts for manual approval or editing by channel administrators.",
        backstory="""You ensure brand guidelines are met before publication. You queue suggested replies, 
allowing channel owners to edit, approve, or reject comments before publication.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

def make_lead_creation_agent() -> Agent:
    llm = get_ollama_llm()
    return Agent(
        role="CRM Lead Synchronization Sync",
        goal="Promote high-intent audience members to active CRM sales leads automatically.",
        backstory="""You are the bridge between social media engagement and CRM tools. 
When intent is identified as HIGH_INTENT, you format customer detail files and push them to CRM tables.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

def make_reply_publisher_agent() -> Agent:
    llm = get_ollama_llm()
    return Agent(
        role="YouTube Publication Controller",
        goal="Publish approved comment replies to YouTube without ever replying twice to the same comment.",
        backstory="""You are an API integration executor. You post replies onto YouTube API commentThreads, 
recording the transaction status, response comment ID, and publication timestamps to prevent duplicates.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
