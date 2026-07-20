// frontend/app/agent-details/page.tsx
"use client";

import { useState } from "react";
import { 
  Cpu, 
  ShieldCheck, 
  Zap, 
  ChevronRight, 
  Workflow, 
  TrendingUp, 
  FileText, 
  Image as ImageIcon, 
  Video, 
  MessageSquare, 
  Users, 
  Smartphone, 
  BarChart3, 
  Activity, 
  Languages, 
  Sparkles, 
  Terminal, 
  CheckCircle2, 
  Bot, 
  Play, 
  Search
} from "lucide-react";

interface AgentDef {
  id: string;
  name: string;
  role: string;
  category: "crew" | "social" | "sales" | "core";
  goal: string;
  technique: string;
  method: string;
  engine: string;
  icon: any;
  gradient: string;
  badgeBg: string;
  metric: string;
  tools: string[];
  sampleLog: string[];
}

const AGENTS: AgentDef[] = [
  {
    id: "coordinator",
    name: "Coordinator Agent",
    role: "System Orchestration Director",
    category: "core",
    goal: "Map multi-agent pipelines, distribute asynchronous tasks, manage stage gates, and coordinate state handoffs.",
    technique: "Planning-Based Prompting & State Guarding",
    method: "Sequential & Parallel Handoff Routing",
    engine: "CrewAI Orchestration Engine",
    icon: Workflow,
    gradient: "from-indigo-500 to-purple-600",
    badgeBg: "bg-indigo-500/10 border-indigo-500/30 text-indigo-400",
    metric: "100% Pipeline Guarding",
    tools: ["StateGraph Router", "Task Dispatcher", "Memory Buffer"],
    sampleLog: [
      "[INFO] Initialized marketing pipeline request #7829",
      "[INFO] Dispatching parallel tasks to TrendAgent & ScriptAgent",
      "[SUCCESS] Stage gate 1 passed. Handoff to VideoAgent ready."
    ]
  },
  {
    id: "trend",
    name: "Trend Agent",
    role: "SEO Keyword Trend Analyst",
    category: "crew",
    goal: "Scrape regional Google/YouTube search volume trends to extract high-traffic, low-competition keywords.",
    technique: "Zero-Shot Regional Keyword Extraction",
    method: "Keyword Density & Volatility Evaluation",
    engine: "Ollama Llama 3.1 + PyTrends API",
    icon: TrendingUp,
    gradient: "from-cyan-500 to-blue-600",
    badgeBg: "bg-cyan-500/10 border-cyan-500/30 text-cyan-400",
    metric: "1,250 Keywords Audited",
    tools: ["SerpAPI", "YouTube Search Scraper", "NLP Tokenizer"],
    sampleLog: [
      "[SEARCH] Auditing top search queries for 'Jasmine Plant Care'",
      "[EXTRACT] Found 14 high-intent keywords in Malayalam & English",
      "[OUTPUT] Selected target keyword: 'Jasmine blooming tips Kerala'"
    ]
  },
  {
    id: "script",
    name: "Script Agent",
    role: "Creative Marketing Copywriter",
    category: "crew",
    goal: "Generate high-converting, regional ad scripts with attention-grabbing hooks, story arcs, and platform CTAs.",
    technique: "Role-Prompting & Cultural Contextualization",
    method: "Chain-of-Thought (CoT) Copywriting",
    engine: "Ollama Llama 3.1 8B Instruct",
    icon: FileText,
    gradient: "from-purple-500 to-pink-600",
    badgeBg: "bg-purple-500/10 border-purple-500/30 text-purple-400",
    metric: "98.2% Hook Retention",
    tools: ["Commercial Script Templates", "Tone Modifier", "CTA Injector"],
    sampleLog: [
      "[GENERATE] Drafting 30-sec script for 'Jasmine Plant Care'",
      "[HOOK] 'Hey plant lovers! Most people kill their Jasmine plant because...'",
      "[SUCCESS] Script generated with Malayalam subtitle alignment."
    ]
  },
  {
    id: "thumbnail",
    name: "Thumbnail Agent",
    role: "Visual Layout & Prompter",
    category: "crew",
    goal: "Generate visual contrast blueprints and detailed prompt descriptions for high-click video thumbnails.",
    technique: "Structured Image Blueprinting",
    method: "Visual Contrast & Rule-of-Thirds Analysis",
    engine: "Pillow Graphics + DALL-E Prompt Builder",
    icon: ImageIcon,
    gradient: "from-pink-500 to-rose-600",
    badgeBg: "bg-pink-500/10 border-pink-500/30 text-pink-400",
    metric: "High Click-Through Optimization",
    tools: ["Canvas Engine", "Image Asset Manager", "Color Contrast Validator"],
    sampleLog: [
      "[PROMPT] Composing high-contrast prompt: 'Vibrant blooming Jasmine in terra cotta pot'",
      "[CANVAS] Rendering text overlay: 'SECRET HIGH-BLOOM TIPS'",
      "[SUCCESS] Thumbnail asset created: /media/thumb_jasmine.jpg"
    ]
  },
  {
    id: "video",
    name: "Video Agent",
    role: "Background Video Renderer",
    category: "crew",
    goal: "Compile product media, audio voiceovers, dynamic captions, and background audio into MP4 video shorts.",
    technique: "Dynamic Scripting & Subtitle Mapping",
    method: "FFmpeg Pipeline Acceleration",
    engine: "MoviePy + gTTS Voice Synthesizer",
    icon: Video,
    gradient: "from-rose-500 to-red-600",
    badgeBg: "bg-rose-500/10 border-rose-500/30 text-rose-400",
    metric: "FFmpeg Hardware Rendering",
    tools: ["gTTS Engine", "FFmpeg Renderer", "Unicode Subtitle Embedder"],
    sampleLog: [
      "[TTS] Synthesizing voiceover audio in Malayalam: 28.4 sec duration",
      "[FFMPEG] Stitching video frames with ASS subtitle overlay",
      "[COMPLETED] Exported MP4: /static/media/prod_jasmine_short.mp4"
    ]
  },
  {
    id: "comment",
    name: "Comment Agent",
    role: "YouTube Comment Monitor",
    category: "social",
    goal: "Poll YouTube comment feeds in real-time, classify purchase intent, and publish automated deep-link replies.",
    technique: "Few-Shot Intent Classification",
    method: "Regex Pattern & LLM Hybrid Classifier",
    engine: "YouTube Data API v3 + Ollama",
    icon: MessageSquare,
    gradient: "from-emerald-500 to-teal-600",
    badgeBg: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
    metric: "< 5s Intent Qualification",
    tools: ["YouTube API Connector", "Intent Classifier", "Trackable Link Generator"],
    sampleLog: [
      "[POLL] Checked comment stream for Video ID: yv_781920",
      "[INTENT] Commenter @sunil_kerala asked 'How to buy this plant?' -> Classified BUYING_INTENT",
      "[REPLY] Published reply with trackable WhatsApp link wa.me/919000000000?text=BUY_JASMINE"
    ]
  },
  {
    id: "lead",
    name: "Lead Agent",
    role: "CRM Lead Ingester",
    category: "sales",
    goal: "Capture qualified comment authors and WhatsApp contacts into structured database CRM profiles.",
    technique: "Structured Entity Extraction",
    method: "Database Record Normalization",
    engine: "Supabase Postgres Service",
    icon: Users,
    gradient: "from-amber-500 to-orange-600",
    badgeBg: "bg-amber-500/10 border-amber-500/30 text-amber-400",
    metric: "Instant Lead Record Ingestion",
    tools: ["Supabase Lead Table", "CRM Lead Matcher", "Geo Tagging"],
    sampleLog: [
      "[INGEST] Processing new lead: @sunil_kerala",
      "[DB] Saved lead record: ID lead_89127 (Product: Jasmine Plant)",
      "[ANALYTICS] Incremented total qualified leads counter +1"
    ]
  },
  {
    id: "whatsapp",
    name: "WhatsApp Agent",
    role: "Conversational Checkout Assistant",
    category: "sales",
    goal: "Manage interactive customer checkouts, answer plant care FAQs via RAG, collect shipping details, and issue UPI links.",
    technique: "Contextual RAG & Self-Correction Prompting",
    method: "State-Machine Directed Conversational Checkout",
    engine: "LangGraph + ChromaDB Vector Store",
    icon: Smartphone,
    gradient: "from-emerald-400 to-green-600",
    badgeBg: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
    metric: "Stateful Sales State Graph",
    tools: ["LangGraph StateGraph", "RAG Retriever", "Pincode Validator", "UPI Generator"],
    sampleLog: [
      "[STATE] Active chat stage: ADDRESS_COLLECTION",
      "[VALIDATE] User address verified: Pincode 686001, Street: MG Road",
      "[PAYMENT] Generated UPI Payment URL: http://localhost:8000/payment/simulate?order=9012"
    ]
  },
  {
    id: "analytics",
    name: "Analytics Agent",
    role: "Business Performance Reporter",
    category: "core",
    goal: "Aggregate real-time metrics across video views, comment volume, lead conversions, and store revenue.",
    technique: "Structured Aggregations & Telemetry",
    method: "Data Trend & Sales Forecasting",
    engine: "FastAPI Analytics Engine",
    icon: BarChart3,
    gradient: "from-blue-500 to-indigo-600",
    badgeBg: "bg-blue-500/10 border-blue-500/30 text-blue-400",
    metric: "Real-time Telemetry Feed",
    tools: ["Revenue Metrics Aggregator", "Conversion Funnel Calculator", "Chart Dataset Builder"],
    sampleLog: [
      "[CALCULATE] Summing completed orders for Jasmine Plant",
      "[AGGREGATE] Total Revenue: Rs. 1,480.00 across 12 orders",
      "[METRIC] Conversion Rate updated: 41.6%"
    ]
  },
  {
    id: "monitoring",
    name: "Monitoring Agent",
    role: "System Diagnostics Inspector",
    category: "core",
    goal: "Monitor process health, detect network drops, inspect background worker logs, and execute self-healing actions.",
    technique: "Deterministic Health Validation",
    method: "Step-by-Step System Diagnostics Routing",
    engine: "Python Process Supervisor",
    icon: Activity,
    gradient: "from-rose-400 to-red-600",
    badgeBg: "bg-rose-500/10 border-rose-500/30 text-rose-400",
    metric: "Self-Healing Uptime Guard",
    tools: ["Process Health Checker", "Task Log Inspector", "Tunnel Restarter"],
    sampleLog: [
      "[HEALTHCHECK] Polling FastAPI server at http://localhost:8000/health",
      "[STATUS] Backend status: 200 OK. Memory: 142MB",
      "[SUCCESS] All background task workers operating nominally."
    ]
  },
  {
    id: "response",
    name: "Response Agent",
    role: "Regional Language Copy Editor",
    category: "social",
    goal: "Translate, localize, and refine final customer responses in regional Indian languages (Hindi, Malayalam, Tamil, Telugu).",
    technique: "Dynamic Contextual Translation",
    method: "Cross-Lingual Copy Validation",
    engine: "Ollama Regional Translation Layer",
    icon: Languages,
    gradient: "from-violet-500 to-purple-600",
    badgeBg: "bg-violet-500/10 border-violet-500/30 text-violet-400",
    metric: "Multi-regional Indian Support",
    tools: ["Unicode Script Formatter", "Regional Phrase Dictionary", "Grammar Auditor"],
    sampleLog: [
      "[TRANSLATE] Source text: 'Namaste! Welcome to VyaparAI Nursery.'",
      "[LOCALIZE] Target language: Malayalam",
      "[OUTPUT] 'നമസ്കാരം! Green Haven Nursery-ലേക്ക് സ്വാഗതം.'"
    ]
  }
];

export default function AgentDetailsPage() {
  const [selectedId, setSelectedId] = useState<string>("coordinator");
  const [activeCategory, setActiveCategory] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [simulationLog, setSimulationLog] = useState<string[]>([]);

  const filteredAgents = AGENTS.filter(agent => {
    const matchesCategory = activeCategory === "all" || agent.category === activeCategory;
    const matchesSearch = agent.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          agent.role.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          agent.goal.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const selectedAgent = AGENTS.find(a => a.id === selectedId) || filteredAgents[0] || AGENTS[0];
  const IconComponent = selectedAgent.icon;

  const runSimulatedInspection = () => {
    setIsSimulating(true);
    setSimulationLog(["[INIT] Connection to Agent Runtime Environment initialized..."]);
    
    setTimeout(() => {
      setSimulationLog(prev => [...prev, `[EXEC] Querying ${selectedAgent.name} state parameters...`]);
    }, 600);

    setTimeout(() => {
      setSimulationLog(prev => [...prev, ...selectedAgent.sampleLog]);
      setIsSimulating(false);
    }, 1400);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-16">
      {/* Header Banner */}
      <div className="relative overflow-hidden p-8 rounded-3xl bg-slate-900/80 border border-slate-800/80 shadow-2xl backdrop-blur-xl">
        <div className="absolute -right-12 -top-12 w-72 h-72 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -left-12 -bottom-12 w-72 h-72 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 text-indigo-400 text-xs font-extrabold uppercase tracking-widest px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20">
              <Cpu className="w-3.5 h-3.5" />
              Autonomous Agent Architecture Reference
            </div>
            <h1 className="text-3xl md:text-4xl font-black tracking-tight text-white">
              Agent Specifications <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">&amp; Command Suite</span>
            </h1>
            <p className="text-slate-300 text-sm max-w-2xl leading-relaxed font-medium">
              Technical specifications, prompt strategies, reasoning methods, and live execution logs for all 11 autonomous AI agents driving VyaparAI.
            </p>
          </div>

          <div className="flex items-center gap-3 self-start md:self-auto">
            <div className="px-4 py-2.5 rounded-2xl bg-slate-950/80 border border-slate-800 flex items-center gap-2.5 text-xs font-bold text-slate-200">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
              <span className="text-emerald-400">11 Agents Active</span>
            </div>
          </div>
        </div>
      </div>

      {/* Category Filter & Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-md">
        {/* Category Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-2 sm:pb-0">
          {[
            { id: "all", label: "All 11 Agents" },
            { id: "crew", label: "Marketing Crew" },
            { id: "social", label: "Social Monitor" },
            { id: "sales", label: "Sales & Checkout" },
            { id: "core", label: "Core System" }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveCategory(tab.id)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap ${
                activeCategory === tab.id
                  ? "bg-indigo-600 text-white shadow-lg shadow-indigo-500/20"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-64">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search agents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 text-xs rounded-xl bg-slate-950/80 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
          />
        </div>
      </div>

      {/* Main Grid: Selection List (Left) + Detailed Inspector (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left Side: Agent Selection List (5 cols) */}
        <div className="lg:col-span-5 space-y-2.5 max-h-[750px] overflow-y-auto pr-1">
          {filteredAgents.map((agent) => {
            const isSelected = selectedId === agent.id;
            const ItemIcon = agent.icon;
            return (
              <button
                key={agent.id}
                onClick={() => {
                  setSelectedId(agent.id);
                  setSimulationLog([]);
                }}
                className={`w-full p-4 rounded-2xl text-left transition-all relative overflow-hidden group border ${
                  isSelected 
                    ? "bg-slate-900 border-indigo-500/60 shadow-xl shadow-indigo-500/10" 
                    : "bg-slate-900/40 border-slate-800/60 hover:bg-slate-900/80 hover:border-slate-700"
                }`}
              >
                {/* Selected left accent bar */}
                {isSelected && (
                  <div className={`absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b ${agent.gradient}`} />
                )}

                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className={`p-2.5 rounded-xl ${agent.badgeBg}`}>
                      <ItemIcon className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-xs font-extrabold text-white group-hover:text-indigo-300 transition">
                        {agent.name}
                      </h4>
                      <p className="text-[10px] text-slate-400 font-medium truncate max-w-[180px] mt-0.5">
                        {agent.role}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-extrabold uppercase px-2 py-0.5 rounded-md bg-slate-950 text-slate-400 border border-slate-800">
                      {agent.category}
                    </span>
                    <ChevronRight className={`w-4 h-4 transition-transform ${isSelected ? "translate-x-0.5 text-indigo-400" : "text-slate-600"}`} />
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Right Side: Detailed Agent Showcase Inspector (7 cols) */}
        <div className="lg:col-span-7 p-7 backdrop-blur-xl bg-slate-900/70 border border-slate-800/80 rounded-3xl shadow-2xl space-y-6 relative overflow-hidden">
          {/* Background Ambient Glow */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

          {/* Agent Header Info */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-800/80">
            <div className="flex items-center gap-4">
              <div className={`p-3.5 rounded-2xl bg-gradient-to-br ${selectedAgent.gradient} shadow-lg text-white`}>
                <IconComponent className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xl font-black text-white">{selectedAgent.name}</h3>
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    ACTIVE
                  </span>
                </div>
                <p className="text-xs text-indigo-400 font-bold uppercase tracking-wider mt-0.5">
                  {selectedAgent.role}
                </p>
              </div>
            </div>

            <button
              onClick={runSimulatedInspection}
              disabled={isSimulating}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 transition shadow-lg shadow-indigo-500/25 active:scale-95 disabled:opacity-50 self-start sm:self-auto"
            >
              <Play className={`w-3.5 h-3.5 ${isSimulating ? "animate-spin" : ""}`} />
              {isSimulating ? "Inspecting..." : "Test Workflow"}
            </button>
          </div>

          {/* Core Goal Box */}
          <div className="p-5 rounded-2xl bg-slate-950/70 border border-slate-800 space-y-2">
            <div className="flex items-center gap-2 text-[10px] font-extrabold text-indigo-400 uppercase tracking-widest">
              <Bot className="w-3.5 h-3.5" />
              Agent Mission &amp; Autonomous Goal
            </div>
            <p className="text-xs text-slate-200 leading-relaxed font-medium">
              {selectedAgent.goal}
            </p>
          </div>

          {/* Prompt Strategy & Reasoning Architecture */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-4 rounded-2xl bg-slate-950/50 border border-slate-850 flex items-start gap-3">
              <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 mt-0.5">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div>
                <span className="text-[10px] text-slate-500 font-extrabold uppercase tracking-wider block">
                  Prompting Strategy
                </span>
                <span className="text-xs font-bold text-white mt-0.5 block">
                  {selectedAgent.technique}
                </span>
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-slate-950/50 border border-slate-850 flex items-start gap-3">
              <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400 mt-0.5">
                <Zap className="w-4 h-4" />
              </div>
              <div>
                <span className="text-[10px] text-slate-500 font-extrabold uppercase tracking-wider block">
                  Reasoning Method
                </span>
                <span className="text-xs font-bold text-white mt-0.5 block">
                  {selectedAgent.method}
                </span>
              </div>
            </div>
          </div>

          {/* Active Tools & Capabilities Badges */}
          <div className="space-y-2.5">
            <span className="text-[10px] font-extrabold text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              Connected Tools &amp; Service Connectors
            </span>
            <div className="flex flex-wrap gap-2">
              {selectedAgent.tools.map((tool, idx) => (
                <div
                  key={idx}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-slate-950 border border-slate-800 text-[11px] font-semibold text-slate-300"
                >
                  <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                  <span>{tool}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Terminal Execution Inspector Log */}
          <div className="p-4 rounded-2xl bg-slate-950 border border-slate-850 space-y-2.5">
            <div className="flex items-center justify-between text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              <span className="flex items-center gap-1.5 text-indigo-400">
                <Terminal className="w-3.5 h-3.5" />
                Live Agent Execution Log Stream
              </span>
              <span className="text-[9px] text-slate-500">Ollama Llama 3.1 Trace</span>
            </div>

            <div className="font-mono text-[11px] space-y-1 max-h-36 overflow-y-auto text-slate-300">
              {(simulationLog.length > 0 ? simulationLog : selectedAgent.sampleLog).map((line, i) => (
                <div
                  key={i}
                  className={
                    line.includes("SUCCESS") || line.includes("COMPLETED")
                      ? "text-emerald-400 font-semibold"
                      : line.includes("HOOK") || line.includes("INTENT")
                      ? "text-indigo-300 font-semibold"
                      : "text-slate-400"
                  }
                >
                  {line}
                </div>
              ))}
            </div>
          </div>

          {/* Footer Metadata */}
          <div className="pt-4 border-t border-slate-800/60 flex items-center justify-between text-[10px] font-bold text-slate-400">
            <span>Runtime: <strong className="text-slate-200">{selectedAgent.engine}</strong></span>
            <span>Performance: <strong className="text-emerald-400">{selectedAgent.metric}</strong></span>
          </div>

        </div>

      </div>
    </div>
  );
}
