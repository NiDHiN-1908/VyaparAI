// frontend/app/preview/page.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Eye,
  Sparkles,
  Share2,
  Languages,
  Film,
  MessageSquare,
  Copy,
  Check,
  Tag,
  Image as ImageIcon,
  AlertTriangle
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export default function PreviewPage() {
  const [selectedLang, setSelectedLang] = useState("English");
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [version, setVersion] = useState(1);
  const [loading, setLoading] = useState(true);
  const [productId, setProductId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const [jobMessage, setJobMessage] = useState<string>("");
  const [jobProgressStep, setJobProgressStep] = useState<number>(0);

  // Real-time agent status states
  const [agents, setAgents] = useState<Record<string, string>>({
    KeywordAgent: "Queued",
    ScreenplayAgent: "Queued",
    ThumbnailAgent: "Queued",
    TranslationAgent: "Queued",
    ImagePromptAgent: "Queued",
    VoiceoverAgent: "Queued"
  });
  const [progressPercent, setProgressPercent] = useState(10);
  const [estimatedTime, setEstimatedTime] = useState(45);
  const [agentDurations, setAgentDurations] = useState<Record<string, number>>({});
  const [elapsedTime, setElapsedTime] = useState<number>(0);
  const [currentAgent, setCurrentAgent] = useState<string | null>(null);
  const [pollTrigger, setPollTrigger] = useState(0);

  // Video player self-healing states
  const [videoError, setVideoError] = useState<string | null>(null);
  const [repairing, setRepairing] = useState(false);
  const [repairMessage, setRepairMessage] = useState("");

  const handleRetryAgent = async (agentName: string) => {
    if (!productId) return;
    try {
      setAgents(prev => ({ ...prev, [agentName]: "Running" }));
      const res = await fetch(`${API_BASE}/generate-content/retry-agent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId, agent_name: agentName })
      });
      if (res.ok) {
        setPollTrigger(prev => prev + 1);
      }
    } catch (err) {
      console.error("Failed to retry agent:", err);
    }
  };

  const handleRepairVideo = async (videoId: string) => {
    if (!videoId) return;
    setRepairing(true);
    setVideoError(null);
    setRepairMessage("Validating & rebuilding video frames on the server...");

    try {
      const res = await fetch(`${API_BASE}/video/repair`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_id: videoId })
      });

      if (!res.ok) {
        throw new Error("Server failed to repair the video file.");
      }

      const repairData = await res.json();
      if (repairData?.video_url && selectedLang) {
        setCampaignData((prev: any) => ({
          ...prev,
          videos: {
            ...prev?.videos,
            [selectedLang]: {
              ...prev?.videos?.[selectedLang],
              video_url: repairData.video_url
            }
          }
        }));
      }

      setRepairMessage("Video repaired successfully! Reloading...");
      setTimeout(() => {
        setRepairing(false);
        setVersion(prev => prev + 1);
        const temp = selectedLang;
        setSelectedLang("");
        setTimeout(() => setSelectedLang(temp), 50);
      }, 1000);

    } catch (err: any) {
      console.error(err);
      setVideoError("Auto-repair failed. Please try regenerating the campaign or contact support.");
      setRepairing(false);
    }
  };

  const handleRegenerate = async () => {
    if (!productId) return;
    setLoading(true);
    setJobStatus("running");
    setJobProgressStep(1);
    setProgressPercent(10);
    try {
      const res = await fetch(`${API_BASE}/generate-content`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: productId })
      });
      if (res.ok) {
        setPollTrigger(prev => prev + 1);
      }
    } catch (e) {
      console.error("Regeneration failed:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let pollInterval: NodeJS.Timeout;
    let socket: WebSocket | null = null;
    let wsReconnectTimeout: NodeJS.Timeout;

    const connectWS = (pId: string) => {
      const ws_protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const ws_host = API_BASE.replace("http://", "").replace("https://", "");
      const DEFAULT_TENANT = "00000000-0000-0000-0000-000000000000";

      try {
        socket = new WebSocket(`${ws_protocol}//${ws_host}/ws?tenant_id=${DEFAULT_TENANT}`);
        
        socket.onmessage = async (event) => {
          try {
            const payload = JSON.parse(event.data);
            if (payload.event === "job.progress" && payload.data) {
              const updatedJob = payload.data;
              if (updatedJob.product_id === pId || updatedJob.job_id === pId) {
                setJobStatus(updatedJob.current_status.toLowerCase());
                setJobMessage(updatedJob.current_stage ? `${updatedJob.current_stage}: ${updatedJob.current_status} (${updatedJob.percentage_complete}%)` : "");
                
                const step_mapping: Record<string, number> = {
                  "Product Analysis": 1,
                  "Research Enrichment": 2,
                  "SEO Keyword Generation": 3,
                  "Script Generation": 4,
                  "Thumbnail Creation": 5,
                  "Image Generation": 6,
                  "Voice Generation": 7,
                  "Video Rendering": 8,
                  "Completed": 9
                };
                setJobProgressStep(step_mapping[updatedJob.current_stage] || 0);

                if (updatedJob.agents) {
                  setAgents(updatedJob.agents);
                }
                if (updatedJob.percentage_complete !== undefined) {
                  setProgressPercent(updatedJob.percentage_complete);
                }
                if (updatedJob.estimated_remaining_time !== undefined) {
                  setEstimatedTime(updatedJob.estimated_remaining_time);
                }
                if (updatedJob.agent_durations) {
                  setAgentDurations(updatedJob.agent_durations);
                }
                if (updatedJob.elapsed_time !== undefined) {
                  setElapsedTime(updatedJob.elapsed_time);
                }
                
                let activeAgent = null;
                for (const [name, state] of Object.entries(updatedJob.agents || {})) {
                  if (state === "Running") {
                    activeAgent = name;
                    break;
                  }
                }
                if (activeAgent) {
                  setCurrentAgent(activeAgent);
                }

                // Retrieve updated campaign data inline
                const updateCampRes = await fetch(`${API_BASE}/campaign/${pId}`);
                if (updateCampRes.ok) {
                  const updateData = await updateCampRes.json();
                  setCampaignData(updateData);
                }

                if (updatedJob.current_status === "Completed" || updatedJob.current_status === "Failed") {
                  if (socket) socket.close();
                }
              }
            }
          } catch (err) {
            console.error("WS parse error:", err);
          }
        };

        socket.onclose = () => {
          wsReconnectTimeout = setTimeout(() => connectWS(pId), 5000);
        };

        socket.onerror = (err) => {
          console.warn("WS error:", err);
          socket?.close();
        };
      } catch (e) {
        console.error("WS connect failed:", e);
      }
    };

    const fetchCampaign = async () => {
      try {
        let pId = null;
        if (typeof window !== "undefined") {
          const params = new URLSearchParams(window.location.search);
          pId = params.get("product_id");
          if (!pId) {
            pId = localStorage.getItem("latest_product_id");
          }
        }

        if (!pId) {
          const prodRes = await fetch(`${API_BASE}/product`);
          const prodList = await prodRes.json();
          if (prodList && prodList.length > 0) {
            pId = prodList[prodList.length - 1].id;
          }
        }

        if (pId) {
          setProductId(pId);
          connectWS(pId);

          // Fetch initial campaign details (could be placeholders initially)
          const campRes = await fetch(`${API_BASE}/campaign/${pId}`);
          if (campRes.ok) {
            const data = await campRes.json();
            setCampaignData(data);
          }

          const pollPipeline = async () => {
            try {
              const statusRes = await fetch(`${API_BASE}/generate-content/status/${pId}`);
              if (statusRes.ok) {
                const statusData = await statusRes.json();
                setJobStatus(statusData.status);
                setJobMessage(statusData.step_message || "");
                setJobProgressStep(statusData.current_step || 0);

                if (statusData.agents) {
                  setAgents(statusData.agents);
                }
                if (statusData.progress_percent !== undefined) {
                  setProgressPercent(statusData.progress_percent);
                }
                if (statusData.estimated_remaining_time !== undefined) {
                  setEstimatedTime(statusData.estimated_remaining_time);
                }
                if (statusData.agent_durations) {
                  setAgentDurations(statusData.agent_durations);
                }
                if (statusData.elapsed_time !== undefined) {
                  setElapsedTime(statusData.elapsed_time);
                }
                if (statusData.current_agent !== undefined) {
                  setCurrentAgent(statusData.current_agent);
                }

                // Retrieve updated campaign data inline
                const updateCampRes = await fetch(`${API_BASE}/campaign/${pId}`);
                if (updateCampRes.ok) {
                  const updateData = await updateCampRes.json();
                  setCampaignData(updateData);
                }

                if (statusData.status === "completed" || statusData.status === "failed") {
                  clearInterval(pollInterval);
                }
              }
            } catch (pollErr) {
              console.error("Error in status polling:", pollErr);
            }
          };

          // Fetch immediately
          await pollPipeline();
          setLoading(false);

          // Poll every 3 seconds for extremely responsive visual updates!
          pollInterval = setInterval(pollPipeline, 3000);
        }
      } catch (err) {
        console.error("Failed to load generated campaign:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchCampaign();
    return () => {
      if (pollInterval) clearInterval(pollInterval);
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
      clearTimeout(wsReconnectTimeout);
    };
  }, [pollTrigger]);

  const [campaignData, setCampaignData] = useState<any>({
    product: { name: "Fiddle Leaf Fig", price: 499.00 },
    keywords: {
      primary: ["fiddle leaf fig", "buy indoor plants"],
      secondary: ["green haven nursery", "plant shop online"],
      long_tail: ["fiddle leaf fig plant care guide", "best air purifying indoor plants"],
      intent: ["order fiddle leaf fig price", "buy house plants online"],
      regional: ["nursery in kottayam", "kerala plants delivery"]
    },
    script: {
      title: "Nursery Greenery Launch Campaign",
      hook: "Are your house plants constantly dying? 🌿",
      problem: "Normal nursery plants go into shock due to heavy clay soil.",
      solution: "Green Haven root-conditioned Fiddle Leaf Fig comes in a coco-peat blend with a care guide.",
      showcase: "Air-purifying glossy fiddle-shaped leaves, robust root structure, zero chemicals.",
      benefits: "Perfect home decoration, boosts room humidity, easy maintenance, includes detailed care guide.",
      cta: "Reply now to get a free plant care PDF and 10% off your first order!",
      thumbnail_text: "Beautiful Fiddle Leaf Fig!",
      thumbnail_prompt: "Fiddle leaf fig plant in a modern white ceramic pot, sunlit minimal room background"
    },
    videos: {}
  });

  const [editedTitle, setEditedTitle] = useState("");
  const [editedHook, setEditedHook] = useState("");
  const [editedScriptText, setEditedScriptText] = useState("");
  const [selectedVoiceProfile, setSelectedVoiceProfile] = useState("Storyteller");
  const [selectedSpeedRate, setSelectedSpeedRate] = useState("-7%");
  const [approving, setApproving] = useState(false);

  const scriptStatus = campaignData?.script?.status || "draft";
  const hasAnyVideo = Object.values(campaignData?.videos || {}).some(
    (v: any) => v && v.video_url && !v.video_url.includes("generating")
  );
  const isVideoReady = hasAnyVideo || scriptStatus === "locked";

  useEffect(() => {
    if (campaignData?.script) {
      setEditedTitle(prev => prev || campaignData.script.title || "");
      setEditedHook(prev => prev || campaignData.script.hook || "");
      setEditedScriptText(prev => prev || campaignData.script.script_text || "");
    }
  }, [campaignData]);

  const handleApproveScript = async () => {
    let pId = productId;
    if (!pId) {
      try {
        const prodRes = await fetch(`${API_BASE}/product`);
        const prodList = await prodRes.json();
        if (prodList && prodList.length > 0) {
          pId = prodList[prodList.length - 1].id;
          setProductId(pId);
        }
      } catch (e) {
        console.error("Failed to fetch product list for script approval:", e);
      }
    }
    if (!pId) {
      alert("No active campaign product found. Please select a product from dashboard.");
      return;
    }

    setApproving(true);
    try {
      const res = await fetch(`${API_BASE}/campaign/approve-script`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          product_id: pId,
          title: editedTitle,
          hook: editedHook,
          script_text: editedScriptText,
          voice_profile: selectedVoiceProfile,
          speed_rate: selectedSpeedRate,
          pitch: "+0Hz"
        })
      });
      if (res.ok) {
        setJobStatus("running");
        setPollTrigger(prev => prev + 1);
      } else {
        const errorData = await res.json();
        alert(`Error locking script: ${errorData.detail || "unknown error"}`);
      }
    } catch (err) {
      console.error("Failed to approve script:", err);
    } finally {
      setApproving(false);
    }
  };

  const handleApproveVideo = async () => {
    let pId = productId;
    if (!pId) {
      try {
        const prodRes = await fetch(`${API_BASE}/product`);
        const prodList = await prodRes.json();
        if (prodList && prodList.length > 0) {
          pId = prodList[prodList.length - 1].id;
          setProductId(pId);
        }
      } catch (e) {
        console.error("Failed to resolve product for video approval:", e);
      }
    }

    setApproving(true);
    try {
      const activeVideo = campaignData?.videos?.[selectedLang];
      const videoId = activeVideo?.id;
      if (videoId) {
        await fetch(`${API_BASE}/approve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            video_id: videoId,
            status: "approved"
          })
        });
      }
      window.location.href = `/approval?product_id=${pId || ""}`;
    } catch (err) {
      console.error("Failed to approve video:", err);
      window.location.href = `/approval?product_id=${pId || ""}`;
    } finally {
      setApproving(false);
    }
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const languages = ["English", "Hindi", "Tamil", "Telugu", "Malayalam"];
  const activeTranslations = {
    English: {
      title: "Nursery Greenery Launch Campaign",
      hook: "Are your house plants constantly dying? 🌿",
      problem: "Normal nursery plants go into shock due to heavy clay soil.",
      solution: "Green Haven root-conditioned Fiddle Leaf Fig comes in a coco-peat blend with a care guide.",
      cta: "Reply now to get a free plant care PDF and 10% off your first order!"
    },
    Hindi: {
      title: "नर्सरी हरियाली अभियान",
      hook: "क्या आपके घर के पौधे बार-बार सूख जाते हैं? 🌿",
      problem: "सामान्य नर्सरी पौधे भारी मिट्टी के कारण शॉक में चले जाते हैं।",
      solution: "ग्रीन हेवन नर्सरी का फिडेल लीफ फिग कोको-पीट मिश्रण और केयर गाइड के साथ आता है।",
      cta: "अभी उत्तर दें और प्लांट केयर गाइड के साथ 10% की छूट पाएं!"
    },
    Tamil: {
      title: "பசுமை இல்ல பிரச்சாரம்",
      hook: "உங்கள் வீட்டு செடிகள் அடிக்கடி காய்ந்து விடுகிறதா? 🌿",
      problem: "வழக்கமான செடிகள் களிமண்ணில் வளர்க்கப்படுவதால் சீக்கிரம் வாடிவிடுகின்றன.",
      solution: "எங்கள் ஃபிடில் லீஃப் பிக் செடிகள் மாற்று மண் கலவையுடன் எளிதான பராமரிப்பு குறிப்புகளுடன் வருகின்றன.",
      cta: "இப்போதே பதிலளித்து, இலவச பராமரிப்பு வழிகாட்டி மற்றும் 10% தள்ளுபடி பெறுங்கள்!"
    },
    Telugu: {
      title: "గ్రీన్ హేవెన్ నర్సరీ ప్రచారం",
      hook: "మీ ఇంట్లోని మొక్కలు తరచుగా చనిపోతున్నాయా? 🌿",
      problem: "సాధారణ నర్సరీ మొక్కలు బంకమట్టి వల్ల త్వరగా ఎండిపోతాయి.",
      solution: "మా ప్రీమియం ఫిడిల్ లీఫ్ ఫిగ్ ప్రత్యేక కోకో-పీట్ మరియు కేర్ గైడ్ తో లభిస్తుంది.",
      cta: "ఇప్పుడే సమాధానం ఇవ్వండి మరియు 10% తగ్గింపు పొందండి!"
    },
    Malayalam: {
      title: "ഹരിത ഗൃഹ കാമ്പയിൻ",
      hook: "നിങ്ങളുടെ വീട്ടിലെ ചെടികൾ പെട്ടെന്ന് ഉണങ്ങിപ്പോകാറുണ്ടോ? 🌿",
      problem: "സാധാരണ നഴ്സറി ചെടികൾ കനത്ത കളിമണ്ണിൽ വളരുന്നതിനാൽ എളുപ്പം നശിച്ചുപോകുന്നു.",
      solution: "ഞങ്ങളുടെ ഫിഡിൽ ലീഫ് ഫിഗ് ചെടി പ്രത്യേക കോക്കോപീറ്റ് മിശ്രിതത്തിലും പരിചരണ സഹായിയോടും കൂടി വരുന്നു.",
      cta: "ഇപ്പോൾ തന്നെ ഓർഡർ ചെയ്യൂ, സൌജന്യ പ്ലാന്റ് കെയർ ഗൈഡും 10% ഡിസ്കൗണ്ടും സ്വന്തമാക്കൂ!"
    }
  };

  const dynamicText = campaignData?.translations?.[selectedLang];

  const activeText = dynamicText ? {
    youtube_script: dynamicText.youtube_script,
    reel_script: dynamicText.reel_script,
    whatsapp_post: dynamicText.whatsapp_post,
    google_business_post: dynamicText.google_business_post,
    hook: dynamicText.youtube_script,
    problem: dynamicText.reel_script,
    solution: dynamicText.whatsapp_post,
    cta: dynamicText.google_business_post
  } : {
    youtube_script: activeTranslations[selectedLang as keyof typeof activeTranslations]?.hook || "",
    reel_script: activeTranslations[selectedLang as keyof typeof activeTranslations]?.solution || "",
    whatsapp_post: activeTranslations[selectedLang as keyof typeof activeTranslations]?.cta || "",
    google_business_post: activeTranslations[selectedLang as keyof typeof activeTranslations]?.title || "",
    hook: activeTranslations[selectedLang as keyof typeof activeTranslations]?.hook || "",
    problem: activeTranslations[selectedLang as keyof typeof activeTranslations]?.problem || "",
    solution: activeTranslations[selectedLang as keyof typeof activeTranslations]?.solution || "",
    cta: activeTranslations[selectedLang as keyof typeof activeTranslations]?.cta || ""
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-12 h-12 rounded-full border-4 border-t-indigo-500 border-slate-800 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Live progress banner */}
      {jobStatus === "running" && (
        <div className="bg-slate-900 border border-slate-850 rounded-xl p-5 mb-6 space-y-3 shadow-lg">
          <div className="flex justify-between items-center text-xs font-semibold text-slate-200">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full border-2 border-t-indigo-500 border-slate-700 animate-spin" />
              <span className={jobMessage.includes("Delayed") ? "text-amber-400 font-semibold" : "text-slate-200"}>
                {jobMessage || "Generating video campaign assets..."}
              </span>
            </div>
            <span className="text-indigo-400 font-bold uppercase tracking-wider">
              {progressPercent}% Complete
            </span>
          </div>
          <div className="w-full bg-slate-850 rounded-full h-2 overflow-hidden">
            <div
              className="bg-indigo-500 h-2 rounded-full transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <div className="flex justify-between items-center text-[10px] text-slate-450 uppercase font-semibold gap-4">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span>Keyword: <span className={agents.KeywordAgent === "Running" ? "text-indigo-400 font-bold" : agents.KeywordAgent === "Failed" ? "text-rose-450" : "text-slate-500"}>{agents.KeywordAgent}</span></span>
              <span>•</span>
              <span>Screenplay: <span className={agents.ScreenplayAgent === "Running" ? "text-indigo-400 font-bold" : agents.ScreenplayAgent === "Failed" ? "text-rose-450" : "text-slate-500"}>{agents.ScreenplayAgent}</span></span>
              <span>•</span>
              <span>Thumbnail: <span className={agents.ThumbnailAgent === "Running" ? "text-indigo-400 font-bold" : agents.ThumbnailAgent === "Failed" ? "text-rose-450" : "text-slate-500"}>{agents.ThumbnailAgent}</span></span>
              {currentAgent && (
                <>
                  <span>•</span>
                  <span className="text-indigo-400 font-bold">Active Agent: {currentAgent}</span>
                </>
              )}
            </div>
            <div className="flex gap-3 whitespace-nowrap">
              <span>Elapsed: {elapsedTime}s</span>
              <span>Est. remaining: ~{estimatedTime}s</span>
            </div>
          </div>
        </div>
      )}

      {/* Failed campaign alert banner */}
      {jobStatus === "failed" && (
        <div className="bg-rose-950/40 border border-rose-500/30 rounded-2xl p-5 mb-6 space-y-3 shadow-lg backdrop-blur-md">
          <div className="flex justify-between items-center text-xs font-semibold text-rose-200">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 animate-bounce" />
              <span>Campaign generation failed: {jobMessage || "An error occurred."}</span>
            </div>
            <button
              onClick={handleRegenerate}
              className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold rounded-lg transition"
            >
              Regenerate Campaign
            </button>
          </div>
        </div>
      )}

      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            Campaign Assets Review
          </h1>
          <p className="text-slate-400 mt-2">
            Audit structured copy hooks, thumbnail layout prompts, and keywords categorized by our agents.
          </p>
        </div>

        {/* Toggle details */}
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-xl p-1 gap-1">
            <button
              onClick={() => setVersion(1)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition ${version === 1 ? "bg-slate-800 text-white border border-slate-700" : "text-slate-500"
                }`}
            >
              V1 (QA: {campaignData?.qa_score || 85})
            </button>
            <button
              disabled
              className="px-3 py-1.5 rounded-lg text-xs font-bold text-slate-700"
            >
              V2 (Draft)
            </button>
          </div>

          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-xl p-1 gap-1">
            {languages.map(lang => (
              <button
                key={lang}
                onClick={() => setSelectedLang(lang)}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold transition ${selectedLang === lang ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-slate-200"
                  }`}
              >
                <Languages className="w-3.5 h-3.5" />
                {lang}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

        {/* Expanded Keyword Groups */}
        <div className="lg:col-span-2 space-y-6">
          <div className="glass-panel rounded-2xl p-6">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <Tag className="w-5 h-5 text-indigo-400" />
              SEO Keywords Classification (KeywordAgent)
            </h3>

            {agents.KeywordAgent !== "Completed" ? (
              <div className="flex flex-col items-center justify-center py-8 text-center space-y-3">
                {agents.KeywordAgent === "Running" ? (
                  <>
                    <div className="w-8 h-8 rounded-full border-2 border-t-indigo-500 border-slate-855 animate-spin" />
                    <p className="text-xs font-semibold text-slate-350">KeywordAgent is analyzing product tags...</p>
                  </>
                ) : agents.KeywordAgent === "Failed" ? (
                  <>
                    <div className="text-rose-450 text-xs font-semibold">Keyword classification failed or timed out.</div>
                    <button
                      onClick={() => handleRetryAgent("KeywordAgent")}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-lg transition"
                    >
                      Retry Keyword Agent
                    </button>
                  </>
                ) : (
                  <p className="text-xs text-slate-500">KeywordAgent is queued...</p>
                )}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Primary Keywords</span>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {campaignData?.keywords?.primary?.map((kw: string) => (
                      <span key={kw} className="bg-slate-900 border border-slate-800 text-xs px-2.5 py-1 rounded-lg text-slate-300">#{kw}</span>
                    )) || <span className="text-xs text-slate-650">None found</span>}
                  </div>
                </div>

                <div>
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Secondary Keywords</span>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {campaignData?.keywords?.secondary?.map((kw: string) => (
                      <span key={kw} className="bg-slate-900 border border-slate-800 text-xs px-2.5 py-1 rounded-lg text-slate-300">#{kw}</span>
                    )) || <span className="text-xs text-slate-650">None found</span>}
                  </div>
                </div>

                <div>
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Long Tail Keywords</span>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {campaignData?.keywords?.long_tail?.map((kw: string) => (
                      <span key={kw} className="bg-slate-900 border border-slate-800 text-xs px-2.5 py-1 rounded-lg text-slate-300">#{kw}</span>
                    )) || <span className="text-xs text-slate-650">None found</span>}
                  </div>
                </div>

                <div>
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Regional Keywords</span>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {campaignData?.keywords?.regional?.map((kw: string) => (
                      <span key={kw} className="bg-slate-900 border border-slate-800 text-xs px-2.5 py-1 rounded-lg text-slate-300">#{kw}</span>
                    )) || <span className="text-xs text-slate-650">None found</span>}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Structured Script View */}
          <div className="glass-panel rounded-2xl p-6 space-y-6">
            <h3 className="text-lg font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-3">
              <Film className="w-5 h-5 text-indigo-400" />
              Structured Screenplay Script ({selectedLang})
            </h3>

            {agents.ScreenplayAgent !== "Completed" ? (
              <div className="flex flex-col items-center justify-center py-12 text-center space-y-3">
                {agents.ScreenplayAgent === "Running" ? (
                  <>
                    <div className="w-8 h-8 rounded-full border-2 border-t-indigo-500 border-slate-855 animate-spin" />
                    <p className="text-xs font-semibold text-slate-350">ScreenplayAgent is writing copy and dialogue hooks...</p>
                  </>
                ) : agents.ScreenplayAgent === "Failed" ? (
                  <>
                    <div className="text-rose-455 text-xs font-semibold">Screenplay generation failed or timed out.</div>
                    <button
                      onClick={() => handleRetryAgent("ScreenplayAgent")}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-lg transition"
                    >
                      Retry Screenplay Agent
                    </button>
                  </>
                ) : (
                  <p className="text-xs text-slate-500">ScreenplayAgent is waiting for keywords...</p>
                )}
              </div>
            ) : (
              <div className="space-y-6">
                {/* Master Script Fields (Editable if draft) */}
                <div className="space-y-4 p-4 rounded-xl bg-slate-900/30 border border-slate-800">
                  <div className="flex justify-between items-center pb-2 border-b border-slate-800">
                    <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">Master Campaign Script (English Source)</span>
                    {scriptStatus === "locked" ? (
                      <span className="flex items-center gap-1 text-[9px] bg-emerald-950 border border-emerald-500/30 text-emerald-450 font-bold px-2 py-0.5 rounded-full">
                        <Check className="w-2.5 h-2.5" /> Locked &amp; Approved
                      </span>
                    ) : (
                      <span className="text-[9px] bg-indigo-950 border border-indigo-550/30 text-indigo-400 font-bold px-2 py-0.5 rounded-full">
                        Draft Mode (Editable)
                      </span>
                    )}
                  </div>

                  <div className="space-y-3">
                    <div>
                      <label className="text-[9px] font-bold text-slate-455 block mb-1">Campaign Title</label>
                      <input
                        type="text"
                        value={editedTitle}
                        onChange={(e) => setEditedTitle(e.target.value)}
                        disabled={scriptStatus === "locked"}
                        className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500/80 rounded-lg p-2.5 text-xs text-slate-200 transition focus:outline-none disabled:opacity-60"
                        placeholder="Campaign Title"
                      />
                    </div>

                    <div>
                      <label className="text-[9px] font-bold text-slate-455 block mb-1">Creative Hook</label>
                      <textarea
                        rows={2}
                        value={editedHook}
                        onChange={(e) => setEditedHook(e.target.value)}
                        disabled={scriptStatus === "locked"}
                        className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500/80 rounded-lg p-2.5 text-xs text-slate-200 transition focus:outline-none resize-none disabled:opacity-60"
                        placeholder="Campaign Hook"
                      />
                    </div>

                    <div>
                      <label className="text-[9px] font-bold text-slate-455 block mb-1">Voiceover Dialogue Screenplay</label>
                      <textarea
                        rows={5}
                        value={editedScriptText}
                        onChange={(e) => setEditedScriptText(e.target.value)}
                        disabled={scriptStatus === "locked"}
                        className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500/80 rounded-lg p-2.5 text-xs text-slate-200 leading-relaxed transition focus:outline-none disabled:opacity-60"
                        placeholder="Voiceover Screenplay Script Text"
                      />
                    </div>
                  </div>
                </div>

                {/* Localized Translations Preview Blocks */}
                <div className="space-y-4 pt-2">
                  <div className="flex items-center justify-between pb-1 border-b border-slate-800">
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wide">Localized Translations Preview ({selectedLang})</span>
                  </div>

                  {/* YouTube Script */}
                  <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80">
                    <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest block mb-1">YouTube Campaign Voiceover Script</span>
                    <p className="text-sm text-slate-200">{activeText.youtube_script || activeText.hook || ""}</p>
                  </div>

                  {/* Reel Script */}
                  <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80">
                    <span className="text-[10px] font-bold text-purple-400 uppercase tracking-widest block mb-1">Instagram Reel / Shorts Script</span>
                    <p className="text-sm text-slate-200">{activeText.reel_script || activeText.solution || ""}</p>
                  </div>

                  {/* WhatsApp Post */}
                  <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80">
                    <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest block mb-1">WhatsApp Broadcast Post</span>
                    <p className="text-sm text-slate-200 whitespace-pre-wrap">{activeText.whatsapp_post || activeText.cta || ""}</p>
                  </div>

                  {/* Google Business Post */}
                  <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80">
                    <span className="text-[10px] font-bold text-sky-400 uppercase tracking-widest block mb-1">Google Business Update Post</span>
                    <p className="text-sm text-slate-200">{activeText.google_business_post || ""}</p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Thumbnail layouts and preview */}
        <div className="space-y-6">
          <div className="glass-panel rounded-2xl p-6 space-y-4">
            <h3 className="text-lg font-bold text-white border-b border-slate-800 pb-3 flex items-center gap-2">
              <ImageIcon className="w-5 h-5 text-indigo-400" />
              Clickable Thumbnail layout (ThumbnailAgent)
            </h3>

            {agents.ThumbnailAgent !== "Completed" || agents.ImagePromptAgent !== "Completed" ? (
              <div className="flex flex-col items-center justify-center py-8 text-center space-y-3">
                {agents.ThumbnailAgent === "Running" || agents.ImagePromptAgent === "Running" ? (
                  <>
                    <div className="w-8 h-8 rounded-full border-2 border-t-indigo-500 border-slate-850 animate-spin" />
                    <p className="text-xs font-semibold text-slate-350">Thumbnail & ImagePrompt agents are designing CTR layouts...</p>
                  </>
                ) : (agents.ThumbnailAgent === "Failed" || agents.ImagePromptAgent === "Failed") ? (
                  <>
                    <div className="text-rose-455 text-xs font-semibold">Thumbnail layout design failed or timed out.</div>
                    <div className="flex gap-2 justify-center">
                      {agents.ThumbnailAgent === "Failed" && (
                        <button
                          onClick={() => handleRetryAgent("ThumbnailAgent")}
                          className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-lg transition"
                        >
                          Retry Layout
                        </button>
                      )}
                      {agents.ImagePromptAgent === "Failed" && (
                        <button
                          onClick={() => handleRetryAgent("ImagePromptAgent")}
                          className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-lg transition"
                        >
                          Retry Image Prompt
                        </button>
                      )}
                    </div>
                  </>
                ) : (
                  <p className="text-xs text-slate-500">Thumbnail layout design queued...</p>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                {campaignData?.thumbnail?.image_url && (
                  <div>
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wide block mb-1.5">Generated Thumbnail Image</span>
                    <div className="rounded-xl overflow-hidden border border-slate-800 bg-slate-950 aspect-video relative group mb-3">
                      <img 
                        src={`${API_BASE}${campaignData.thumbnail.image_url}`} 
                        alt="Generated Campaign Thumbnail" 
                        className="w-full h-full object-cover transition duration-300 group-hover:scale-105"
                      />
                      <div className="absolute inset-0 bg-slate-950/20 group-hover:bg-transparent transition" />
                    </div>
                  </div>
                )}

                <div>
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Text Overlay</span>
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 text-xs text-white font-bold mt-1.5 uppercase">
                    "{campaignData?.script?.thumbnail_text || ""}"
                  </div>
                </div>

                <div>
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Image Model Prompt</span>
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 text-xs text-slate-400 leading-relaxed mt-1.5 italic">
                    "{campaignData?.script?.thumbnail_prompt || ""}"
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="glass-panel rounded-2xl p-6 text-center">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wide mb-4 text-left">Vertical Video Preview</h3>
            {(() => {
              const videoObj = campaignData?.videos?.[selectedLang];
              const hasVideo = !!(videoObj?.video_url || videoObj?.youtube_url);

              // 1. If no video has been generated and script is still awaiting approval, guide script approval
              if (!hasVideo && scriptStatus !== "locked" && jobStatus !== "completed") {
                return (
                  <div className="w-full aspect-[9/16] max-h-[450px] rounded-2xl bg-slate-900/60 border border-slate-800 p-6 flex flex-col items-center justify-center text-center space-y-4 shadow-2xl">
                    <div className="w-12 h-12 rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                      <Film className="w-6 h-6 animate-pulse" />
                    </div>
                    <div>
                      <h4 className="font-extrabold text-sm text-slate-200">Script Review Phase</h4>
                      <span className="text-[10px] text-indigo-400 font-bold block mt-1 uppercase tracking-wide">
                        Awaiting Script Approval
                      </span>
                      <p className="text-xs text-slate-455 mt-3 max-w-xs mx-auto leading-relaxed">
                        Configure your desired voice profile and rate in the controls panel, review the screenplay copy, and click "Approve Script &amp; Render Video" below to generate voiceover audios and video slideshows.
                      </p>
                    </div>
                  </div>
                );
              }
              const youtubeUrl = videoObj?.youtube_url;
              const youtubeId = videoObj?.youtube_id || (youtubeUrl ? (() => {
                const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
                const match = youtubeUrl.match(regExp);
                return (match && match[2].length === 11) ? match[2] : null;
              })() : null);

              if (youtubeId) {
                return (
                  <div className="w-full aspect-video rounded-2xl bg-slate-950 border border-slate-800 overflow-hidden relative shadow-2xl">
                    <iframe
                      className="w-full h-full"
                      src={`https://www.youtube.com/embed/${youtubeId}`}
                      title="YouTube video player"
                      frameBorder="0"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                      allowFullScreen
                    ></iframe>
                  </div>
                );
              }

              if (videoObj?.video_url) {
                const videoId = videoObj.id;

                const isVideoRendering = agents.VideoAgent === "Running" || 
                                        agents.VoiceoverAgent === "Running" || 
                                        (jobStatus === "running" && progressPercent < 100 && agents.VideoAgent !== "Completed");

                if (isVideoRendering) {
                  return (
                    <div className="w-full aspect-[9/16] max-h-[450px] rounded-2xl bg-slate-950 border border-slate-800 p-6 flex flex-col items-center justify-center text-center space-y-4 shadow-2xl">
                      <div className="w-12 h-12 rounded-full border-4 border-t-indigo-500 border-slate-800 animate-spin" />
                      <div>
                        <h4 className="font-extrabold text-sm text-slate-200">Rendering MP4 Video Stream</h4>
                        <p className="text-[10px] text-indigo-400 mt-2 font-bold animate-pulse uppercase tracking-wider">
                          Stitching MP4 Frames &amp; Voiceovers ({progressPercent}%)...
                        </p>
                      </div>
                    </div>
                  );
                }

                if (agents.VoiceoverAgent === "Failed" || agents.VideoAgent === "Failed") {
                  return (
                    <div className="w-full aspect-[9/16] max-h-[450px] rounded-2xl bg-slate-950 border border-slate-800 p-6 flex flex-col items-center justify-center text-center space-y-4 shadow-2xl">
                      <div className="text-rose-450 text-xs font-semibold">Video compilation failed or timed out.</div>
                      <button
                        onClick={() => handleRetryAgent(agents.VideoAgent === "Failed" ? "VideoAgent" : "VoiceoverAgent")}
                        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-lg transition cursor-pointer"
                      >
                        Retry Video Agent
                      </button>
                    </div>
                  );
                }

                if (repairing) {
                  return (
                    <div className="w-full aspect-[9/16] max-h-[450px] rounded-2xl bg-slate-950 border border-slate-800 p-6 flex flex-col items-center justify-center text-center space-y-4 shadow-2xl">
                      <div className="w-12 h-12 rounded-full border-4 border-t-indigo-500 border-slate-800 animate-spin" />
                      <div>
                        <h4 className="font-extrabold text-sm text-slate-200">Auto-Repairing Video</h4>
                        <p className="text-[11px] text-slate-400 mt-2 max-w-[200px] leading-relaxed">
                          {repairMessage}
                        </p>
                      </div>
                    </div>
                  );
                }

                if (videoError && jobStatus !== "running") {
                  return (
                    <div className="w-full aspect-[9/16] max-h-[450px] rounded-2xl bg-slate-950 border border-slate-800 p-6 flex flex-col items-center justify-center text-center space-y-4 shadow-2xl">
                      <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
                        <AlertTriangle className="w-6 h-6" />
                      </div>
                      <div>
                        <h4 className="font-extrabold text-sm text-rose-400">Playback Failed</h4>
                        <p className="text-[10px] text-slate-400 mt-1 max-w-[200px] leading-relaxed">
                          {videoError}
                        </p>
                      </div>
                      <button
                        onClick={() => handleRepairVideo(videoId)}
                        className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2 rounded-xl transition cursor-pointer"
                      >
                        Auto-Repair Video File
                      </button>
                    </div>
                  );
                }

                return (
                  <div className="w-full rounded-2xl bg-slate-950 border border-slate-800 overflow-hidden relative shadow-2xl flex items-center justify-center p-2">
                    <video
                      key={`${selectedLang}_${version}_${videoObj.video_url}`}
                      controls
                      playsInline
                      preload="metadata"
                      className="w-full max-h-[450px] rounded-xl"
                      src={(() => {
                        const raw = videoObj.video_url.startsWith("http") ? videoObj.video_url : `${API_BASE}${videoObj.video_url}`;
                        return raw.includes("?") ? raw : `${raw}?v=${version}`;
                      })()}
                      onError={(e) => {
                        console.error("Video load error: ", e);
                        if (jobStatus === "running" || agents.VideoAgent === "Running") {
                          console.log("Video is currently rendering on backend, skipping error overlay.");
                          return;
                        }
                        if (videoId) {
                          handleRepairVideo(videoId);
                        } else {
                          setVideoError("The video file could not be played. No video ID was found to trigger auto-repair.");
                        }
                      }}
                    >
                      Your browser does not support the video tag.
                    </video>
                  </div>
                );
              }

              return (
                <div className="glass-panel bg-slate-900/60 border border-slate-800 rounded-2xl p-6 text-center flex flex-col items-center justify-center min-h-[300px] space-y-4 shadow-xl">
                  <div className="w-12 h-12 rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                    <Film className="w-6 h-6 animate-pulse" />
                  </div>
                  <div>
                    <h4 className="font-extrabold text-sm text-slate-200">Video Draft Stitched</h4>
                    <span className="text-[10px] text-indigo-400 font-bold block mt-1 uppercase tracking-wide">
                      Status: Ready for Publishing
                    </span>
                    <p className="text-xs text-slate-455 mt-3 max-w-xs mx-auto leading-relaxed">
                      This localized video draft is successfully compiled. To ensure visual excellence and compliance, you can watch it once published to YouTube.
                    </p>
                  </div>
                </div>
              );
            })()}

            {/* AI Voice Synthesizer Settings controls */}
            <div className="border-t border-slate-800/80 pt-5 mt-5 space-y-4 text-left">
              <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest block">AI Voice Synthesizer Settings</span>
              
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[9px] font-bold text-slate-455 uppercase block mb-1">Voice Profile</label>
                  <select
                    value={selectedVoiceProfile}
                    onChange={(e) => setSelectedVoiceProfile(e.target.value)}
                    disabled={scriptStatus === "locked"}
                    className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 rounded-lg px-2.5 py-2 text-xs text-slate-200 focus:outline-none disabled:opacity-60"
                  >
                    <option value="Storyteller">Storyteller (Warm)</option>
                    <option value="Presenter">Presenter (Professional)</option>
                    <option value="Nursery">Nursery Owner (Friendly)</option>
                  </select>
                </div>

                <div>
                  <label className="text-[9px] font-bold text-slate-455 uppercase block mb-1">Speaking Speed</label>
                  <select
                    value={selectedSpeedRate}
                    onChange={(e) => setSelectedSpeedRate(e.target.value)}
                    disabled={scriptStatus === "locked"}
                    className="w-full bg-slate-900 border border-slate-800 focus:border-indigo-500 rounded-lg px-2.5 py-2 text-xs text-slate-200 focus:outline-none disabled:opacity-60"
                  >
                    <option value="-12%">Slow (-12%)</option>
                    <option value="-7%">Natural (-7%)</option>
                    <option value="+0%">Normal (+0%)</option>
                    <option value="+5%">Fast (+5%)</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Action buttons */}
            <div className="space-y-3 mt-6">
              {!isVideoReady ? (
                <>
                  <button
                    onClick={handleApproveScript}
                    disabled={approving}
                    className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3.5 rounded-xl transition text-sm shadow-lg cursor-pointer disabled:opacity-50"
                  >
                    {approving ? "Submitting Script Approval..." : "Approve Script & Render Video"}
                  </button>
                  <button
                    onClick={handleRegenerate}
                    className="w-full bg-slate-850 hover:bg-slate-800 border border-slate-700/60 text-slate-350 hover:text-white py-2.5 rounded-xl transition text-xs cursor-pointer"
                  >
                    Reject &amp; Regenerate Draft
                  </button>
                </>
              ) : (
                <div className="flex gap-3">
                  <button
                    onClick={handleRegenerate}
                    className="flex-1 bg-slate-850 hover:bg-slate-800 border border-slate-700/60 text-slate-200 hover:text-white font-bold py-3.5 rounded-xl transition text-center text-xs cursor-pointer"
                  >
                    Reject &amp; Regenerate
                  </button>
                  <button
                    onClick={handleApproveVideo}
                    disabled={approving}
                    className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3.5 rounded-xl transition text-center text-xs shadow-lg cursor-pointer disabled:opacity-50"
                  >
                    {approving ? "Approving Video..." : "Approve Video & Publish"}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
