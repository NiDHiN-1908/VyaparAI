// frontend/app/module-details/page.tsx
"use client";

import { useState } from "react";
import { 
  Layers, 
  Database, 
  ArrowRight, 
  Video, 
  MessageSquare, 
  Film, 
  Bot, 
  Zap, 
  Workflow, 
  Activity, 
  Sparkles, 
  Code, 
  CheckCircle2, 
  Terminal, 
  Play, 
  Search, 
  Server, 
  ChevronRight,
  ShieldCheck
} from "lucide-react";

interface ModuleDef {
  id: string;
  name: string;
  category: "integration" | "rendering" | "sales" | "infra";
  desc: string;
  type: string;
  status: string;
  latency: string;
  icon: any;
  gradient: string;
  badgeBg: string;
  inputs: string[];
  transformation: string;
  outputs: string[];
  samplePayload: string;
}

const MODULES: ModuleDef[] = [
  {
    id: "yt-ingester",
    name: "YouTube Data API Ingester",
    category: "integration",
    desc: "Polls connected channel uploads, indexes comment streams every 5 seconds, classifies buyer intent, and queues automated replies.",
    type: "OAuth 2.0 REST Webhook",
    status: "Active / Polling",
    latency: "1.2s avg poll",
    icon: Video,
    gradient: "from-red-500 to-rose-600",
    badgeBg: "bg-red-500/10 border-red-500/30 text-red-400",
    inputs: ["YouTube Access Token", "Channel ID", "Video Comment Stream"],
    transformation: "Runs hybrid regular expression matching + Ollama Llama 3.1 intent classification to detect buying inquiries.",
    outputs: ["Qualified Lead Profiles", "Deep-link WhatsApp Replies", "Comment Analytics Records"],
    samplePayload: `{
  "event": "YOUTUBE_COMMENT_RECEIVED",
  "channel_id": "UC_vyapar_nursery",
  "video_id": "yv_98271",
  "comment": "How much for the Jasmine plant? Deliver to Kerala?",
  "intent": "BUYING_INTENT",
  "confidence": 0.96
}`
  },
  {
    id: "wa-evolution",
    name: "Evolution WhatsApp Gateway",
    category: "integration",
    desc: "Manages live WhatsApp instances, registers inbound webhooks, processes customer media, and dispatches stateful agent responses.",
    type: "WebSocket & Webhook Gateway",
    status: "Connected",
    latency: "350ms response",
    icon: MessageSquare,
    gradient: "from-emerald-500 to-teal-600",
    badgeBg: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
    inputs: ["WhatsApp Business Webhook", "Evolution API Key", "Customer Phone Number"],
    transformation: "Parses incoming chat payloads, maintains conversation thread IDs, and invokes the LangGraph Sales Workflow graph.",
    outputs: ["Inbound Webhook Events", "Interactive Catalog Dialogues", "UPI Payment Buttons"],
    samplePayload: `{
  "event": "MESSAGES_UPSERT",
  "instance": "VyaparNursery",
  "data": {
    "key": { "remoteJid": "919000000000@s.whatsapp.net" },
    "message": { "conversation": "I want to buy 2 Rose Plants in Kottayam 686001" }
  }
}`
  },
  {
    id: "render-queue",
    name: "FFmpeg Video Rendering Pipeline",
    category: "rendering",
    desc: "Asynchronously compiles high-resolution plant imagery, regional TTS voiceovers, ASS subtitles, and background audio into MP4 Shorts.",
    type: "Background Worker Queue",
    status: "Worker Active",
    latency: "8.4s / 30s clip",
    icon: Film,
    gradient: "from-pink-500 to-rose-600",
    badgeBg: "bg-pink-500/10 border-pink-500/30 text-pink-400",
    inputs: ["Product Spec Script", "gTTS Regional Audio", "Plant JPG Images"],
    transformation: "Executes FFmpeg filtergraphs, overlays dynamic Unicode subtitles (Malayalam, Hindi, Tamil), and burns commercial CTA banners.",
    outputs: ["HD 1080x1920 MP4 Video Shorts", "Thumbnail Assets", "Render Job Logs"],
    samplePayload: `{
  "job_id": "render_job_9812",
  "status": "COMPLETED",
  "video_path": "/static/media/prod_jasmine_short.mp4",
  "duration_sec": 28.5,
  "subtitles_embedded": true,
  "language": "Malayalam"
}`
  },
  {
    id: "langgraph-engine",
    name: "LangGraph Conversational Sales Engine",
    category: "sales",
    desc: "Stateful dialogue graph managing welcome flows, product info Q&A, plant care FAQs via RAG, strict address validation, and UPI payments.",
    type: "LangGraph StateGraph",
    status: "Engine Running",
    latency: "420ms inference",
    icon: Bot,
    gradient: "from-indigo-500 to-purple-600",
    badgeBg: "bg-indigo-500/10 border-indigo-500/30 text-indigo-400",
    inputs: ["Customer Chat Message", "Current Sales State", "Vector Store Context"],
    transformation: "Evaluates state transitions (WELCOME -> QA_LOOP -> ADDRESS_COLLECTION -> PAYMENT), verifies pincode/street rules, and computes discounts.",
    outputs: ["Verified Shipping Address", "Order Summary & Discounts", "Simulated UPI Payment Link"],
    samplePayload: `{
  "state": "ADDRESS_COLLECTION",
  "lead_id": "lead_98127",
  "product_id": "prod_jasmine_102",
  "address_verified": true,
  "pincode": "686001",
  "total_cost": 120.0,
  "next_node": "PAYMENT"
}`
  },
  {
    id: "supabase-db",
    name: "Supabase Postgres & Realtime Store",
    category: "infra",
    desc: "Central relational & vector data store. Maintains products, leads, orders, campaign logs, and analytics telemetry.",
    type: "PostgreSQL Database",
    status: "Online / Syncing",
    latency: "12ms query",
    icon: Database,
    gradient: "from-amber-500 to-orange-600",
    badgeBg: "bg-amber-500/10 border-amber-500/30 text-amber-400",
    inputs: ["Product Schemas", "Customer Orders", "Telemetry Records"],
    transformation: "Provides ACID-compliant storage with automatic JSON fallback and real-time subscription channels.",
    outputs: ["Persisted CRM Records", "Catalog Inventories", "Analytics Aggregations"],
    samplePayload: `{
  "table": "orders",
  "action": "INSERT",
  "record": {
    "id": "ord_89123",
    "lead_id": "lead_9012",
    "product_id": "prod_jasmine_102",
    "amount": 120.0,
    "status": "paid"
  }
}`
  },
  {
    id: "rag-engine",
    name: "ChromaDB Vector Retrieval Engine",
    category: "sales",
    desc: "Retrieves contextual plant care knowledge, watering schedules, sunlight needs, and nursery policies for customer queries.",
    type: "Vector Database RAG",
    status: "Index Loaded",
    latency: "45ms lookup",
    icon: Zap,
    gradient: "from-purple-500 to-indigo-600",
    badgeBg: "bg-purple-500/10 border-purple-500/30 text-purple-400",
    inputs: ["Customer Care Query", "Embedding Model", "Nursery FAQ Documents"],
    transformation: "Generates 384-dim text embeddings and queries ChromaDB vector index via cosine similarity retrieval.",
    outputs: ["Relevant Knowledge Snippets", "Horticultural Care Guidelines"],
    samplePayload: `{
  "query": "Is Jasmine toxic to cats and dogs?",
  "top_document": "Jasminum officinale is non-toxic to pets according to ASPCA guidelines.",
  "similarity_score": 0.94
}`
  },
  {
    id: "crew-orchestrator",
    name: "CrewAI Multi-Agent Task Orchestrator",
    category: "infra",
    desc: "Coordinates multi-agent task distribution, managing parallel keyword extraction, script writing, thumbnail prompting, and quality checks.",
    type: "Multi-Agent Framework",
    status: "Crew Operational",
    latency: "Stage-gated execution",
    icon: Workflow,
    gradient: "from-blue-500 to-cyan-600",
    badgeBg: "bg-blue-500/10 border-blue-500/30 text-blue-400",
    inputs: ["User Product Request", "Target Language", "Brand Tone Rules"],
    transformation: "Executes structured Agent task handoffs: TrendAgent -> ScriptAgent -> QualityAgent -> VideoAgent.",
    outputs: ["Complete Campaign Asset Package", "Audit Scorecards"],
    samplePayload: `{
  "crew_run_id": "crew_78291",
  "status": "SUCCESS",
  "agents_executed": ["TrendAgent", "ScriptAgent", "QualityAgent", "VideoAgent"],
  "quality_score": 9.4
}`
  },
  {
    id: "tunnel-monitor",
    name: "Reverse Tunnel & Diagnostics Manager",
    category: "infra",
    desc: "Monitors process health, detects network drops, inspects worker tasks, and executes self-healing tunnel & service restarts.",
    type: "Supervisor & Diagnostics",
    status: "Self-Healing Guard Active",
    latency: "10s check interval",
    icon: Activity,
    gradient: "from-rose-500 to-red-600",
    badgeBg: "bg-rose-500/10 border-rose-500/30 text-rose-400",
    inputs: ["Local Port 8000 Listener", "Public Webhook URL Ping"],
    transformation: "Polls endpoint health. If tunnel fails or port drops, automatically restarts cloudflare/localtunnel processes.",
    outputs: ["Diagnostic Logs", "Updated Public Webhook Endpoints"],
    samplePayload: `{
  "healthcheck": "PASS",
  "port_8000": "UP",
  "tunnel_url": "http://localhost:8000",
  "memory_used_mb": 142.5,
  "auto_restart_count": 0
}`
  }
];

export default function ModuleDetailsPage() {
  const [activeId, setActiveId] = useState<string>("yt-ingester");
  const [activeCategory, setActiveCategory] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [simMessage, setSimMessage] = useState<string | null>(null);

  const filteredModules = MODULES.filter(mod => {
    const matchesCategory = activeCategory === "all" || mod.category === activeCategory;
    const matchesSearch = mod.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          mod.desc.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          mod.type.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const activeModule = MODULES.find(m => m.id === activeId) || filteredModules[0] || MODULES[0];
  const ModuleIcon = activeModule.icon;

  const testModuleGateway = () => {
    setIsSimulating(true);
    setSimMessage(null);
    
    setTimeout(() => {
      setSimMessage(`[GATEWAY TEST] Successfully pinged module endpoint: ${activeModule.name}. Status: 200 OK (${activeModule.latency})`);
      setIsSimulating(false);
    }, 1000);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-16">
      {/* Header Banner */}
      <div className="relative overflow-hidden p-8 rounded-3xl bg-slate-900/80 border border-slate-800/80 shadow-2xl backdrop-blur-xl">
        <div className="absolute -right-12 -top-12 w-72 h-72 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -left-12 -bottom-12 w-72 h-72 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 text-cyan-400 text-xs font-extrabold uppercase tracking-widest px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20">
              <Layers className="w-3.5 h-3.5" />
              Infrastructure &amp; Service Architecture Reference
            </div>
            <h1 className="text-3xl md:text-4xl font-black tracking-tight text-white">
              System Modules <span className="bg-gradient-to-r from-cyan-400 via-teal-400 to-indigo-400 bg-clip-text text-transparent">&amp; Data Flow Control</span>
            </h1>
            <p className="text-slate-300 text-sm max-w-2xl leading-relaxed font-medium">
              Technical specifications, input/output data mappings, payload schemas, and data pipelines powering VyaparAI.
            </p>
          </div>

          <div className="flex items-center gap-3 self-start md:self-auto">
            <div className="px-4 py-2.5 rounded-2xl bg-slate-950/80 border border-slate-800 flex items-center gap-2.5 text-xs font-bold text-slate-200">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
              <span className="text-emerald-400">8 Modules Operational</span>
            </div>
          </div>
        </div>
      </div>

      {/* Category Filter & Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-md">
        {/* Category Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-2 sm:pb-0">
          {[
            { id: "all", label: "All 8 Modules" },
            { id: "integration", label: "Integrations & APIs" },
            { id: "rendering", label: "Rendering Engine" },
            { id: "sales", label: "Sales & RAG" },
            { id: "infra", label: "Core Infrastructure" }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveCategory(tab.id)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap ${
                activeCategory === tab.id
                  ? "bg-cyan-600 text-white shadow-lg shadow-cyan-500/20"
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
            placeholder="Search modules..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 text-xs rounded-xl bg-slate-950/80 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition"
          />
        </div>
      </div>

      {/* Main Grid: Selector List (Left 5 cols) + Detailed Inspector (Right 7 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left Side: Module Selection List */}
        <div className="lg:col-span-5 space-y-2.5 max-h-[750px] overflow-y-auto pr-1">
          {filteredModules.map((mod) => {
            const isActive = activeId === mod.id;
            const ItemIcon = mod.icon;
            return (
              <button
                key={mod.id}
                onClick={() => {
                  setActiveId(mod.id);
                  setSimMessage(null);
                }}
                className={`w-full p-4 rounded-2xl text-left transition-all relative overflow-hidden group border ${
                  isActive 
                    ? "bg-slate-900 border-cyan-500/60 shadow-xl shadow-cyan-500/10" 
                    : "bg-slate-900/40 border-slate-800/60 hover:bg-slate-900/80 hover:border-slate-700"
                }`}
              >
                {/* Active left bar indicator */}
                {isActive && (
                  <div className={`absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b ${mod.gradient}`} />
                )}

                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className={`p-2.5 rounded-xl ${mod.badgeBg}`}>
                      <ItemIcon className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-xs font-extrabold text-white group-hover:text-cyan-300 transition">
                        {mod.name}
                      </h4>
                      <p className="text-[10px] text-slate-400 font-medium truncate max-w-[180px] mt-0.5">
                        {mod.type}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-extrabold uppercase px-2 py-0.5 rounded-md bg-slate-950 text-slate-400 border border-slate-800">
                      {mod.category}
                    </span>
                    <ChevronRight className={`w-4 h-4 transition-transform ${isActive ? "translate-x-0.5 text-cyan-400" : "text-slate-600"}`} />
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {/* Right Side: Immersive Module Inspector */}
        <div className="lg:col-span-7 p-7 backdrop-blur-xl bg-slate-900/70 border border-slate-800/80 rounded-3xl shadow-2xl space-y-6 relative overflow-hidden">
          {/* Background Ambient Glow */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

          {/* Module Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-800/80">
            <div className="flex items-center gap-4">
              <div className={`p-3.5 rounded-2xl bg-gradient-to-br ${activeModule.gradient} shadow-lg text-white`}>
                <ModuleIcon className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xl font-black text-white">{activeModule.name}</h3>
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    {activeModule.status}
                  </span>
                </div>
                <p className="text-xs text-cyan-400 font-bold uppercase tracking-wider mt-0.5">
                  {activeModule.type}
                </p>
              </div>
            </div>

            <button
              onClick={testModuleGateway}
              disabled={isSimulating}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-500 hover:to-teal-500 transition shadow-lg shadow-cyan-500/25 active:scale-95 disabled:opacity-50 self-start sm:self-auto"
            >
              <Play className={`w-3.5 h-3.5 ${isSimulating ? "animate-spin" : ""}`} />
              {isSimulating ? "Testing..." : "Test Gateway"}
            </button>
          </div>

          {/* Module Summary */}
          <div className="p-5 rounded-2xl bg-slate-950/70 border border-slate-800 space-y-2">
            <div className="flex items-center gap-2 text-[10px] font-extrabold text-cyan-400 uppercase tracking-widest">
              <Server className="w-3.5 h-3.5" />
              Module Functionality &amp; Purpose
            </div>
            <p className="text-xs text-slate-200 leading-relaxed font-medium">
              {activeModule.desc}
            </p>
          </div>

          {/* Process Data Flow Pipeline */}
          <div className="space-y-4 p-5 rounded-2xl bg-slate-950/50 border border-slate-850">
            <div className="flex items-center gap-2 text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">
              <Workflow className="w-3.5 h-3.5 text-indigo-400" />
              Data Pipeline &amp; Transformation Architecture
            </div>

            {/* Inputs */}
            <div>
              <span className="text-[10px] text-slate-500 font-bold uppercase block mb-1.5">
                📥 EXPECTED DATA INPUT STREAMS
              </span>
              <div className="flex flex-wrap gap-2">
                {activeModule.inputs.map((inp, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 px-3 py-1 rounded-xl bg-slate-900 border border-slate-800 text-[11px] text-slate-300 font-semibold font-mono"
                  >
                    <CheckCircle2 className="w-3 h-3 text-cyan-400" />
                    {inp}
                  </span>
                ))}
              </div>
            </div>

            {/* Transformation Logic */}
            <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800/80 space-y-1">
              <span className="text-[10px] text-indigo-400 font-bold uppercase tracking-wider block">
                ⚡ PROCESSING &amp; TRANSFORMATION LOGIC
              </span>
              <p className="text-xs text-slate-300 font-medium leading-relaxed">
                {activeModule.transformation}
              </p>
            </div>

            {/* Outputs */}
            <div>
              <span className="text-[10px] text-slate-500 font-bold uppercase block mb-1.5">
                📤 PRODUCED DATA OUTPUT ARTIFACTS
              </span>
              <div className="flex flex-wrap gap-2">
                {activeModule.outputs.map((out, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 px-3 py-1 rounded-xl bg-slate-900 border border-slate-800 text-[11px] text-emerald-300 font-semibold font-mono"
                  >
                    <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                    {out}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Sample JSON Payload Inspector */}
          <div className="p-4 rounded-2xl bg-slate-950 border border-slate-850 space-y-2.5">
            <div className="flex items-center justify-between text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              <span className="flex items-center gap-1.5 text-cyan-400">
                <Code className="w-3.5 h-3.5" />
                Live Payload &amp; Event Schema Inspector
              </span>
              <span className="text-[9px] text-slate-500 font-mono">JSON / REST Schema</span>
            </div>

            <pre className="font-mono text-[11px] p-3 rounded-xl bg-slate-900/90 text-emerald-300 overflow-x-auto leading-relaxed border border-slate-800 max-h-40">
              {activeModule.samplePayload}
            </pre>
          </div>

          {/* Simulated Test Gateway Output Message */}
          {simMessage && (
            <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              <span>{simMessage}</span>
            </div>
          )}

          {/* Footer Metadata */}
          <div className="pt-4 border-t border-slate-800/60 flex items-center justify-between text-[10px] font-bold text-slate-400">
            <span>Latency: <strong className="text-emerald-400">{activeModule.latency}</strong></span>
            <span>Protocol: <strong className="text-slate-200">{activeModule.type}</strong></span>
          </div>

        </div>

      </div>
    </div>
  );
}
