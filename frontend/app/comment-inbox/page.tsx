// frontend/app/comment-inbox/page.tsx
"use client";

import { useEffect, useState } from "react";
import { 
  MessageSquare, Search, Filter, Sparkles, Send, RefreshCw, 
  ToggleLeft, ToggleRight, CheckSquare, Check, X, AlertCircle, Calendar 
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
  const [whatsappStatus, setWhatsappStatus] = useState<string>("disconnected");
  const [error, setError] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState("");
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
        body: JSON.stringify({ auto_reply: nextVal })
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
  }

  useEffect(() => {
    fetchVideos();
    fetchComments();
    checkSettings();
    checkWhatsAppStatus();

    // Poll WhatsApp status every 10 seconds to keep dashboard state aligned
    const interval = setInterval(() => {
      checkWhatsAppStatus();
    }, 10000);

    return () => clearInterval(interval);
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
          <div className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 flex items-center gap-3">
            <span className="text-xs font-semibold text-slate-300">AUTO_REPLY Mode</span>
            <button onClick={toggleAutoReply} className="focus:outline-none">
              {autoReply ? (
                <ToggleRight className="w-8 h-8 text-emerald-400" />
              ) : (
                <ToggleLeft className="w-8 h-8 text-slate-500" />
              )}
            </button>
          </div>

          <button
            onClick={handleRefresh}
            disabled={loading}
            className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700/60 text-slate-300 font-bold px-5 py-3 rounded-xl transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
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
                            : "bg-slate-900 border border-slate-800 text-slate-500"
                        }`}>
                          {cmt.status}
                        </span>
                      </div>
                    </div>

                    <p className="text-slate-300 text-sm leading-relaxed">"{cmt.text}"</p>
                    
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
                  </div>
                ))}
              </div>
            )}
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
