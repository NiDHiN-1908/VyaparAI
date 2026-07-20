// frontend/app/comment-inbox/page.tsx
"use client";

import { useEffect, useState } from "react";
import { 
  MessageSquare, Search, Filter, Sparkles, Send, RefreshCw, 
  ToggleLeft, ToggleRight, CheckSquare, Check, X, AlertCircle, Calendar, Settings, Activity 
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function CommentInbox() {
  const [loading, setLoading] = useState(true);
  const [comments, setComments] = useState<any[]>([]);
  const [monitoredVideos, setMonitoredVideos] = useState<any[]>([]);
  const [selectedVideo, setSelectedVideo] = useState("ALL");
  const [search, setSearch] = useState("");
  const [intentFilter, setIntentFilter] = useState("ALL");
  const [statusTab, setStatusTab] = useState("ALL"); // "ALL" | "pending_approval" | "replied" | "rejected"
  const [autoReply, setAutoReply] = useState(false);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.80);
  const [whatsappStatus, setWhatsappStatus] = useState<string>("disconnected");
  const [error, setError] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState("");
  const [lastSynced, setLastSynced] = useState<string>("");
  const [videoSearch, setVideoSearch] = useState("");

  // Comment simulator state
  const [simVideo, setSimVideo] = useState("");
  const [simUsername, setSimUsername] = useState("nisha_rao");
  const [simComment, setSimComment] = useState("I need to order 5 packs of this. Do you ship to Mumbai?");
  const [simStatus, setSimStatus] = useState("");
  const [simLoading, setSimLoading] = useState(false);

  // Inline action States
  const [editableReplies, setEditableReplies] = useState<Record<string, string>>({});
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});

  // Webhook settings state
  const [webhookConfig, setWebhookConfig] = useState<any>(null);
  const [webhookLoading, setWebhookLoading] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [activeTunnelUrl, setActiveTunnelUrl] = useState("");
  const [webhookValidation, setWebhookValidation] = useState<{ status: string; message: string; suggestions?: string[] }>({ status: "", message: "", suggestions: [] });
  const [webhookSaveStatus, setWebhookSaveStatus] = useState<{ status: string; message: string }>({ status: "", message: "" });
  const [localBackendStatus, setLocalBackendStatus] = useState<any>({ status: "", message: "", details: null });
  const [localBackendLoading, setLocalBackendLoading] = useState(false);
  const [publicTunnelStatus, setPublicTunnelStatus] = useState<any>({ status: "", message: "", details: null });
  const [publicTunnelLoading, setPublicTunnelLoading] = useState(false);

  async function fetchComments() {
    try {
      const res = await fetch(`${API_BASE}/youtube/comments`);
      const data = await res.json();
      if (data.status === "success" && data.data) {
        setComments(data.data);
        // Pre-populate textareas for pending replies
        const textMap: Record<string, string> = {};
        data.data.forEach((c: any) => {
          if (c.reply && c.status === "pending_approval") {
            textMap[c.comment_id] = c.reply.suggested_reply || "";
          }
        });
        setEditableReplies(prev => ({ ...textMap, ...prev }));
        setLastSynced(new Date().toLocaleTimeString());
      } else {
        setComments([]);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to connect to backend server.");
    } finally {
      setLoading(false);
    }
  }

  async function fetchVideos() {
    try {
      const res = await fetch(`${API_BASE}/youtube/videos`);
      const data = await res.json();
      if (data.status === "success" && data.data) {
        setMonitoredVideos(data.data);
        if (data.data.length > 0) {
          setSimVideo(data.data[0].video_id);
        }
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function checkWhatsAppStatus() {
    try {
      const res = await fetch(`${API_BASE}/whatsapp/instances?tenant_id=00000000-0000-0000-0000-000000000000`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === "success" && data.data) {
          // Look for any connected instance
          const hasConnected = data.data.some((inst: any) => inst.status === "connected");
          if (hasConnected) {
            setWhatsappStatus("connected");
            return;
          }
          // If none are connected, look for any connecting
          const hasConnecting = data.data.some((inst: any) => inst.status === "connecting");
          if (hasConnecting) {
            setWhatsappStatus("connecting");
            return;
          }
        }
      }
      setWhatsappStatus("disconnected");
    } catch (err) {
      console.warn("Failed to retrieve WhatsApp funnel status:", err);
      setWhatsappStatus("disconnected");
    }
  }

  async function checkSettings() {
    try {
      const res = await fetch(`${API_BASE}/youtube/settings/auto-reply`);
      const data = await res.json();
      setAutoReply(data.auto_reply);
      if (data.confidence_threshold !== undefined) {
        setConfidenceThreshold(data.confidence_threshold);
      }
    } catch (err) {
      console.warn("Settings API offline.");
    }
  }

  async function toggleAutoReply() {
    const nextVal = !autoReply;
    setAutoReply(nextVal);
    try {
      await fetch(`${API_BASE}/youtube/settings/auto-reply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ auto_reply: nextVal, confidence_threshold: confidenceThreshold })
      });
    } catch (err) {
      console.error(err);
    }
  }

  async function handleThresholdChange(val: number) {
    setConfidenceThreshold(val);
    try {
      await fetch(`${API_BASE}/youtube/settings/auto-reply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ auto_reply: autoReply, confidence_threshold: val })
      });
    } catch (err) {
      console.error(err);
    }
  }

  async function handleToggleVideoAutoReply(videoId: string, currentAutoReply: boolean) {
    const nextVal = !currentAutoReply;
    // Optimistic UI update
    setMonitoredVideos(prev => prev.map(v => v.video_id === videoId ? { ...v, auto_reply: nextVal } : v));
    try {
      const res = await fetch(`${API_BASE}/youtube/videos/${videoId}/auto-reply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ auto_reply: nextVal })
      });
      if (!res.ok) {
        // Revert on error
        setMonitoredVideos(prev => prev.map(v => v.video_id === videoId ? { ...v, auto_reply: currentAutoReply } : v));
        setStatusMsg("Failed to update video settings.");
        setTimeout(() => setStatusMsg(""), 3000);
      }
    } catch (err) {
      console.error(err);
      // Revert on error
      setMonitoredVideos(prev => prev.map(v => v.video_id === videoId ? { ...v, auto_reply: currentAutoReply } : v));
      setStatusMsg("Connection error.");
      setTimeout(() => setStatusMsg(""), 3000);
    }
  }

  async function handleRefresh() {
    setLoading(true);
    setStatusMsg("Syncing with YouTube...");
    try {
      await fetch(`${API_BASE}/youtube/comments/sync`, { method: "POST" });
    } catch (err) {
      console.warn("Sync failed, falling back to local load.", err);
    } finally {
      setStatusMsg("");
    }
    await fetchComments();
    await fetchVideos();
    await fetchWebhookConfig();
  }

  async function fetchWebhookConfig() {
    setWebhookLoading(true);
    try {
      const res = await fetch(`${API_BASE}/whatsapp/webhook-config?tenant_id=00000000-0000-0000-0000-000000000000`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === "success" && data.connected) {
          setWebhookConfig(data);
          setWebhookUrl(data.stored_webhook_url || data.suggested_webhook_url);
          
          const newTunnelUrl = data.active_tunnel_url || "";
          if (activeTunnelUrl && newTunnelUrl && activeTunnelUrl !== newTunnelUrl) {
            // Tunnel URL changed! Notify the user (Requirement 7)
            setStatusMsg(`Notice: Public tunnel regenerated! Webhook synced to: ${data.suggested_webhook_url}`);
            setTimeout(() => setStatusMsg(""), 8000);
          }
          
          setActiveTunnelUrl(newTunnelUrl);
        } else {
          setWebhookConfig(null);
          setActiveTunnelUrl("");
        }
      } else {
        setWebhookConfig(null);
        setActiveTunnelUrl("");
      }
    } catch (err) {
      console.warn("Failed to fetch webhook config:", err);
      setWebhookConfig(null);
      setActiveTunnelUrl("");
    } finally {
      setWebhookLoading(false);
    }
  }

  async function handleSaveWebhook(e: React.FormEvent) {
    e.preventDefault();
    if (!webhookConfig) return;
    setWebhookSaveStatus({ status: "saving", message: "Saving webhook configuration..." });
    try {
      const res = await fetch(`${API_BASE}/whatsapp/webhook-config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          instance_id: webhookConfig.instance_id,
          webhook_url: webhookUrl.trim()
        })
      });
      const data = await res.json();
      if (res.ok && data.status === "success") {
        setWebhookSaveStatus({ status: "success", message: "Webhook URL updated successfully!" });
        await fetchWebhookConfig();
        setTimeout(() => setWebhookSaveStatus({ status: "", message: "" }), 3000);
      } else {
        setWebhookSaveStatus({ status: "error", message: data.detail || "Failed to save webhook URL." });
      }
    } catch (err) {
      console.error(err);
      setWebhookSaveStatus({ status: "error", message: "Network error saving webhook." });
    }
  }

  async function handleValidateWebhook() {
    if (!webhookUrl.trim()) return;
    
    const targetUrl = webhookUrl.trim();
    setWebhookValidation({ status: "validating", message: `Validating reachability for: ${targetUrl}...`, suggestions: [] });
    try {
      const res = await fetch(`${API_BASE}/whatsapp/validate-webhook`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          webhook_url: targetUrl
        })
      });
      const data = await res.json();
      if (res.ok && data.reachable) {
        setWebhookValidation({ status: "success", message: data.message });
      } else {
        setWebhookValidation({ 
          status: "error", 
          message: data.message || `Endpoint ${data.validated_url || targetUrl} is unreachable.`,
          suggestions: data.recovery_suggestions || []
        });
      }
    } catch (err) {
      console.error(err);
      setWebhookValidation({ 
        status: "error", 
        message: "Connection check failed. Please check if the FastAPI backend is running and the public tunnel is online.",
        suggestions: [
          "Start backend server (run start_all.bat)",
          "Verify the public tunnel is active and synchronized"
        ]
      });
    }
  }

  async function handleTestLocalBackend() {
    setLocalBackendLoading(true);
    setLocalBackendStatus({ status: "checking", message: "Auditing local port and health check...", details: null });
    try {
      const res = await fetch(`${API_BASE}/whatsapp/test-local-backend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      const data = await res.json();
      if (res.ok && data.status === "success") {
        setLocalBackendStatus({
          status: "success",
          message: data.message,
          details: data
        });
      } else {
        setLocalBackendStatus({
          status: "error",
          message: data.message || "Failed to reach local backend.",
          details: data
        });
      }
    } catch (err) {
      console.error(err);
      setLocalBackendStatus({
        status: "error",
        message: "Failed to connect to local backend api endpoint.",
        details: {
          configured_port: 8000,
          is_listening: false,
          health_status: "offline",
          health_error: "Connection refused / API Server down"
        }
      });
    } finally {
      setLocalBackendLoading(false);
    }
  }

  async function handleTestPublicTunnel() {
    setPublicTunnelLoading(true);
    setPublicTunnelStatus({ status: "checking", message: "Auditing public tunnel forward and gateway...", details: null });
    try {
      const res = await fetch(`${API_BASE}/whatsapp/test-public-tunnel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      const data = await res.json();
      
      // Clear stale state and synchronize (Requirement 2)
      const isOk = res.ok && data.status === "success";
      setPublicTunnelStatus({
        status: isOk ? "success" : "error",
        message: data.message || "Diagnostics check complete.",
        details: data
      });
      
      const newUrl = data.public_tunnel_url || "";
      setActiveTunnelUrl(newUrl);
      if (newUrl) {
        setWebhookUrl(newUrl.replace(/\/$/, '') + '/webhooks/whatsapp');
      } else {
        setWebhookUrl("");
      }
    } catch (err) {
      console.error(err);
      setPublicTunnelStatus({
        status: "error",
        message: "Failed to connect to public tunnel api endpoint.",
        details: {
          configured_port: 8000,
          local_health: "offline",
          public_tunnel_url: "",
          public_health_status: "offline",
          public_error: "Gateway connection refused"
        }
      });
      setActiveTunnelUrl("");
      setWebhookUrl("");
    } finally {
      setPublicTunnelLoading(false);
    }
  }

  async function handleRestartTunnel() {
    setWebhookLoading(true);
    setPublicTunnelLoading(true);
    setWebhookSaveStatus({ status: "saving", message: "Stopping existing tunnel and spawning a new one..." });
    // Clear stale status before check (Requirement 2)
    setPublicTunnelStatus({ status: "checking", message: "Restarting tunnel...", details: null });
    try {
      const res = await fetch(`${API_BASE}/whatsapp/restart-tunnel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      const data = await res.json();
      if (res.ok && data.status === "success") {
        setWebhookSaveStatus({ status: "success", message: "Tunnel restarted successfully!" });
        
        // Sync states (Requirement 2)
        const newUrl = data.public_url || "";
        setActiveTunnelUrl(newUrl);
        if (newUrl) {
          setWebhookUrl(newUrl.replace(/\/$/, '') + '/webhooks/whatsapp');
        } else {
          setWebhookUrl("");
        }
        
        if (data.diagnostics) {
          setPublicTunnelStatus({
            status: "success",
            message: "Tunnel started and verified.",
            details: {
              status: "success",
              configured_port: 8000,
              local_health: "healthy",
              public_tunnel_url: newUrl,
              public_health_status: "healthy",
              diagnostics: data.diagnostics
            }
          });
        }
        setTimeout(() => setWebhookSaveStatus({ status: "", message: "" }), 3000);
      } else {
        setWebhookSaveStatus({ status: "error", message: data.detail || "Failed to restart tunnel." });
        setPublicTunnelStatus({
          status: "error",
          message: data.detail || "Failed to restart tunnel.",
          details: null
        });
        setActiveTunnelUrl("");
        setWebhookUrl("");
      }
    } catch (err) {
      console.error(err);
      setWebhookSaveStatus({ status: "error", message: "Network error restarting tunnel." });
      setPublicTunnelStatus({
        status: "error",
        message: "Connection failed during tunnel restart.",
        details: null
      });
      setActiveTunnelUrl("");
      setWebhookUrl("");
    } finally {
      setWebhookLoading(false);
      setPublicTunnelLoading(false);
    }
  }

  async function handleRefreshSilent() {
    try {
      await fetch(`${API_BASE}/youtube/comments/sync`, { method: "POST" });
    } catch (err) {
      console.warn("Silent comments sync failed:", err);
    }
    await fetchComments();
    await fetchVideos();
  }

  useEffect(() => {
    fetchVideos();
    fetchComments();
    checkSettings();
    checkWhatsAppStatus();
    fetchWebhookConfig();

    // Silent background sync and state refresh every 20 seconds
    const syncInterval = setInterval(() => {
      handleRefreshSilent();
    }, 20000);

    // Fast local UI status polling every 10 seconds
    const pollInterval = setInterval(() => {
      checkWhatsAppStatus();
      fetchWebhookConfig();
    }, 10000);

    return () => {
      clearInterval(syncInterval);
      clearInterval(pollInterval);
    };
  }, []);

  async function handleInsertWhatsAppLink(commentId: string) {
    try {
      const res = await fetch(`${API_BASE}/youtube/comments/${commentId}/whatsapp-link`);
      const data = await res.json();
      if (res.ok && data.whatsapp_link) {
        const cmt = comments.find(c => c.comment_id === commentId);
        const currentReply = editableReplies[commentId] ?? cmt?.reply?.suggested_reply ?? "";
        const space = currentReply.endsWith(" ") || currentReply === "" ? "" : " ";
        const newReply = `${currentReply}${space}Let's discuss on WhatsApp: ${data.whatsapp_link}`;
        setEditableReplies(prev => ({ ...prev, [commentId]: newReply }));
      } else {
        setStatusMsg("Failed to generate WhatsApp link.");
        setTimeout(() => setStatusMsg(""), 3000);
      }
    } catch (err) {
      console.error(err);
      setStatusMsg("Failed to generate WhatsApp link.");
      setTimeout(() => setStatusMsg(""), 3000);
    }
  }

  async function handleSimulate(e: React.FormEvent) {
    e.preventDefault();
    setSimLoading(true);
    setSimStatus("Processing new comment through agents...");
    try {
      const res = await fetch(`${API_BASE}/youtube/comments/inject`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_id: simVideo,
          username: simUsername,
          comment_text: simComment
        })
      });
      const data = await res.json();
      if (res.ok && data.status === "success") {
        setSimStatus("Comment processed successfully!");
        setSimComment("");
        // Reload list
        fetchComments();
      } else {
        setSimStatus("Injection failed.");
      }
    } catch (err) {
      setSimStatus("Error contacting backend.");
    } finally {
      setSimLoading(false);
      setTimeout(() => setSimStatus(""), 4000);
    }
  }

  // Retry action for failed replies
  async function handleRetry(commentId: string, replyText: string) {
    if (!replyText || !replyText.trim()) return;
    setActionLoading(prev => ({ ...prev, [commentId]: true }));
    setStatusMsg("Retrying comment reply publication...");
    try {
      const res = await fetch(`${API_BASE}/youtube/comments/${commentId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reply_text: replyText })
      });
      if (res.ok) {
        setStatusMsg("Reply published successfully on retry!");
        setComments(prev => prev.map(c => {
          if (c.comment_id === commentId) {
            return {
              ...c,
              status: "replied",
              reply: {
                ...(c.reply || {}),
                status: "published",
                actual_reply: replyText,
                published_at: new Date().toISOString(),
                failure_reason: null
              }
            };
          }
          return c;
        }));
      } else {
        const errorData = await res.json();
        alert(`Retry failed: ${errorData.detail || "Server error"}`);
      }
    } catch (err) {
      console.error(err);
      alert("Network error retrying comment reply.");
    } finally {
      setActionLoading(prev => ({ ...prev, [commentId]: false }));
      setTimeout(() => setStatusMsg(""), 3000);
    }
  }

  // Inline Approval Queue Actions
  async function handleApprove(commentId: string) {
    const cmt = comments.find(c => c.comment_id === commentId);
    const replyText = editableReplies[commentId] ?? cmt?.reply?.suggested_reply;
    if (!replyText || !replyText.trim()) return;

    setActionLoading(prev => ({ ...prev, [commentId]: true }));
    setStatusMsg("Publishing reply to YouTube comment...");
    try {
      const res = await fetch(`${API_BASE}/youtube/comments/${commentId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reply_text: replyText })
      });
      if (res.ok) {
        setStatusMsg("Reply published successfully!");
        // Update local React state inline
        setComments(prev => prev.map(c => {
          if (c.comment_id === commentId) {
            return {
              ...c,
              status: "replied",
              reply: {
                ...(c.reply || {}),
                status: "published",
                actual_reply: replyText,
                published_at: new Date().toISOString()
              }
            };
          }
          return c;
        }));
      } else {
        let errorDetail = "Failed to publish reply.";
        try {
          const errData = await res.json();
          if (errData && errData.detail) {
            errorDetail = `Error: ${errData.detail}`;
          }
        } catch (_) {}
        setStatusMsg(errorDetail);
      }
    } catch (err) {
      console.error(err);
      setStatusMsg("Connection error.");
    } finally {
      setActionLoading(prev => ({ ...prev, [commentId]: false }));
      setTimeout(() => setStatusMsg(""), 5000); // give more time to read errors
    }
  }

  async function handleReject(commentId: string) {
    setActionLoading(prev => ({ ...prev, [commentId]: true }));
    setStatusMsg("Dismissing suggested reply...");
    try {
      const res = await fetch(`${API_BASE}/youtube/comments/${commentId}/reject`, {
        method: "POST"
      });
      if (res.ok) {
        setStatusMsg("Suggestion dismissed.");
        // Update local React state inline
        setComments(prev => prev.map(c => {
          if (c.comment_id === commentId) {
            return {
              ...c,
              status: "rejected",
              reply: c.reply ? { ...c.reply, status: "rejected" } : null
            };
          }
          return c;
        }));
      } else {
        setStatusMsg("Failed to dismiss suggestion.");
      }
    } catch (err) {
      console.error(err);
      setStatusMsg("Connection error.");
    } finally {
      setActionLoading(prev => ({ ...prev, [commentId]: false }));
      setTimeout(() => setStatusMsg(""), 3000);
    }
  }

  async function handleRegenerate(commentId: string) {
    setActionLoading(prev => ({ ...prev, [commentId]: true }));
    setStatusMsg("Regenerating reply using LLM...");
    try {
      const res = await fetch(`${API_BASE}/youtube/comments/${commentId}/regenerate`, {
        method: "POST"
      });
      const data = await res.json();
      if (res.ok && data.suggested_reply) {
        setStatusMsg("Reply draft updated!");
        setEditableReplies(prev => ({ ...prev, [commentId]: data.suggested_reply }));
        // Update local React state inline
        setComments(prev => prev.map(c => {
          if (c.comment_id === commentId) {
            return {
              ...c,
              reply: {
                ...(c.reply || {}),
                suggested_reply: data.suggested_reply,
                status: "draft"
              }
            };
          }
          return c;
        }));
      } else {
        setStatusMsg("Failed to regenerate reply.");
      }
    } catch (err) {
      console.error(err);
      setStatusMsg("Connection error.");
    } finally {
      setActionLoading(prev => ({ ...prev, [commentId]: false }));
      setTimeout(() => setStatusMsg(""), 3000);
    }
  }

  const filteredComments = comments.filter(c => {
    const matchesSearch = c.username.toLowerCase().includes(search.toLowerCase()) ||
                          c.text.toLowerCase().includes(search.toLowerCase());
    const matchesIntent = intentFilter === "ALL" || c.intent === intentFilter;
    
    // Hide comments that don't belong to any monitored video in the list
    const isMonitored = monitoredVideos.some(v => v.video_id === c.video_id);
    if (!isMonitored) return false;
    
    // Filter by selected video dropdown (if not set to ALL)
    const matchesVideo = selectedVideo === "ALL" || c.video_id === selectedVideo;

    // Filter by status tab
    const matchesStatus = statusTab === "ALL" || c.status === statusTab;
    
    return matchesSearch && matchesIntent && matchesVideo && matchesStatus;
  });

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            Comment Inbox & Approvals
          </h1>
          <p className="text-slate-400 mt-2">
            Social conversation stream and AI response approval workspace. Qualify and interact in real-time.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          {/* WhatsApp status badge */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 flex items-center gap-3">
            <span className="text-xs font-semibold text-slate-300">WhatsApp Funnel</span>
            {whatsappStatus === "connected" ? (
              <span className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                Active
              </span>
            ) : whatsappStatus === "connecting" ? (
              <span className="text-xs font-bold text-indigo-400 flex items-center gap-1.5 animate-pulse">
                <span className="w-2 h-2 rounded-full bg-indigo-500" />
                Connecting
              </span>
            ) : (
              <span className="text-xs font-bold text-slate-500 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-slate-600" />
                Offline
              </span>
            )}
          </div>

          {/* Auto reply toggle */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 flex flex-col sm:flex-row items-start sm:items-center gap-3">
            <div className="flex items-center gap-3">
              <span className="text-xs font-semibold text-slate-300">AUTO_REPLY Mode</span>
              <button onClick={toggleAutoReply} className="focus:outline-none">
                {autoReply ? (
                  <ToggleRight className="w-8 h-8 text-emerald-400" />
                ) : (
                  <ToggleLeft className="w-8 h-8 text-slate-500" />
                )}
              </button>
            </div>
            
            {autoReply && (
              <div className="flex items-center gap-2 border-t sm:border-t-0 border-slate-800/80 pt-2 sm:pt-0 sm:pl-3 sm:border-l sm:border-l-slate-800">
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Min Confidence:</span>
                <input
                  type="range"
                  min="0.1"
                  max="1.0"
                  step="0.05"
                  value={confidenceThreshold}
                  onChange={(e) => handleThresholdChange(parseFloat(e.target.value))}
                  className="w-20 accent-indigo-500 cursor-pointer h-1 bg-slate-800 rounded-lg appearance-none"
                />
                <span className="text-[10px] font-bold text-indigo-400 font-mono">{(confidenceThreshold * 100).toFixed(0)}%</span>
              </div>
            )}
          </div>

          <div className="flex flex-col items-end gap-1">
            <button
              onClick={handleRefresh}
              disabled={loading}
              className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700/60 text-slate-300 font-bold px-5 py-3 rounded-xl transition"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              Refresh Comments
            </button>
            {lastSynced && (
              <span className="text-[10px] text-slate-500 font-medium mr-1 mt-0.5">
                Last Synced: {lastSynced}
              </span>
            )}
          </div>
        </div>
      </div>

      {statusMsg && (
        <div className="bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 px-4 py-3 rounded-xl text-xs font-semibold flex items-center gap-2 animate-pulse">
          <RefreshCw className="w-4 h-4 animate-spin" />
          {statusMsg}
        </div>
      )}

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 px-4 py-3 rounded-xl text-xs font-semibold flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Tabs Row */}
      <div className="flex border-b border-slate-800 gap-6">
        {[
          { id: "ALL", label: "All Comments" },
          { id: "pending_approval", label: "Pending Approvals" },
          { id: "replied", label: "Replied" },
          { id: "rejected", label: "Rejected/Spam" }
        ].map((tab) => {
          const isActive = statusTab === tab.id;
          const count = comments.filter(c => {
            const matchesTab = tab.id === "ALL" || c.status === tab.id;
            const isMonitored = monitoredVideos.some(v => v.video_id === c.video_id);
            return matchesTab && isMonitored;
          }).length;

          return (
            <button
              key={tab.id}
              onClick={() => setStatusTab(tab.id)}
              className={`pb-3 text-sm font-semibold transition relative flex items-center gap-2 ${
                isActive ? "text-indigo-400" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {tab.label}
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                isActive ? "bg-indigo-500/20 text-indigo-300" : "bg-slate-800 text-slate-500"
              }`}>
                {count}
              </span>
              {isActive && (
                <div className="absolute bottom-0 left-0 w-full h-0.5 bg-indigo-500 rounded-t" />
              )}
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Comments Stream */}
        <div className="lg:col-span-2 space-y-6">
          <div className="glass-panel rounded-2xl p-6">
            
            {/* Filters */}
            <div className="flex flex-col sm:flex-row justify-between gap-4 mb-6">
              <div className="relative w-full sm:w-72">
                <Search className="absolute left-3.5 top-3.5 w-4 h-4 text-slate-500" />
                <input
                  type="text"
                  placeholder="Search comments..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-3 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-sm"
                />
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <Filter className="w-4 h-4 text-slate-400" />
                <select
                  value={selectedVideo}
                  onChange={(e) => setSelectedVideo(e.target.value)}
                  className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-300 focus:outline-none focus:border-indigo-500 text-sm max-w-xs"
                >
                  <option value="ALL">All Monitored Videos</option>
                  {monitoredVideos.map(v => (
                    <option key={v.video_id} value={v.video_id}>
                      {v.title || v.video_id}
                    </option>
                  ))}
                </select>

                <select
                  value={intentFilter}
                  onChange={(e) => setIntentFilter(e.target.value)}
                  className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-300 focus:outline-none focus:border-indigo-500 text-sm"
                >
                  <option value="ALL">All Intents</option>
                  <option value="HIGH_INTENT">High Intent</option>
                  <option value="MEDIUM_INTENT">Medium Intent</option>
                  <option value="LOW_INTENT">Low Intent</option>
                  <option value="SPAM">Spam</option>
                </select>
              </div>
            </div>

            {/* Inbox stream */}
            {loading && comments.length === 0 ? (
              <div className="text-center py-12">
                <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin mx-auto mb-3" />
                <p className="text-sm text-slate-400">Loading conversation stream...</p>
              </div>
            ) : filteredComments.length === 0 ? (
              <div className="text-center py-12 text-slate-400">
                <MessageSquare className="w-12 h-12 text-slate-600 mx-auto mb-3" />
                <p className="text-sm font-bold text-slate-300">No Comments Found</p>
                <p className="text-xs text-slate-500 mt-1">Run comment polling or inject a mock comment to test the system.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredComments.map((cmt) => (
                  <div key={cmt.id} className="p-5 rounded-xl bg-slate-900/40 border border-slate-800/80 space-y-4 hover:border-slate-700/50 transition">
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="font-bold text-sm text-slate-200">@{cmt.username}</span>
                        <span className="text-[10px] text-slate-500 ml-2">
                          {new Date(cmt.timestamp || cmt.created_at).toLocaleString()}
                        </span>
                      </div>
                      
                      <div className="flex gap-2">
                        <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase border ${
                          cmt.intent === "HIGH_INTENT"
                            ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                            : cmt.intent === "MEDIUM_INTENT"
                            ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                            : cmt.intent === "LOW_INTENT"
                            ? "bg-slate-800 text-slate-400 border-slate-700/60"
                            : "bg-red-500/10 text-red-500 border-red-500/20"
                        }`}>
                          {cmt.intent.replace("_", " ")}
                        </span>
                        
                        <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase border ${
                          cmt.status === "replied"
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                            : cmt.status === "pending_approval"
                            ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                            : cmt.status === "failed"
                            ? "bg-rose-500/10 text-rose-400 border-rose-500/20 animate-pulse"
                            : "bg-slate-900 border border-slate-800 text-slate-500"
                        }`}>
                          {cmt.status === "pending_approval" ? "Waiting Approval" : cmt.status === "replied" ? "Reply Posted" : cmt.status}
                        </span>
                      </div>
                    </div>

                    <p className="text-slate-300 text-sm leading-relaxed">"{cmt.text}"</p>

                    {/* Status Workflow Timeline */}
                    <div className="flex flex-wrap items-center gap-y-2 gap-x-6 pt-3 pb-1 text-[11px] text-slate-400 border-t border-slate-800/40">
                      <div className="flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                        <span className="font-semibold text-slate-400">Detected:</span>
                        <span className="text-slate-500 font-mono">
                          {new Date(cmt.timestamp || cmt.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      
                      <div className="flex items-center gap-1.5">
                        <span className={`w-1.5 h-1.5 rounded-full ${cmt.reply ? "bg-indigo-550" : "bg-slate-800"}`} />
                        <span className="font-semibold text-slate-400">AI Reply:</span>
                        <span className={cmt.reply ? "text-indigo-400 font-medium" : "text-slate-500"}>
                          {cmt.reply ? "Generated" : "Waiting"}
                        </span>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          cmt.status === "replied" ? "bg-emerald-500" :
                          cmt.status === "failed" ? "bg-rose-500 animate-pulse" :
                          cmt.status === "pending_approval" ? "bg-amber-500" : "bg-slate-800"
                        }`} />
                        <span className="font-semibold text-slate-400">Status:</span>
                        <span className={`font-bold uppercase text-[10px] ${
                          cmt.status === "replied" ? "text-emerald-400" :
                          cmt.status === "failed" ? "text-rose-400" :
                          cmt.status === "pending_approval" ? "text-amber-400" : "text-slate-500"
                        }`}>
                          {cmt.status === "replied" ? "Reply Posted" :
                           cmt.status === "failed" ? "Failed" :
                           cmt.status === "pending_approval" ? "Waiting Approval" : cmt.status}
                        </span>
                        {cmt.reply?.published_at && (
                          <span className="text-[10px] text-slate-500 font-mono">
                            ({new Date(cmt.reply.published_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Failed status view */}
                    {cmt.status === "failed" && (
                      <div className="bg-rose-950/15 border border-rose-900/30 rounded-xl p-4 text-xs space-y-3 border-l-4 border-l-rose-500/80">
                        <div className="flex items-center gap-1.5 text-rose-455 font-bold uppercase text-[9px] tracking-wider">
                          <AlertCircle className="w-3.5 h-3.5" />
                          Reply Posting Failed
                        </div>
                        {cmt.reply?.failure_reason && (
                          <p className="text-slate-355 font-mono bg-slate-950/50 p-3 rounded-lg border border-slate-900 leading-normal">
                            {cmt.reply.failure_reason}
                          </p>
                        )}
                        <div className="flex items-center gap-3">
                          <button
                            onClick={() => handleRetry(cmt.comment_id, cmt.reply?.suggested_reply || "")}
                            disabled={actionLoading[cmt.comment_id]}
                            className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-3 py-1.5 rounded-lg transition text-[10px]"
                          >
                            Retry Posting
                          </button>
                          <button
                            onClick={() => handleReject(cmt.comment_id)}
                            disabled={actionLoading[cmt.comment_id]}
                            className="text-slate-400 hover:text-slate-350 text-[10px] font-medium transition"
                          >
                            Dismiss
                          </button>
                        </div>
                      </div>
                    )}
                    
                    {/* Inline Approvals queue box */}
                    {cmt.status === "pending_approval" && (
                      <div className="space-y-4 pt-3 border-t border-slate-800/80">
                        <div className="space-y-2">
                          <div className="flex justify-between items-center mb-2">
                            <label className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider block">Suggested Reply Draft</label>
                            <button
                              onClick={() => handleInsertWhatsAppLink(cmt.comment_id)}
                              type="button"
                              className="text-[10px] text-indigo-300 hover:text-indigo-200 font-semibold bg-indigo-500/10 border border-indigo-500/10 hover:border-indigo-500/20 px-2 py-0.5 rounded transition"
                            >
                              + Attach WhatsApp Link
                            </button>
                          </div>
                          <textarea
                            value={editableReplies[cmt.comment_id] ?? cmt.reply?.suggested_reply ?? ""}
                            onChange={(e) => setEditableReplies(prev => ({ ...prev, [cmt.comment_id]: e.target.value }))}
                            rows={3}
                            disabled={actionLoading[cmt.comment_id]}
                            className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-200 text-sm leading-relaxed focus:outline-none focus:border-indigo-500"
                          />
                        </div>
                        <div className="grid grid-cols-3 gap-3">
                          <button
                            onClick={() => handleApprove(cmt.comment_id)}
                            disabled={actionLoading[cmt.comment_id]}
                            className="flex items-center justify-center gap-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold py-2.5 rounded-xl shadow-lg shadow-emerald-500/10 transition text-xs"
                          >
                            <Check className="w-4 h-4" />
                            Approve & Send
                          </button>
                          <button
                            onClick={() => handleRegenerate(cmt.comment_id)}
                            disabled={actionLoading[cmt.comment_id]}
                            className="flex items-center justify-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-slate-700/80 font-bold py-2.5 rounded-xl transition text-xs"
                          >
                            <RefreshCw className={`w-3.5 h-3.5 ${actionLoading[cmt.comment_id] ? "animate-spin" : ""}`} />
                            Regenerate
                          </button>
                          <button
                            onClick={() => handleReject(cmt.comment_id)}
                            disabled={actionLoading[cmt.comment_id]}
                            className="flex items-center justify-center gap-1.5 bg-slate-900 border border-slate-800 text-slate-400 hover:text-rose-400 font-bold py-2.5 rounded-xl hover:border-slate-700/60 transition text-xs"
                          >
                            <X className="w-3.5 h-3.5" />
                            Reject & Dismiss
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Published Reply bubble */}
                    {cmt.status === "replied" && cmt.reply && (cmt.reply.actual_reply || cmt.reply.suggested_reply) && (
                      <div className="bg-slate-950/60 border border-slate-900 rounded-xl p-4 text-xs space-y-1.5 border-l-4 border-l-emerald-500">
                        <div className="flex items-center gap-1.5 text-emerald-400 font-bold uppercase text-[9px]">
                          <CheckSquare className="w-3.5 h-3.5" />
                          Published Reply
                        </div>
                        <p className="text-slate-300 italic">"{cmt.reply.actual_reply || cmt.reply.suggested_reply}"</p>
                        {cmt.reply.published_at && (
                          <span className="text-[9px] text-slate-500 block">
                            Sent at: {new Date(cmt.reply.published_at).toLocaleString()}
                          </span>
                        )}
                      </div>
                    )}

                    {/* Rejected Reply banner */}
                    {cmt.status === "rejected" && (
                      <div className="bg-slate-950/40 border border-slate-900 rounded-xl p-4 text-xs space-y-1.5 border-l-4 border-l-rose-500/50">
                        <div className="flex items-center gap-1.5 text-rose-400/80 font-bold uppercase text-[9px]">
                          <X className="w-3.5 h-3.5" />
                          Suggestion Rejected / Dismissed
                        </div>
                      </div>
                    )}

                    {/* Attached Reply Link Card (Requirement 4) */}
                    <div className="bg-slate-950/40 border border-slate-800 rounded-xl p-4 text-xs space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider">
                          Attached Reply Link (WhatsApp Funnel)
                        </span>
                        {!cmt.reply_link && (
                          <span className="text-[9px] text-slate-500 italic">No link stored</span>
                        )}
                      </div>
                      
                      {cmt.reply_link ? (
                        <div className="font-mono bg-black/40 p-2.5 rounded-lg border border-slate-900 break-all text-slate-300">
                          {cmt.reply_link}
                        </div>
                      ) : (
                        <div className="text-slate-500 italic py-1 pl-1">
                          No redirect link generated yet. Click regenerate below to create one.
                        </div>
                      )}
                      
                      <div className="flex flex-wrap gap-2 pt-1">
                        {cmt.reply_link && (
                          <>
                            <button
                              onClick={() => {
                                navigator.clipboard.writeText(cmt.reply_link);
                                setStatusMsg("Link copied to clipboard!");
                                setTimeout(() => setStatusMsg(""), 3000);
                              }}
                              type="button"
                              className="px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 font-bold rounded-lg transition text-[11px]"
                            >
                              Copy Link
                            </button>
                            <a
                              href={cmt.reply_link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 font-bold rounded-lg transition text-[11px] text-center"
                            >
                              Open Link
                            </a>
                          </>
                        )}
                        <button
                          onClick={async () => {
                            setActionLoading(prev => ({ ...prev, [cmt.comment_id]: true }));
                            setStatusMsg("Regenerating reply redirect link...");
                            try {
                              const res = await fetch(`${API_BASE}/youtube/comments/${cmt.comment_id}/regenerate-link`, {
                                method: "POST"
                              });
                              const data = await res.json();
                              if (res.ok && data.reply_link) {
                                setComments(prev => prev.map(c => c.comment_id === cmt.comment_id ? { ...c, reply_link: data.reply_link } : c));
                                setStatusMsg("Reply link regenerated successfully!");
                              } else {
                                setStatusMsg(data.detail || "Failed to regenerate link.");
                              }
                            } catch (err) {
                              setStatusMsg("Network error regenerating link.");
                            } finally {
                              setActionLoading(prev => ({ ...prev, [cmt.comment_id]: false }));
                              setTimeout(() => setStatusMsg(""), 3000);
                            }
                          }}
                          disabled={actionLoading[cmt.comment_id]}
                          type="button"
                          className="px-3 py-2 bg-indigo-900/30 hover:bg-indigo-900/50 border border-indigo-500/20 text-indigo-400 font-bold rounded-lg transition text-[11px]"
                        >
                          Regenerate Link
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* WhatsApp Status Compact Widget */}
        <div className="glass-panel rounded-2xl p-6 h-max space-y-5">
          <h3 className="text-lg font-bold text-white border-b border-slate-800 pb-3 flex items-center gap-2">
            <Activity className="w-5 h-5 text-indigo-400" />
            System Status Widget
          </h3>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between items-center py-2 border-b border-slate-850">
              <span className="text-slate-400 font-medium">WhatsApp Connected</span>
              <span className={`font-bold px-2.5 py-0.5 rounded text-[10px] uppercase tracking-wider ${
                whatsappStatus === "connected" 
                  ? "bg-emerald-500/10 text-emerald-450 border border-emerald-500/20" 
                  : "bg-rose-500/10 text-rose-450 border border-rose-500/20"
              }`}>
                {whatsappStatus === "connected" ? "Yes" : "No"}
              </span>
            </div>

            <div className="flex justify-between items-center py-2 border-b border-slate-850">
              <span className="text-slate-400 font-medium">Webhook Status</span>
              <span className={`font-bold px-2.5 py-0.5 rounded text-[10px] uppercase tracking-wider ${
                webhookConfig?.is_synchronized 
                  ? "bg-emerald-500/10 text-emerald-455 border border-emerald-500/20" 
                  : "bg-amber-500/10 text-amber-455 border border-amber-500/20"
              }`}>
                {webhookConfig?.is_synchronized ? "Synced" : "Modified"}
              </span>
            </div>

            <div className="flex justify-between items-center py-2 border-b border-slate-850">
              <span className="text-slate-400 font-medium">Tunnel Status</span>
              <span className={`font-bold px-2.5 py-0.5 rounded text-[10px] uppercase tracking-wider ${
                activeTunnelUrl 
                  ? "bg-emerald-500/10 text-emerald-450 border border-emerald-500/20" 
                  : "bg-rose-500/10 text-rose-450 border border-rose-500/20"
              }`}>
                {activeTunnelUrl ? "Active" : "Offline"}
              </span>
            </div>

            <div className="flex justify-between items-center py-2 border-b border-slate-850">
              <span className="text-slate-400 font-medium">Auto Reply Status</span>
              <span className={`font-bold px-2.5 py-0.5 rounded text-[10px] uppercase tracking-wider ${
                autoReply 
                  ? "bg-indigo-500/15 text-indigo-400 border border-indigo-500/20" 
                  : "bg-slate-850 text-slate-500 border border-slate-800"
              }`}>
                {autoReply ? "Enabled" : "Disabled"}
              </span>
            </div>

            <div className="flex justify-between items-center py-2 border-b border-slate-850">
              <span className="text-slate-400 font-medium">Active Campaign</span>
              <span className="font-bold text-slate-200">
                {monitoredVideos.length > 0 ? monitoredVideos[0].title : "Nursery Greenery Campaign"}
              </span>
            </div>

            {webhookConfig && (
              <div className="pt-3 space-y-2">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Active Webhook URL</span>
                <div className="bg-slate-950 px-3.5 py-2.5 rounded-xl border border-slate-850 font-mono text-[10px] text-slate-350 break-all select-all leading-normal">
                  {webhookConfig.stored_webhook_url || webhookConfig.suggested_webhook_url}
                </div>
              </div>
            )}
          </div>

          <div className="pt-2">
            <a
              href="/whatsapp-settings"
              className="w-full flex items-center justify-center gap-2 bg-indigo-650 hover:bg-indigo-600 text-white font-bold py-3 rounded-xl transition text-xs text-center shadow-lg shadow-indigo-600/10"
            >
              Configure Integration & Webhooks
            </a>
          </div>
        </div>

        {/* Auto-Reply Video Settings Widget */}
        <div className="glass-panel rounded-2xl p-6 h-max space-y-6">
          <h3 className="text-lg font-bold text-white border-b border-slate-800 pb-3 flex items-center gap-2">
            <CheckSquare className="w-5 h-5 text-indigo-400" />
            Auto-Reply Video Settings
          </h3>

          <p className="text-xs text-slate-400 leading-relaxed">
            Select which videos will automatically reply to customer comments using LLM-generated responses.
          </p>

          <div className="relative">
            <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search videos..."
              value={videoSearch}
              onChange={(e) => setVideoSearch(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-xs"
            />
          </div>

          <div className="space-y-3 max-h-60 overflow-y-auto pr-1 scrollbar-thin">
            {monitoredVideos.filter(v => v.title.toLowerCase().includes(videoSearch.toLowerCase())).length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-4">No matching videos found.</p>
            ) : (
              monitoredVideos
                .filter(v => v.title.toLowerCase().includes(videoSearch.toLowerCase()))
                .map((video) => {
                  const isAutoReplyOn = video.auto_reply !== false; // Default to true if not explicitly false
                  return (
                    <div key={video.video_id} className="flex justify-between items-center bg-slate-900/50 hover:bg-slate-900 border border-slate-800/80 rounded-xl p-3 transition gap-3">
                      <div className="min-w-0">
                        <p className="text-xs font-bold text-slate-200 truncate" title={video.title}>
                          {video.title}
                        </p>
                        <p className="text-[9px] text-slate-500 font-mono mt-0.5 truncate">
                          ID: {video.video_id}
                        </p>
                      </div>

                      <button
                        onClick={() => handleToggleVideoAutoReply(video.video_id, isAutoReplyOn)}
                        className="focus:outline-none flex-shrink-0"
                        title={isAutoReplyOn ? "Disable Auto-Reply" : "Enable Auto-Reply"}
                      >
                        {isAutoReplyOn ? (
                          <ToggleRight className="w-7 h-7 text-emerald-400" />
                        ) : (
                          <ToggleLeft className="w-7 h-7 text-slate-500" />
                        )}
                      </button>
                    </div>
                  );
                })
            )}
          </div>
        </div>

        {/* Comment Simulator Widget */}
        <div className="glass-panel rounded-2xl p-6 h-max space-y-6">
          <h3 className="text-lg font-bold text-white border-b border-slate-800 pb-3 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-indigo-400" />
            Comment Simulator
          </h3>

          <form onSubmit={handleSimulate} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Video Target</label>
              <select
                value={simVideo}
                onChange={(e) => setSimVideo(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-200 focus:outline-none focus:border-indigo-500 text-sm"
              >
                {monitoredVideos.length === 0 ? (
                  <option value="">No videos being monitored</option>
                ) : (
                  monitoredVideos.map(v => (
                    <option key={v.video_id} value={v.video_id}>
                      {v.title} ({v.video_id})
                    </option>
                  ))
                )}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Simulated Handle</label>
              <input
                type="text"
                value={simUsername}
                onChange={(e) => setSimUsername(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-sm"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Comment Text</label>
              <textarea
                value={simComment}
                onChange={(e) => setSimComment(e.target.value)}
                rows={3}
                placeholder="Type query to classify..."
                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-sm leading-relaxed"
                required
              />
            </div>

            <button
              type="submit"
              disabled={simLoading}
              className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3.5 rounded-xl transition shadow-lg shadow-indigo-600/10"
            >
              <Send className="w-4 h-4" />
              Inject Comment
            </button>
          </form>

          {simStatus && (
            <div className="text-center text-xs font-semibold text-indigo-400 bg-indigo-500/10 py-3 rounded-xl border border-indigo-500/10 animate-pulse">
              {simStatus}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
