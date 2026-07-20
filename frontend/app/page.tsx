// frontend/app/page.tsx
"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { 
  Activity, 
  Play, 
  CheckSquare, 
  Youtube, 
  Inbox, 
  MessageSquare, 
  Users, 
  MessageCircle, 
  BarChart3, 
  Sparkles, 
  Cpu, 
  Zap, 
  Compass, 
  MapPin, 
  TrendingUp, 
  Terminal, 
  ArrowUpRight, 
  AlertCircle, 
  X,
  Network,
  LayoutDashboard,
  UploadCloud,
  Settings,
  Sliders,
  Globe,
  Video
} from "lucide-react";

import { SplineScene } from "@/components/ui/splite";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Detailed static mapping for all 11 Agents to show on Command Center clicks
const AGENTS_METADATA: Record<string, {
  name: string;
  role: string;
  goal: string;
  backstory: string;
  promptTechnique: string;
  reasoningMethod: string;
  promptHistory: string[];
  memoryLog: string[];
  recentDecisions: string[];
}> = {
  coordinator: {
    name: "Coordinator Agent",
    role: "System Orchestration Director",
    goal: "Map pipelines, distribute tasks, manage workflow gates, and coordinate state transfers between agents.",
    backstory: "A high-performance pipeline manager designed to route events, manage concurrent background queues, and ensure state synchronization between CrewAI content tasks and LangGraph checkout nodes.",
    promptTechnique: "Planning-Based Prompting & State Guarding",
    reasoningMethod: "Sequential & Parallel Handoff Routing",
    promptHistory: [
      "Analyze pipeline request for product ID: Fig_01. Map translation dependencies, execute TTS synthesis workers, and lock state variables on database success.",
      "Check YouTube monitor polling status. If comments count exceeds 0, launch the Intent Classification agent crew."
    ],
    memoryLog: [
      "Active Session: Productfig_eb27",
      "Completed: [Trend ➔ Script ➔ Translate ➔ Voiceover ➔ Video Render]",
      "Active Node: comment_poll_worker"
    ],
    recentDecisions: [
      "Allocated background video job #Job_7c22 to rendering queue.",
      "Routed WhatsApp inbound thread #Lead_9a12 to LangGraph checkouts state machine."
    ]
  },
  trend: {
    name: "Trend Agent",
    role: "SEO Keyword Trend Analyst",
    goal: "Scrape Google/YouTube search volume trends to extract high-traffic, low-competition keywords.",
    backstory: "An SEO optimization analyst trained on local Indian retail metrics. Specializes in finding regional search trends (like 'organic gardening Malayalam' or 'cardamom price Delhi') to target video tags.",
    promptTechnique: "Zero-Shot regional keyword extraction",
    reasoningMethod: "Keyword Density & Volatility Evaluation",
    promptHistory: [
      "Analyze product name: Virgin Coconut Oil. Extract primary, secondary, and regional Malayalam/Hindi keywords with search volumes above 5000."
    ],
    memoryLog: [
      "Search Key: 'virgin coconut oil Kerala'",
      "Metrics: Volume=12400, Competition=Low",
      "Selected tags: ['CoconutOilKerala', 'OrganicCoconutOil', 'OrganicVyapar']"
    ],
    recentDecisions: [
      "Selected primary tag 'OrganicCoconutOil' for campaign #Script_cc21.",
      "Associated regional Telugu tags with Coconut oil campaigns."
    ]
  },
  script: {
    name: "Script Agent",
    role: "Creative Marketing Copywriter",
    goal: "Generate high-converting, cultural ad scripts with engaging hooks, body text, and platform-specific CTAs.",
    backstory: "A copywriter with years of experience crafting social media scripts for Indian retail markets. Blends local culture with direct sale hooks.",
    promptTechnique: "Role-Prompting & Contextual Prompting",
    reasoningMethod: "Chain-of-Thought (CoT) copywriting",
    promptHistory: [
      "Write a 15-second YouTube Short script for Fiddle Leaf Fig. Hook must target house plant deaths. Tone should be warm and friendly."
    ],
    memoryLog: [
      "Selected Hook: 'Are your house plants constantly dying? 🌿'",
      "Target Price: Rs. 499",
      "CTA: 'Reply on YouTube comments to buy directly!'"
    ],
    recentDecisions: [
      "Appended wa.me link invitation as the primary CTA for high-intent comment replies.",
      "Generated version 2 script for Fiddle Leaf Fig."
    ]
  },
  thumbnail: {
    name: "Thumbnail Agent",
    role: "Visual Layout & Prompter",
    goal: "Generate layout structures and detailed DALL-E/Midjourney prompts for campaign thumbnails.",
    backstory: "A visual media architect. Specializes in designing product layouts with bold text overlays to capture attention on feeds.",
    promptTechnique: "Structured Image Prompts",
    reasoningMethod: "Visual Contrast Analysis",
    promptHistory: [
      "Generate image prompt for Fiddle Leaf Fig thumbnail. Product must be centered in a modern white pot on a sunlit table. Style: minimal, photorealistic."
    ],
    memoryLog: [
      "Prompt: 'Fiddle leaf fig in a modern white ceramic pot, sunlit minimal room, bold text overlay'",
      "Layout: Centered Product, Yellow text border"
    ],
    recentDecisions: [
      "Approved image prompt design for campaign Fig_01.",
      "Passed prompt output to active database script."
    ]
  },
  video: {
    name: "Video Agent",
    role: "Background Video Renderer",
    goal: "Compile product images, audio voiceovers, transitions, and subtitles into MP4 campaign assets.",
    backstory: "A server-side ffmpeg automation worker. Compiles audio-video timelines, matches subtitle coordinates, and manages background threads.",
    promptTechnique: "Dynamic Scripting & Timestamp Mapping",
    reasoningMethod: "Deterministic Timeline Calculations",
    promptHistory: [
      "Command: ffmpeg -i image.png -i audio.mp3 -vf subtitles=captions.srt output.mp4"
    ],
    memoryLog: [
      "Audio duration: 11.59s",
      "Image dimensions: 1080x1920 (Portrait)",
      "Job status: Processing"
    ],
    recentDecisions: [
      "Assigned job #Job_7c22 to active status queue.",
      "Updated video rendering state to Completed."
    ]
  },
  comment: {
    name: "Comment Agent",
    role: "YouTube Comment Monitor",
    goal: "Poll comment threads, qualify buyer intent, and post automated deep-link replies.",
    backstory: "A social media monitor that scans comment feeds. Qualified to separate buyer intent from greetings or spam comments.",
    promptTechnique: "Few-Shot Intent Classification",
    reasoningMethod: "Regex Pattern & LLM Hybrid check",
    promptHistory: [
      "Analyze comment text: 'How much is it? Do you deliver to Kochi?' Options: HIGH_INTENT, MEDIUM_INTENT, LOW_INTENT, SPAM. Return one word."
    ],
    memoryLog: [
      "Incoming Comment: 'Is this available in Kerala? Delivery charge?'",
      "Classified: HIGH_INTENT (Confidence: 95%)",
      "Auto-Reply: Sent wa.me link with Ref:YT_cc12"
    ],
    recentDecisions: [
      "Posted deep-link reply to @shyam_kumar on video PuCb1JHpBkM.",
      "Queued low-confidence comment from @user_92 for manual review."
    ]
  },
  lead: {
    name: "Lead Agent",
    role: "CRM Lead Ingester",
    goal: "Ingest and promote qualified comment authors to Postgres lead records.",
    backstory: "The database synchronization worker. Integrates social interactions with database CRM tables.",
    promptTechnique: "Structured DB Schema Inserts",
    reasoningMethod: "Entity Extraction Mapping",
    promptHistory: [
      "Ingest qualified customer details: Username: shyam_kumar, Language: Malayalam, CommentID: comment_uuid. Write to leads."
    ],
    memoryLog: [
      "Lead: @shyam_kumar",
      "Language: Malayalam",
      "Initial Status: New"
    ],
    recentDecisions: [
      "Inserted lead profile into CRM tables.",
      "Linked conversation record with default store client settings."
    ]
  },
  whatsapp: {
    name: "WhatsApp Agent",
    role: "Conversational Checkout Assistant",
    goal: "Guide customers through welcome dialogs, answer FAQs using RAG, collect addresses, and send UPI links.",
    backstory: "A stateful sales assistant built on LangGraph. Ensures clear transaction checkouts and answers policy FAQs.",
    promptTechnique: "Contextual RAG & Self-Correction Prompting",
    reasoningMethod: "State-Machine Directed Conversational Checkout",
    promptHistory: [
      "You are a sales assistant. Answer: 'Do you deliver to Bangalore?' using context: 'We ship across India. Free delivery on orders over Rs. 399.'"
    ],
    memoryLog: [
      "State: QA_LOOP ➔ ADDRESS_COLLECTION",
      "Address captured: Kochi, Kerala, 682011",
      "Order created: Order_uuid"
    ],
    recentDecisions: [
      "Validated shipping address pincode: 682011 (Valid).",
      "Generated UPI payment invoice link for Rs. 499."
    ]
  },
  analytics: {
    name: "Analytics Agent",
    role: "Business Performance Reporter",
    goal: "Compile statistics across campaigns, views, conversion rates, and store revenue.",
    backstory: "A business reporting agent. Aggregates data lines to provide insights on store performance.",
    promptTechnique: "Structured CSV & JSON Aggregations",
    reasoningMethod: "Data Trend Forecasting",
    promptHistory: [
      "Aggregate revenue, lead conversions, and clicks for active campaigns. Write report JSON."
    ],
    memoryLog: [
      "Qualified Leads count: 68",
      "Completed orders: 12",
      "Revenue count: Rs. 5,988.00"
    ],
    recentDecisions: [
      "Updated campaign analytics summaries in database.",
      "Generated monthly sales forecast."
    ]
  },
  monitoring: {
    name: "Monitoring Agent",
    role: "System Diagnostics Inspector",
    goal: "Monitor process health, identify network drops, and run self-healing SSH tunnel restarts.",
    backstory: "A system inspector. Verifies local ports, health routes, tunnel processes, and webhook responses.",
    promptTechnique: "Deterministic Connectivity Validation",
    reasoningMethod: "Step-by-Step Diagnostics Routing",
    promptHistory: [
      "Diagnostics status check: local port 8000, tunnel process, public health URL, webhook route."
    ],
    memoryLog: [
      "Tunnel Uptime: 4500s",
      "Last check status: Healthy",
      "Restart count: 1"
    ],
    recentDecisions: [
      "Triggered tunnel recovery script due to network timeout.",
      "Updated .env variables with new public URL."
    ]
  },
  response: {
    name: "Response Agent",
    role: "Regional Language Copy Editor",
    goal: "Translate and refine final chatbot responses in regional Indian languages.",
    backstory: "A multilingual copy editor. Specializes in translating script copy and chat responses to Hindi, Tamil, Telugu, Malayalam, and English.",
    promptTechnique: "Dynamic Contextual Translations",
    reasoningMethod: "Cross-Lingual Copy Validation",
    promptHistory: [
      "Translate chat reply: 'Your order is confirmed and will be shipped soon.' to Malayalam. Ensure warm, friendly, retail-appropriate tone."
    ],
    memoryLog: [
      "English: Your order is confirmed.",
      "Malayalam: നിങ്ങളുടെ ഓർഡർ സ്ഥിരീകരിച്ചു.",
      "Output verified."
    ],
    recentDecisions: [
      "Approved Malayalam translations for order confirmation messages.",
      "Logged translation outputs to active database translations table."
    ]
  }
};

// Seeding Mock Data for Offline fallbacks
const MOCK_ANALYTICS = {
  campaign_status: "Active",
  products_promoted: 2,
  videos_published: 3,
  total_comments: 12,
  auto_replies_sent: 7,
  pending_replies: 2,
  whatsapp_conversations: 5,
  qualified_leads: 68,
  orders_created: 15,
  payments_completed: 12,
  conversion_rate: 17.65,
  revenue: 5988.00,
  avg_response_time: "4.2 mins",
  top_campaigns: [
    { product_id: "1", product_name: "Fiddle Leaf Fig", videos_published: 1, comments: 8, leads: 5, revenue: 2495.00, views: 1200 },
    { product_id: "2", product_name: "Virgin Coconut Oil", videos_published: 2, comments: 4, leads: 3, revenue: 3493.00, views: 800 }
  ],
  recent_activity: [
    { type: "comment", message: "New comment from @shyam_kumar: 'How much is it? Deliver to Kochi?'", timestamp: new Date(Date.now() - 5 * 60000).toISOString() },
    { type: "lead", message: "Lead qualified: @shyam_kumar", timestamp: new Date(Date.now() - 6 * 60000).toISOString() },
    { type: "order", message: "Order PAID: Rs. 499 (Ref: TXN_8c22)", timestamp: new Date(Date.now() - 15 * 60000).toISOString() },
    { type: "comment", message: "New comment from @amala_v: 'Is this plant organic?'", timestamp: new Date(Date.now() - 45 * 60000).toISOString() }
  ],
  funnel: [
    { step: "Campaign Video Views", count: 2000, pct: 100 },
    { step: "Audience Comments", count: 12, pct: 0.6 },
    { step: "Qualified Leads", count: 68, pct: 566.7 },
    { step: "UPI Payments Paid", count: 12, pct: 17.6 }
  ]
};

const FICTIONAL_COMPANIES = [
  {
    name: "GreenLeaf Nursery",
    logo: (
      <svg className="w-5 h-5 text-emerald-400" viewBox="0 0 24 24" fill="currentColor">
        <path d="M17 8C8 10 7 21 7 21S17 19 17 8z" />
      </svg>
    )
  },
  {
    name: "BloomCraft Gardens",
    logo: (
      <svg className="w-5 h-5 text-teal-400" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2a4 4 0 00-4 4 4 4 0 004 4 4 4 0 004-4 4 4 0 00-4-4zm-6 8a4 4 0 00-4 4 4 4 0 004 4 4 4 0 004-4 4 4 0 00-4-4zm12 0a4 4 0 00-4 4 4 4 0 004 4 4 4 0 004-4 4 4 0 00-4-4zm-6 6a4 4 0 00-4 4 4 4 0 004 4 4 4 0 004-4 4 4 0 00-4-4z" />
      </svg>
    )
  },
  {
    name: "FreshMart Grocers",
    logo: (
      <svg className="w-5 h-5 text-orange-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" />
        <line x1="3" y1="6" x2="21" y2="6" />
        <path d="M16 10a4 4 0 01-8 0" />
      </svg>
    )
  },
  {
    name: "Urban Flora",
    logo: (
      <svg className="w-5 h-5 text-pink-400" viewBox="0 0 24 24" fill="currentColor">
        <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V9H6v10zm6-8a3 3 0 013 3H9a3 3 0 013-3zm1-7.5h-2v3.8h2V3.5z" />
      </svg>
    )
  },
  {
    name: "Kerala Organics",
    logo: (
      <svg className="w-5 h-5 text-lime-400" viewBox="0 0 24 24" fill="currentColor">
        <path d="M2 21a2 2 0 002 2h16a2 2 0 002-2v-4H2v4zm10-18C8.5 3 6 5.5 6 9c0 4 6 10 6 10s6-6 6-10c0-3.5-2.5-6-6-6z" />
      </svg>
    )
  },
  {
    name: "FarmNest",
    logo: (
      <svg className="w-5 h-5 text-amber-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 12h18M3 12a9 9 0 0118 0M3 12v6a3 3 0 003 3h12a3 3 0 003-3v-6" />
      </svg>
    )
  },
  {
    name: "PetalPoint",
    logo: (
      <svg className="w-5 h-5 text-violet-400" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2C8 6 7 11 7 15s3 7 5 7 5-3 5-7-1-9-5-13zm0 15a2 2 0 110-4 2 2 0 010 4z" />
      </svg>
    )
  },
  {
    name: "EcoHarvest",
    logo: (
      <svg className="w-5 h-5 text-cyan-400" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2v20M2 12h20M12 12l7-7M5 19l7-7" />
      </svg>
    )
  },
  {
    name: "SpiceRoots",
    logo: (
      <svg className="w-5 h-5 text-rose-500" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2C9 5 8 9 8 12s2 8 4 10c2-2 4-7 4-10S15 5 12 2z" />
      </svg>
    )
  },
  {
    name: "CraftHive",
    logo: (
      <svg className="w-5 h-5 text-yellow-500" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2l8.7 5v10L12 22l-8.7-5V7L12 2zm0 3.5L6.5 8.7v6.6l5.5 3.2 5.5-3.2V8.7L12 5.5z" />
      </svg>
    )
  },
  {
    name: "AquaBloom",
    logo: (
      <svg className="w-5 h-5 text-sky-400" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2.7c-.2 0-.4.1-.5.3C9.7 5.6 5.5 11 5.5 14c0 3.6 2.9 6.5 6.5 6.5s6.5-2.9 6.5-6.5c0-3-4.2-8.4-6-11-.1-.2-.3-.3-.5-.3z" />
      </svg>
    )
  },
  {
    name: "SmartAgri",
    logo: (
      <svg className="w-5 h-5 text-indigo-400" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2c0 2 1 4 3 5-2 1-3 3-3 5 0-2-1-4-3-5 2-1 3-3 3-5zm0 10v10" />
      </svg>
    )
  },
  {
    name: "Nature Basket",
    logo: (
      <svg className="w-5 h-5 text-green-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="11" width="18" height="10" rx="2" />
        <path d="M12 2v9M8 5a4 4 0 018 0" />
      </svg>
    )
  },
  {
    name: "HomeGarden Pro",
    logo: (
      <svg className="w-5 h-5 text-slate-400" viewBox="0 0 24 24" fill="currentColor">
        <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8h5z" />
      </svg>
    )
  },
  {
    name: "PlantVerse",
    logo: (
      <svg className="w-5 h-5 text-emerald-300" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2a10 10 0 100 20 10 10 0 000-20zm0 18c-4.4 0-8-3.6-8-8s3.6-8 8-8 8 3.6 8 8-3.6 8-8 8z" />
      </svg>
    )
  }
];

export default function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(MOCK_ANALYTICS);
  
  // Active connection states
  const [whatsappStatus, setWhatsappStatus] = useState<string>("disconnected");
  const [youtubeChannel, setYoutubeChannel] = useState<any>(null);
  const [tunnelUrl, setTunnelUrl] = useState<string | null>(null);
  const [tunnelDiagnostics, setTunnelDiagnostics] = useState<any>(null);
  const [activeJobs, setActiveJobs] = useState<any[]>([]);

  // Selected agent for Command Center Detail modal
  const [selectedAgentKey, setSelectedAgentKey] = useState<string | null>(null);

  // Network graph states to animate lines
  const [activeFlowLine, setActiveFlowLine] = useState<string | null>(null);

  async function fetchDashboardData() {
    try {
      // 1. Fetch live metrics
      const res = await fetch(`${API_BASE}/analytics/campaigns`);
      if (res.ok) {
        const json = await res.json();
        if (json && json.status === "success") {
          setData(json);
        }
      }

      // 2. Fetch WhatsApp instances
      const waRes = await fetch(`${API_BASE}/whatsapp/instances?tenant_id=00000000-0000-0000-0000-000000000000`);
      if (waRes.ok) {
        const waData = await waRes.json();
        if (waData.status === "success" && waData.data && waData.data.length > 0) {
          setWhatsappStatus(waData.data[0].status || "disconnected");
        } else {
          setWhatsappStatus("disconnected");
        }
      }

      // 3. Fetch YouTube status details
      const ytRes = await fetch(`${API_BASE}/auth/youtube/status`);
      if (ytRes.ok) {
        const ytData = await ytRes.json();
        if (ytData.connected && ytData.channel) {
          setYoutubeChannel(ytData.channel);
        } else {
          setYoutubeChannel(null);
        }
      }

      // 4. Fetch active tunnels URL and diagnostics
      const tunnelRes = await fetch(`${API_BASE}/whatsapp/test-public-tunnel`, {
        method: "POST"
      });
      if (tunnelRes.ok) {
        const tunnelData = await tunnelRes.json();
        if (tunnelData.diagnostics) {
          setTunnelUrl(tunnelData.diagnostics.current_public_url);
          setTunnelDiagnostics(tunnelData.diagnostics);
        }
      }

      // 5. Fetch active video jobs
      const jobsRes = await fetch(`${API_BASE}/video-jobs/active`);
      if (jobsRes.ok) {
        const jobsData = await jobsRes.json();
        if (jobsData.status === "success") {
          setActiveJobs(jobsData.jobs || []);
        }
      }
    } catch (err) {
      console.warn("Failed to fetch dashboard live metrics, using high-fidelity mock fallbacks.", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 10000);

    // Periodically change active network flow animations
    const flowKeys = ["coor-trend", "trend-script", "script-thumb", "thumb-vid", "coor-comm", "comm-lead", "lead-wa", "wa-ana", "coor-mon"];
    const flowInterval = setInterval(() => {
      const randomKey = flowKeys[Math.floor(Math.random() * flowKeys.length)];
      setActiveFlowLine(randomKey);
    }, 3000);

    return () => {
      clearInterval(interval);
      clearInterval(flowInterval);
    };
  }, []);

  // Format date helper
  const timeAgo = (dateStr: string) => {
    try {
      const diff = Date.now() - new Date(dateStr).getTime();
      const mins = Math.floor(diff / 60000);
      if (mins < 1) return "Just now";
      if (mins < 60) return `${mins}m ago`;
      const hrs = Math.floor(mins / 60);
      if (hrs < 24) return `${hrs}h ago`;
      return new Date(dateStr).toLocaleDateString();
    } catch (e) {
      return dateStr;
    }
  };

  const selectedAgent = selectedAgentKey ? AGENTS_METADATA[selectedAgentKey] : null;

  return (
    <div className="space-y-8 pb-16 relative overflow-hidden">
      {/* Ambient glowing background blobs */}
      <div className="absolute top-[10%] left-[5%] w-[450px] h-[450px] rounded-full bg-indigo-500/[0.02] blur-[120px] pointer-events-none -z-10" />
      <div className="absolute top-[40%] right-[5%] w-[400px] h-[400px] rounded-full bg-purple-500/[0.02] blur-[110px] pointer-events-none -z-10" />
      <div className="absolute bottom-[20%] left-[20%] w-[550px] h-[550px] rounded-full bg-emerald-500/[0.02] blur-[140px] pointer-events-none -z-10" />
      
      {/* 1. Sleek SaaS Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between pb-6 border-b border-white/[0.04] gap-6 relative z-10">
        <div className="flex flex-col md:flex-row items-start md:items-center gap-6 flex-1">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-extrabold bg-indigo-500/10 border border-indigo-500/25 text-indigo-400 uppercase tracking-widest">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-ping" />
                VyaparAI Sales OS
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-black tracking-tight leading-tight max-w-2xl font-heading">
              <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent mr-2">
                Autonomous
              </span>
              <span className="text-slate-200 font-bold">
                Multi-Agent Sales Funnel & Pipeline
              </span>
            </h1>
            <p className="text-sm text-slate-400 max-w-xl font-medium leading-relaxed">
              Empowering plant nurseries & micro-retailers by automating the entire sales funnel from social video discovery to stateful WhatsApp checkouts.
            </p>
            
            {/* Integrated Clean Server Status Badges */}
            <div className="flex flex-wrap items-center gap-2 pt-2">
              {/* Ollama Status */}
              <div className="px-3.5 py-2 bg-white/[0.02] border border-white/[0.04] rounded-xl flex items-center gap-2 hover:bg-white/[0.04] transition duration-300">
                <Cpu className="w-4 h-4 text-indigo-400" />
                <span className="text-xs font-bold text-slate-300">LLM Server: Ollama</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              </div>

              {/* YouTube Status */}
              <Link href="/youtube-connect" className="px-3.5 py-2 bg-white/[0.02] border border-white/[0.04] rounded-xl flex items-center gap-2 hover:bg-white/[0.06] hover:border-white/[0.1] hover:text-rose-400 transition duration-300 cursor-pointer">
                <Youtube className="w-4 h-4 text-rose-400" />
                <span className="text-xs font-bold text-slate-300">
                  {youtubeChannel ? `@${youtubeChannel.channel_name}` : "YouTube Offline"}
                </span>
                <span className={`w-1.5 h-1.5 rounded-full ${youtubeChannel ? "bg-emerald-500 animate-pulse" : "bg-rose-500"}`} />
              </Link>

              {/* WhatsApp Status */}
              <Link href="/whatsapp-settings" className="px-3.5 py-2 bg-white/[0.02] border border-white/[0.04] rounded-xl flex items-center gap-2 hover:bg-white/[0.06] hover:border-white/[0.1] hover:text-emerald-400 transition duration-300 cursor-pointer">
                <MessageCircle className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-bold text-slate-300">WhatsApp Link</span>
                <span className={`w-1.5 h-1.5 rounded-full ${whatsappStatus === "connected" ? "bg-emerald-500 animate-pulse" : "bg-rose-500"}`} />
              </Link>

              {/* Public Tunnel Status */}
              <Link href="/whatsapp-settings" className="px-3.5 py-2 bg-white/[0.02] border border-white/[0.04] rounded-xl flex items-center gap-2 hover:bg-white/[0.06] hover:border-white/[0.1] hover:text-amber-400 transition duration-300 cursor-pointer">
                <Globe className="w-4 h-4 text-amber-400" />
                <span className="text-xs font-bold text-slate-300 truncate max-w-[110px]">
                  {tunnelUrl ? "Tunnel Active" : "Tunnel Offline"}
                </span>
                <span className={`w-1.5 h-1.5 rounded-full ${tunnelUrl ? "bg-emerald-500 animate-pulse" : "bg-amber-500"}`} />
              </Link>
            </div>
          </div>
        </div>

        {/* Interactive 3D Robot Card on the Top Right */}
        <div className="w-full lg:w-[480px] h-48 relative overflow-hidden rounded-2xl border border-white/[0.04] bg-white/[0.01] backdrop-blur-md flex items-center justify-between group hover:border-white/[0.08] transition duration-300 shadow-lg shadow-black/10">
          <div className="p-6 z-10 flex flex-col justify-between h-full pointer-events-none">
            <div>
              <span className="text-slate-500 text-xs uppercase font-extrabold tracking-widest block mb-1">AI Operations</span>
              <span className="text-base font-bold text-slate-200">VyaparAI Agent OS</span>
            </div>
          </div>
          
          <div className="absolute right-0 top-0 bottom-0 w-80 h-full">
            <SplineScene 
              scene="https://prod.spline.design/kZDDjO5HuC9GJUM2/scene.splinecode"
              className="w-full h-full"
            />
          </div>
        </div>
      </div>

      {/* 2. Sleek Toolbar Navigation Dock */}
      <div className="relative z-10">
        <div className="bg-white/[0.01] backdrop-blur-md border border-white/[0.04] p-1.5 rounded-2xl flex items-center justify-between gap-1 overflow-x-auto shadow-xl shadow-black/5">
          <div className="flex items-center gap-1 overflow-x-auto w-full scrollbar-none">
            <Link href="/upload" className="px-4 py-2.5 hover:bg-white/[0.03] rounded-xl flex items-center gap-2.5 transition duration-200 group flex-shrink-0">
              <div className="p-1.5 rounded bg-indigo-500/10 text-indigo-400 group-hover:scale-105 transition-transform">
                <UploadCloud className="w-4 h-4" />
              </div>
              <span className="text-xs md:text-sm font-bold text-slate-300">Products</span>
            </Link>
 
            <div className="w-[1px] h-4 bg-white/[0.06] flex-shrink-0" />
 
            <Link href="/preview" className="px-4 py-2.5 hover:bg-white/[0.03] rounded-xl flex items-center gap-2.5 transition duration-200 group flex-shrink-0">
              <div className="p-1.5 rounded bg-indigo-500/10 text-indigo-400 group-hover:scale-105 transition-transform">
                <Play className="w-4 h-4" />
              </div>
              <span className="text-xs md:text-sm font-bold text-slate-300">Campaigns</span>
            </Link>
 
            <div className="w-[1px] h-4 bg-white/[0.06] flex-shrink-0" />
 
            <Link href="/approval" className="px-4 py-2.5 hover:bg-white/[0.03] rounded-xl flex items-center gap-2.5 transition duration-200 group flex-shrink-0">
              <div className="p-1.5 rounded bg-indigo-500/10 text-indigo-400 group-hover:scale-105 transition-transform">
                <CheckSquare className="w-4 h-4" />
              </div>
              <span className="text-xs md:text-sm font-bold text-slate-300">Approvals</span>
            </Link>
 
            <div className="w-[1px] h-4 bg-white/[0.06] flex-shrink-0" />
 
            <Link href="/video-monitoring" className="px-4 py-2.5 hover:bg-white/[0.03] rounded-xl flex items-center gap-2.5 transition duration-200 group flex-shrink-0">
              <div className="p-1.5 rounded bg-indigo-500/10 text-indigo-400 group-hover:scale-105 transition-transform">
                <Video className="w-4 h-4" />
              </div>
              <span className="text-xs md:text-sm font-bold text-slate-300">Monitored Videos</span>
            </Link>
 
            <div className="w-[1px] h-4 bg-white/[0.06] flex-shrink-0" />
 
            <Link href="/comment-inbox" className="px-4 py-2.5 hover:bg-white/[0.03] rounded-xl flex items-center gap-2.5 transition duration-200 group flex-shrink-0">
              <div className="p-1.5 rounded bg-indigo-500/10 text-indigo-400 group-hover:scale-105 transition-transform">
                <Inbox className="w-4 h-4" />
              </div>
              <span className="text-xs md:text-sm font-bold text-slate-300">Inbox</span>
            </Link>
 
            <div className="w-[1px] h-4 bg-white/[0.06] flex-shrink-0" />
 
            <Link href="/live-chat" className="px-4 py-2.5 hover:bg-white/[0.03] rounded-xl flex items-center gap-2.5 transition duration-200 group flex-shrink-0">
              <div className="p-1.5 rounded bg-indigo-500/10 text-indigo-400 group-hover:scale-105 transition-transform">
                <MessageCircle className="w-4 h-4" />
              </div>
              <span className="text-xs md:text-sm font-bold text-slate-300">Live Chat</span>
            </Link>
 
            <div className="w-[1px] h-4 bg-white/[0.06] flex-shrink-0" />
 
            <Link href="/lead-dashboard" className="px-4 py-2.5 hover:bg-white/[0.03] rounded-xl flex items-center gap-2.5 transition duration-200 group flex-shrink-0">
              <div className="p-1.5 rounded bg-indigo-500/10 text-indigo-400 group-hover:scale-105 transition-transform">
                <Users className="w-4 h-4" />
              </div>
              <span className="text-xs md:text-sm font-bold text-slate-300">Leads CRM</span>
            </Link>
 
            <div className="w-[1px] h-4 bg-white/[0.06] flex-shrink-0" />
 
            <Link href="/analytics" className="px-4 py-2.5 hover:bg-white/[0.03] rounded-xl flex items-center gap-2.5 transition duration-200 group flex-shrink-0">
              <div className="p-1.5 rounded bg-indigo-500/10 text-indigo-400 group-hover:scale-105 transition-transform">
                <BarChart3 className="w-4 h-4" />
              </div>
              <span className="text-xs md:text-sm font-bold text-slate-300">Analytics</span>
            </Link>
 
            <div className="w-[1px] h-4 bg-white/[0.06] flex-shrink-0" />
 
            <Link href="/whatsapp-settings" className="px-4 py-2.5 hover:bg-white/[0.03] rounded-xl flex items-center gap-2.5 transition duration-200 group flex-shrink-0">
              <div className="p-1.5 rounded bg-indigo-500/10 text-indigo-400 group-hover:scale-105 transition-transform">
                <Settings className="w-4 h-4" />
              </div>
              <span className="text-xs md:text-sm font-bold text-slate-300">Settings</span>
            </Link>
          </div>
        </div>
      </div>

      {/* 3. Performance Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 relative z-10">
        {/* Active Foliage Mission Card - Computed Dynamically */}
        {(() => {
          const targetGoal = 100;
          const currentAdopted = (data?.payments_completed || 0) + (data?.qualified_leads || 0);
          const missionPct = Math.min(Math.round((currentAdopted / targetGoal) * 100), 100);
          const remaining = Math.max(targetGoal - currentAdopted, 0);

          return (
            <div className="p-5 backdrop-blur-md bg-white/[0.01] border border-white/[0.04] rounded-2xl shadow-lg relative overflow-hidden flex items-center justify-between h-28 group hover:bg-white/[0.02] hover:border-white/[0.08] transition duration-300">
              <div className="flex flex-col justify-between h-full">
                <span className="text-slate-400 text-xs uppercase font-extrabold tracking-widest">Active Mission 🌿</span>
                <div className="flex flex-col">
                  <span className="text-2xl font-bold text-slate-100 leading-tight">{currentAdopted} / {targetGoal} Plants</span>
                  <span className="text-xs text-slate-400 mt-1.5 font-medium">{remaining} plant adoptions remaining</span>
                </div>
              </div>
              {/* Compact SVG Progress Ring */}
              <div className="relative w-16 h-16 flex items-center justify-center flex-shrink-0">
                <svg className="w-full h-full transform -rotate-90">
                  <circle cx="32" cy="32" r="26" stroke="rgba(255, 255, 255, 0.03)" strokeWidth="3.5" fill="transparent" />
                  <circle 
                    cx="32" 
                    cy="32" 
                    r="26" 
                    stroke="url(#indigoGrad)" 
                    strokeWidth="4.5" 
                    fill="transparent" 
                    strokeDasharray="163" 
                    strokeDashoffset={163 - (163 * missionPct) / 100}
                    strokeLinecap="round"
                    className="transition-all duration-1000 ease-out"
                  />
                  <defs>
                    <linearGradient id="indigoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#10b981" />
                      <stop offset="100%" stopColor="#6366f1" />
                    </linearGradient>
                  </defs>
                </svg>
                <span className="absolute text-sm font-black text-slate-100">{missionPct}%</span>
              </div>
            </div>
          );
        })()}

        {/* Nursery Checkout Revenue */}
        <div className="p-5 backdrop-blur-md bg-white/[0.01] border border-white/[0.04] rounded-2xl shadow-lg relative overflow-hidden flex flex-col justify-between h-28 group hover:bg-white/[0.02] hover:border-white/[0.08] transition duration-300">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 text-xs uppercase font-extrabold tracking-widest">Nursery Revenue 💰</span>
            <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
              +{data?.payments_completed || 12} Sales
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-2xl font-black text-slate-50 tracking-tight">
              Rs. {(data?.revenue || 5988).toLocaleString()}
            </span>
            <span className="text-xs text-slate-400 mt-1.5 font-medium">Completed plant checkouts</span>
          </div>
        </div>

        {/* Nursery Adoption Rate */}
        <div className="p-5 backdrop-blur-md bg-white/[0.01] border border-white/[0.04] rounded-2xl shadow-lg relative overflow-hidden flex flex-col justify-between h-28 group hover:bg-white/[0.02] hover:border-white/[0.08] transition duration-300">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 text-xs uppercase font-extrabold tracking-widest">Adoption Rate 📈</span>
            <span className="text-xs font-bold text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded border border-indigo-500/20">
              {data?.conversion_rate || 17.6}%
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-2xl font-black text-slate-50 tracking-tight">
              {data?.conversion_rate || 17.6}%
            </span>
            <span className="text-xs text-slate-400 mt-1.5 font-medium">Comments to checkouts conversion</span>
          </div>
        </div>

        {/* Botanical AI Response Speed */}
        <div className="p-5 backdrop-blur-md bg-white/[0.01] border border-white/[0.04] rounded-2xl shadow-lg relative overflow-hidden flex flex-col justify-between h-28 group hover:bg-white/[0.02] hover:border-white/[0.08] transition duration-300">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 text-xs uppercase font-extrabold tracking-widest">Response Speed ⚡</span>
            <span className="text-xs font-bold text-cyan-400 bg-cyan-500/10 px-1.5 py-0.5 rounded border border-cyan-500/20">
              Active
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-2xl font-black text-slate-50 tracking-tight">
              {data?.avg_response_time || "4.2 mins"}
            </span>
            <span className="text-xs text-slate-400 mt-1.5 font-medium">Comment reply latency speed</span>
          </div>
        </div>
      </div>

      {/* 4. Middle Section: AI Command Center Grid & SVN network visualization */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 relative z-10">
        
        {/* Active AI Agent Grid Control Panel */}
        <div className="lg:col-span-2 p-6 backdrop-blur-md bg-white/[0.01] border border-white/[0.04] rounded-[24px] shadow-lg flex flex-col justify-between hover:border-white/[0.06] transition duration-300">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-indigo-400 mb-6 flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Cpu className="w-4 h-4" />
                Autonomous Agents Panel
              </span>
              <span className="text-xs font-bold text-slate-400 uppercase tracking-widest normal-case">
                Click card for live logs
              </span>
            </h2>
 
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
              {Object.keys(AGENTS_METADATA).map((key) => {
                const meta = AGENTS_METADATA[key];
                return (
                  <button 
                    key={key}
                    onClick={() => setSelectedAgentKey(key)}
                    className="p-3 bg-white/[0.01] border border-white/[0.04] hover:bg-white/[0.02] hover:border-indigo-500/20 rounded-xl text-left transition-all duration-300 relative group flex flex-col justify-between h-24 hover:shadow-[0_0_12px_rgba(99,102,241,0.04)]"
                  >
                    <div className="flex items-start justify-between">
                      <span className="text-xs font-bold uppercase text-indigo-400 font-heading tracking-wide truncate max-w-[80%]">
                        {meta.name.split(" ")[0]}
                      </span>
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse flex-shrink-0" />
                    </div>
                    
                    <div className="text-xs text-slate-350 line-clamp-2 leading-snug">
                      {meta.role}
                    </div>
 
                    <div className="flex items-center justify-between text-[10px] text-slate-400 font-bold uppercase tracking-widest">
                      <span>Status</span>
                      <ArrowUpRight className="w-2.5 h-2.5 text-slate-600 group-hover:text-indigo-400 transition-colors" />
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
 
          <div className="mt-6 pt-4 border-t border-white/[0.04] flex items-center justify-between text-xs text-slate-400">
            <span>Operational Mode: <strong className="text-slate-300 font-bold">Hybrid Autopilot</strong></span>
            <span>Total active threads: <strong className="text-slate-300 font-bold">11 Nodes</strong></span>
          </div>
        </div>
 
        {/* AI Network flow graph visualization panel */}
        <div className="lg:col-span-1 p-6 backdrop-blur-md bg-white/[0.01] border border-white/[0.04] rounded-[24px] shadow-lg flex flex-col justify-between hover:border-white/[0.06] transition duration-300">
          <h2 className="text-sm font-bold uppercase tracking-wider text-indigo-400 mb-4 flex items-center gap-2">
            <Network className="w-4 h-4" />
            AI Network Streams
          </h2>
 
          <div className="flex-1 flex items-center justify-center p-2 relative h-64 bg-white/[0.01] rounded-[20px] border border-white/[0.03]">
            {/* SVG Interactive Node map */}
            <svg viewBox="0 0 300 240" className="w-full h-full">
              
              {/* Animated Connection Paths */}
              {/* Coordinator (150, 40) ➔ Trend (60, 80) */}
              <line x1="150" y1="40" x2="60" y2="80" stroke={activeFlowLine === "coor-trend" ? "#a855f7" : "#1e293b"} strokeWidth={activeFlowLine === "coor-trend" ? "2" : "1"} />
              {activeFlowLine === "coor-trend" && <circle r="3" fill="#a855f7"><animateMotion dur="1s" repeatCount="indefinite" path="M 150 40 L 60 80" /></circle>}
 
              {/* Trend (60, 80) ➔ Script (60, 140) */}
              <line x1="60" y1="80" x2="60" y2="140" stroke={activeFlowLine === "trend-script" ? "#6366f1" : "#1e293b"} strokeWidth={activeFlowLine === "trend-script" ? "2" : "1"} />
              {activeFlowLine === "trend-script" && <circle r="3" fill="#6366f1"><animateMotion dur="1s" repeatCount="indefinite" path="M 60 80 L 60 140" /></circle>}
 
              {/* Script (60, 140) ➔ Thumbnail (100, 190) */}
              <line x1="60" y1="140" x2="100" y2="190" stroke={activeFlowLine === "script-thumb" ? "#6366f1" : "#1e293b"} strokeWidth={activeFlowLine === "script-thumb" ? "2" : "1"} />
              {activeFlowLine === "script-thumb" && <circle r="3" fill="#6366f1"><animateMotion dur="1.2s" repeatCount="indefinite" path="M 60 140 L 100 190" /></circle>}
 
              {/* Thumbnail (100, 190) ➔ Video (150, 210) */}
              <line x1="100" y1="190" x2="150" y2="210" stroke={activeFlowLine === "thumb-vid" ? "#3b82f6" : "#1e293b"} strokeWidth={activeFlowLine === "thumb-vid" ? "2" : "1"} />
              {activeFlowLine === "thumb-vid" && <circle r="3" fill="#3b82f6"><animateMotion dur="1s" repeatCount="indefinite" path="M 100 190 L 150 210" /></circle>}
 
              {/* Coordinator (150, 40) ➔ Comment (240, 80) */}
              <line x1="150" y1="40" x2="240" y2="80" stroke={activeFlowLine === "coor-comm" ? "#a855f7" : "#1e293b"} strokeWidth={activeFlowLine === "coor-comm" ? "2" : "1"} />
              {activeFlowLine === "coor-comm" && <circle r="3" fill="#a855f7"><animateMotion dur="1.1s" repeatCount="indefinite" path="M 150 40 L 240 80" /></circle>}
 
              {/* Comment (240, 80) ➔ Lead (240, 140) */}
              <line x1="240" y1="80" x2="240" y2="140" stroke={activeFlowLine === "comm-lead" ? "#ec4899" : "#1e293b"} strokeWidth={activeFlowLine === "comm-lead" ? "2" : "1"} />
              {activeFlowLine === "comm-lead" && <circle r="3" fill="#ec4899"><animateMotion dur="1s" repeatCount="indefinite" path="M 240 80 L 240 140" /></circle>}
 
              {/* Lead (240, 140) ➔ WhatsApp (200, 190) */}
              <line x1="240" y1="140" x2="200" y2="190" stroke={activeFlowLine === "lead-wa" ? "#10b981" : "#1e293b"} strokeWidth={activeFlowLine === "lead-wa" ? "2" : "1"} />
              {activeFlowLine === "lead-wa" && <circle r="3" fill="#10b981"><animateMotion dur="1.2s" repeatCount="indefinite" path="M 240 140 L 200 190" /></circle>}
 
              {/* WhatsApp (200, 190) ➔ Analytics (150, 210) */}
              <line x1="200" y1="190" x2="150" y2="210" stroke={activeFlowLine === "wa-ana" ? "#10b981" : "#1e293b"} strokeWidth={activeFlowLine === "wa-ana" ? "2" : "1"} />
              {activeFlowLine === "wa-ana" && <circle r="3" fill="#10b981"><animateMotion dur="1s" repeatCount="indefinite" path="M 200 190 L 150 210" /></circle>}
 
              {/* Coordinator (150, 40) ➔ Monitoring (150, 110) */}
              <line x1="150" y1="40" x2="150" y2="110" stroke={activeFlowLine === "coor-mon" ? "#f59e0b" : "#1e293b"} strokeWidth={activeFlowLine === "coor-mon" ? "2" : "1"} />
              {activeFlowLine === "coor-mon" && <circle r="3" fill="#f59e0b"><animateMotion dur="0.8s" repeatCount="indefinite" path="M 150 40 L 150 110" /></circle>}
 
              {/* Node Circles */}
              {/* Coordinator */}
              <circle cx="150" cy="40" r="10" fill="#a855f7" className="animate-pulse" />
              <text x="150" y="24" fill="#a855f7" fontSize="9" textAnchor="middle" fontWeight="bold">Coordinator</text>
 
              {/* Trend */}
              <circle cx="60" cy="80" r="8" fill="#6366f1" />
              <text x="60" y="68" fill="#cbd5e1" fontSize="8" textAnchor="middle">Trend</text>
 
              {/* Script */}
              <circle cx="60" cy="140" r="8" fill="#6366f1" />
              <text x="45" y="143" fill="#cbd5e1" fontSize="8" textAnchor="end">Script</text>
 
              {/* Thumbnail */}
              <circle cx="100" cy="190" r="8" fill="#3b82f6" />
              <text x="100" y="205" fill="#cbd5e1" fontSize="8" textAnchor="middle">Thumb</text>
 
              {/* Comment */}
              <circle cx="240" cy="80" r="8" fill="#ec4899" />
              <text x="240" y="68" fill="#cbd5e1" fontSize="8" textAnchor="middle">Comment</text>
 
              {/* Lead */}
              <circle cx="240" cy="140" r="8" fill="#ec4899" />
              <text x="255" y="143" fill="#cbd5e1" fontSize="8" textAnchor="start">Lead</text>
 
              {/* WhatsApp */}
              <circle cx="200" cy="190" r="8" fill="#10b981" />
              <text x="200" y="205" fill="#cbd5e1" fontSize="8" textAnchor="middle">WhatsApp</text>
 
              {/* Monitor */}
              <circle cx="150" cy="110" r="8" fill="#f59e0b" />
              <text x="164" y="113" fill="#cbd5e1" fontSize="8" textAnchor="start">Monitor</text>
 
              {/* Analytics */}
              <circle cx="150" cy="210" r="10" fill="#14b8a6" />
              <text x="150" y="228" fill="#14b8a6" fontSize="9" textAnchor="middle" fontWeight="bold">Analytics</text>
            </svg>
          </div>
 
          <div className="text-xs text-slate-400 font-bold uppercase tracking-widest text-center mt-3">
            Pulsing rays denote active state sharing
          </div>
        </div>
      </div>

      {/* 5. Bottom Row: Opportunity Radar, Funnel & Live Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 relative z-10">
        
        {/* Opportunity Radar alerts */}
        <div className="p-6 backdrop-blur-md bg-white/[0.01] border border-white/[0.04] rounded-[24px] shadow-lg flex flex-col justify-between hover:border-white/[0.06] transition duration-300">
          <h2 className="text-sm font-bold uppercase tracking-wider text-indigo-400 mb-6 flex items-center gap-2">
            <Compass className="w-4 h-4" />
            Opportunity Radar
          </h2>
 
          <div className="space-y-3.5">
            {/* Lead alerts */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-white/[0.01] border border-white/[0.03] hover:bg-white/[0.02] hover:border-white/[0.05] transition duration-200">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                <div className="flex flex-col">
                  <span className="text-sm font-bold text-slate-200">High-Value Leads Waiting</span>
                  <span className="text-xs text-slate-400">Qualified checkout stages active</span>
                </div>
              </div>
              <Link href="/lead-dashboard" className="p-1 rounded bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 text-sm font-bold px-2.5 py-1 transition">
                View ({data?.qualified_leads || 68})
              </Link>
            </div>
 
            {/* Campaign Approval alert */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-white/[0.01] border border-white/[0.03] hover:bg-white/[0.02] hover:border-white/[0.05] transition duration-200">
              <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full ${data?.pending_replies > 0 ? "bg-amber-500 animate-pulse" : "bg-slate-700"}`} />
                <div className="flex flex-col">
                  <span className="text-sm font-bold text-slate-200">Approvals Required</span>
                  <span className="text-xs text-slate-400">Pending comment replies or drafts</span>
                </div>
              </div>
              <Link href="/approval" className="p-1 rounded bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 text-sm font-bold px-2.5 py-1 transition">
                Manage ({data?.pending_replies || 2})
              </Link>
            </div>
 
            {/* Inbound WhatsApp Chat alert */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-white/[0.01] border border-white/[0.03] hover:bg-white/[0.02] hover:border-white/[0.05] transition duration-200">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-indigo-500" />
                <div className="flex flex-col">
                  <span className="text-sm font-bold text-slate-200">Active Autopilots Chats</span>
                  <span className="text-xs text-slate-400">WhatsApp live conversion logs</span>
                </div>
              </div>
              <Link href="/live-chat" className="p-1 rounded bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 text-sm font-bold px-2.5 py-1 transition">
                Join ({data?.whatsapp_conversations || 5})
              </Link>
            </div>
          </div>
 
          <div className="text-xs text-slate-400 font-bold uppercase tracking-widest text-center mt-6">
            Radar scans active pipeline stages
          </div>
        </div>
 
        {/* Customer Journey Funnel widget */}
        <div className="p-6 backdrop-blur-md bg-white/[0.01] border border-white/[0.04] rounded-[24px] shadow-lg flex flex-col justify-between hover:border-white/[0.06] transition duration-300">
          <h2 className="text-sm font-bold uppercase tracking-wider text-indigo-400 mb-6 flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            Conversion Funnel
          </h2>
 
          <div className="space-y-3.5">
            {data?.funnel?.map((item: any, idx: number) => {
              const widths = ["w-full", "w-[85%]", "w-[65%]", "w-[45%]"];
              const colors = ["from-indigo-500 to-indigo-600", "from-purple-500 to-purple-600", "from-pink-500 to-pink-600", "from-emerald-500 to-emerald-600"];
              return (
                <div key={idx} className="space-y-1.5">
                  <div className="flex justify-between text-xs font-bold text-slate-400 uppercase tracking-wide">
                    <span>{item.step}</span>
                    <span>{item.count.toLocaleString()} ({item.pct}%)</span>
                  </div>
                  <div className="h-1.5 w-full bg-white/[0.03] rounded-full overflow-hidden border-0">
                    <div className={`h-full bg-gradient-to-r ${colors[idx]} rounded-full ${widths[idx]} transition-all duration-1000`} />
                  </div>
                </div>
              );
            })}
          </div>
 
          <div className="text-xs text-slate-400 font-bold uppercase tracking-widest text-center mt-6">
            Tracks user progression from click to checkout
          </div>
        </div>
 
        {/* Live Scrolling Activity Feed widget */}
        <div className="p-6 backdrop-blur-md bg-white/[0.01] border border-white/[0.04] rounded-[24px] shadow-lg flex flex-col justify-between h-[360px] hover:border-white/[0.06] transition duration-300">
          <h2 className="text-sm font-bold uppercase tracking-wider text-indigo-400 mb-4 flex items-center gap-2">
            <Terminal className="w-4 h-4 text-emerald-400" />
            Live OS Activity Feed
          </h2>
 
          <div className="flex-1 bg-black/20 border border-white/[0.03] p-4 rounded-2xl font-mono text-xs text-slate-300 overflow-y-auto space-y-3 custom-scrollbar shadow-inner">
            {data?.recent_activity?.length > 0 ? (
              data.recent_activity.map((act: any, idx: number) => (
                <div key={idx} className="border-b border-white/[0.02] pb-2 flex flex-col gap-1">
                  <div className="flex items-center justify-between text-slate-400 font-bold">
                    <span className="uppercase">{act.type} event</span>
                    <span>{timeAgo(act.timestamp)}</span>
                  </div>
                  <div className="text-indigo-300 leading-snug">
                    {act.message}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-slate-400 text-center py-12">No active logs parsed</div>
            )}
          </div>
 
          <div className="text-xs text-slate-400 font-bold uppercase tracking-widest text-center mt-4">
            Live event logs from backend webhooks
          </div>
        </div>
 
      </div>
 
      {/* 5. AI Recommendations and Insights Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative z-10">
        
        {/* AI Recommendations */}
        <div className="p-6 backdrop-blur-md bg-white/[0.01] border border-white/[0.04] rounded-[24px] shadow-lg relative overflow-hidden group hover:border-white/[0.06] transition duration-300">
          <h2 className="text-sm font-bold uppercase tracking-wider text-indigo-400 mb-6 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-purple-400" />
            System Optimization Guidelines
          </h2>
          <div className="space-y-4">
            <div className="p-4 bg-white/[0.01] border border-white/[0.03] rounded-[20px] hover:border-white/[0.06] transition flex items-start gap-4">
              <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 mt-1 flex-shrink-0">
                <Sparkles className="w-4 h-4" />
              </div>
              <div className="flex flex-col gap-1">
                <h4 className="text-sm font-bold text-slate-200">Scale Regional Campaigns</h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Malayalam and Hindi script scripts have achieved a 23% higher engagement rate on YouTube Shorts. We recommend launching another video for your cardamom or plant inventory.
                </p>
              </div>
            </div>
 
            <div className="p-4 bg-white/[0.01] border border-white/[0.03] rounded-[20px] hover:border-white/[0.06] transition flex items-start gap-4">
              <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 mt-1 flex-shrink-0">
                <AlertCircle className="w-4 h-4" />
              </div>
              <div className="flex flex-col gap-1">
                <h4 className="text-sm font-bold text-slate-200">Address Collection Objections</h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  2 leads abandoned checkouts when asked for pincodes. Review your return or shipping policy FAQs stored in ChromaDB to ensure shipping information is clear.
                </p>
              </div>
            </div>
          </div>
        </div>
 
        {/* AI Insights & Metrics distribution mock map */}
        <div className="p-6 backdrop-blur-md bg-white/[0.01] border border-white/[0.04] rounded-[24px] shadow-lg relative overflow-hidden group hover:border-white/[0.06] transition duration-300">
          <h2 className="text-sm font-bold uppercase tracking-wider text-indigo-400 mb-6 flex items-center gap-2">
            <MapPin className="w-4 h-4 text-cyan-400" />
            Regional Leads Distribution
          </h2>
          
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm font-bold text-slate-300 mb-1.5">
                <span>Kerala (Kochi, Kottayam, Trivandrum)</span>
                <span>45% of total leads</span>
              </div>
              <div className="h-1.5 w-full bg-white/[0.03] rounded-full overflow-hidden border-0">
                <div className="h-full bg-indigo-500 rounded-full w-[45%]" />
              </div>
            </div>
 
            <div>
              <div className="flex justify-between text-sm font-bold text-slate-300 mb-1.5">
                <span>Tamil Nadu (Chennai, Madurai, Coimbatore)</span>
                <span>28% of total leads</span>
              </div>
              <div className="h-1.5 w-full bg-white/[0.03] rounded-full overflow-hidden border-0">
                <div className="h-full bg-purple-500 rounded-full w-[28%]" />
              </div>
            </div>
 
            <div>
              <div className="flex justify-between text-sm font-bold text-slate-300 mb-1.5">
                <span>Karnataka (Bangalore, Mysore)</span>
                <span>17% of total leads</span>
              </div>
              <div className="h-1.5 w-full bg-white/[0.03] rounded-full overflow-hidden border-0">
                <div className="h-full bg-pink-500 rounded-full w-[17%]" />
              </div>
            </div>
 
            <div>
              <div className="flex justify-between text-sm font-bold text-slate-300 mb-1.5">
                <span>Other Regions (Delhi, Mumbai, Pune)</span>
                <span>10% of total leads</span>
              </div>
              <div className="h-1.5 w-full bg-white/[0.03] rounded-full overflow-hidden border-0">
                <div className="h-full bg-cyan-500 rounded-full w-[10%]" />
              </div>
            </div>
          </div>
        </div>
      </div>
 
      {/* 6. Credibility Section: Businesses Growing with VyaparAI */}
      <div className="space-y-6 pt-6 border-t border-slate-900/60 max-w-6xl mx-auto">
        <div className="text-center space-y-1">
          <div className="text-xs font-bold text-indigo-400 uppercase tracking-widest">Growth & Adoption</div>
          <h2 className="text-xl font-extrabold text-slate-200 font-heading">Businesses Growing with VyaparAI</h2>
          <p className="text-xs text-slate-500 max-w-md mx-auto leading-normal">
            VyaparAI powers localized conversational sales, catalogs, and marketing automations for independent brands. (Demonstration Sandbox Data)
          </p>
        </div>
 
        <div className="relative w-full overflow-hidden py-4 bg-slate-950/20 backdrop-blur-sm border border-slate-900/60 rounded-2xl mask-fade">
          <style>{`
            .mask-fade {
              mask-image: linear-gradient(to right, transparent, black 15%, black 85%, transparent);
              -webkit-mask-image: linear-gradient(to right, transparent, black 15%, black 85%, transparent);
            }
            @keyframes scroll {
              0% { transform: translateX(0); }
              100% { transform: translateX(-50%); }
            }
            .animate-scroll {
              display: flex;
              width: max-content;
              animation: scroll 32s linear infinite;
            }
            .animate-scroll:hover {
              animation-play-state: paused;
            }
            @media (prefers-reduced-motion: reduce) {
              .animate-scroll {
                animation: none;
                overflow-x: auto;
                width: auto;
              }
            }
          `}</style>
          
          <div className="animate-scroll gap-6 px-4">
            {/* Double list for smooth seamless looping */}
            {[...FICTIONAL_COMPANIES, ...FICTIONAL_COMPANIES].map((company, index) => (
              <div 
                key={index}
                className="flex items-center gap-3 bg-slate-900/40 border border-slate-850 px-4 py-3 rounded-xl hover:scale-105 hover:bg-slate-900/80 transition duration-300 select-none flex-shrink-0 cursor-default"
              >
                {company.logo}
                <span className="text-sm font-bold text-slate-300 font-sans tracking-wide">
                  {company.name}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
 
      {/* 7. Overlay Modal: Detailed Agent System logs and prompts */}
      {selectedAgent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-6 relative overflow-hidden my-8">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-purple-500/0 pointer-events-none" />
            
            {/* Header */}
            <div className="flex items-start justify-between border-b border-slate-800 pb-4 mb-5">
              <div>
                <h3 className="text-xl font-black text-slate-100">{selectedAgent.name}</h3>
                <p className="text-sm text-indigo-400 font-bold uppercase tracking-wider mt-1">{selectedAgent.role}</p>
              </div>
              <button 
                onClick={() => setSelectedAgentKey(null)}
                className="p-1 rounded-lg bg-slate-950/60 border border-slate-850 hover:border-slate-700 text-slate-400 hover:text-slate-100 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
 
            {/* Content Body */}
            <div className="space-y-5 text-sm leading-relaxed max-h-[60vh] overflow-y-auto pr-2 custom-scrollbar">
              
              {/* Goal & Backstory */}
              <div className="space-y-2">
                <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest">Role Description & Backstory</h4>
                <div className="p-3.5 bg-slate-950/60 border border-slate-850 rounded-xl space-y-2">
                  <div>
                    <span className="text-xs text-slate-500 font-bold uppercase block mb-0.5">AGENT GOAL</span>
                    <p className="text-slate-200 text-sm font-medium">{selectedAgent.goal}</p>
                  </div>
                  <div className="pt-2 border-t border-slate-900/60">
                    <span className="text-xs text-slate-500 font-bold uppercase block mb-0.5">AGENT BACKSTORY</span>
                    <p className="text-slate-400 text-xs leading-relaxed">{selectedAgent.backstory}</p>
                  </div>
                </div>
              </div>
 
              {/* Prompt Strategies */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3.5 bg-slate-950/60 border border-slate-850 rounded-xl">
                  <span className="text-xs text-indigo-400 font-bold uppercase block mb-1">Prompting Technique</span>
                  <span className="text-sm font-bold text-slate-200">{selectedAgent.promptTechnique}</span>
                </div>
                <div className="p-3.5 bg-slate-950/60 border border-slate-850 rounded-xl">
                  <span className="text-xs text-purple-400 font-bold uppercase block mb-1">Reasoning Method</span>
                  <span className="text-sm font-bold text-slate-200">{selectedAgent.reasoningMethod}</span>
                </div>
              </div>
 
              {/* Prompt History templates */}
              <div>
                <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-2">Prompt Templates History</h4>
                <div className="space-y-2">
                  {selectedAgent.promptHistory.map((h, i) => (
                    <div key={i} className="p-3 bg-slate-950/80 border border-slate-900 rounded-xl font-mono text-xs text-indigo-300 leading-normal">
                      {h}
                    </div>
                  ))}
                </div>
              </div>
 
              {/* Memory Logs */}
              <div>
                <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-2">Short-Term Memory Registry</h4>
                <div className="p-3 bg-slate-950/80 border border-slate-900 rounded-xl font-mono text-xs text-emerald-400 space-y-1">
                  {selectedAgent.memoryLog.map((m, i) => (
                    <div key={i}>➔ {m}</div>
                  ))}
                </div>
              </div>
 
              {/* Decisions */}
              <div>
                <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-2">Recent Execution Decisions</h4>
                <ul className="space-y-1.5 list-disc pl-4 text-sm text-slate-300">
                  {selectedAgent.recentDecisions.map((d, i) => (
                    <li key={i}>{d}</li>
                  ))}
                </ul>
              </div>
 
            </div>
 
            {/* Footer */}
            <div className="mt-6 pt-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-500 font-bold uppercase tracking-widest">
              <span>Node status: <strong className="text-emerald-500">HEALTHY</strong></span>
              <span>Total calls: 247</span>
            </div>
          </div>
        </div>
      )}
 
    </div>
  );
}
