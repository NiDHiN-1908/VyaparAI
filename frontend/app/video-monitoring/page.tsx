// frontend/app/video-monitoring/page.tsx
"use client";

import { useEffect, useState } from "react";
import { Play, Eye, RefreshCw, Search, Calendar, Film, Video, ExternalLink, ToggleLeft, ToggleRight, AlertCircle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function VideoMonitoring() {
  const [loading, setLoading] = useState(true);
  const [videos, setVideos] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function fetchVideos() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/youtube/videos`);
      const data = await res.json();
      if (data.status === "success" && data.data) {
        setVideos(data.data);
      } else {
        setVideos([]);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to connect to backend server.");
    } finally {
      setLoading(false);
    }
  }

  async function handleToggleVideoAutoReply(videoId: string, currentAutoReply: boolean) {
    const nextVal = !currentAutoReply;
    // Optimistic UI update
    setVideos(prev => prev.map(v => v.video_id === videoId ? { ...v, auto_reply: nextVal } : v));
    try {
      await fetch(`${API_BASE}/youtube/videos/${videoId}/auto-reply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ auto_reply: nextVal })
      });
    } catch (err) {
      console.error(err);
      // Revert on error
      setVideos(prev => prev.map(v => v.video_id === videoId ? { ...v, auto_reply: currentAutoReply } : v));
    }
  }

  async function handleToggleVideoMonitoring(videoId: string, isCurrentlyMonitored: boolean) {
    const nextStatus = isCurrentlyMonitored ? "unmonitored" : "monitored";
    // Optimistic UI update
    setVideos(prev => prev.map(v => v.video_id === videoId ? { ...v, status: nextStatus } : v));
    try {
      await fetch(`${API_BASE}/youtube/videos/${videoId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus })
      });
    } catch (err) {
      console.error(err);
      // Revert on error
      setVideos(prev => prev.map(v => v.video_id === videoId ? { ...v, status: isCurrentlyMonitored ? "monitored" : "unmonitored" } : v));
    }
  }

  useEffect(() => {
    fetchVideos();
  }, []);

  const filteredVideos = videos.filter(video => 
    video.title.toLowerCase().includes(search.toLowerCase()) ||
    video.video_id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            Monitored Videos
          </h1>
          <p className="text-slate-400 mt-2">
            Videos uploaded by your connected channel currently indexed and monitored by VideoMonitoringAgent.
          </p>
        </div>

        <button
          onClick={fetchVideos}
          disabled={loading}
          className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700/60 text-slate-300 font-bold px-5 py-3 rounded-xl transition"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Sync Videos
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <div className="glass-panel rounded-2xl p-6 relative overflow-hidden">
          <p className="text-sm font-medium text-slate-400">Actively Monitored</p>
          <h3 className="text-3xl font-bold mt-2 text-white">
            {videos.filter(v => v.status === "monitored").length} / {videos.length} Videos
          </h3>
          <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500/20 to-transparent" />
        </div>
        <div className="glass-panel rounded-2xl p-6 relative overflow-hidden">
          <p className="text-sm font-medium text-slate-400">Active Monitoring Channels</p>
          <h3 className="text-3xl font-bold mt-2 text-emerald-400">1 Channel</h3>
          <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-emerald-500/20 to-transparent" />
        </div>
        <div className="glass-panel rounded-2xl p-6 relative overflow-hidden">
          <p className="text-sm font-medium text-slate-400">Scanning Frequency</p>
          <h3 className="text-3xl font-bold mt-2 text-indigo-400">Every 5 min</h3>
          <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500/20 to-transparent" />
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative max-w-md">
        <Search className="absolute left-3.5 top-3.5 w-4 h-4 text-slate-500" />
        <input
          type="text"
          placeholder="Search by video title or ID..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-3 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-sm"
        />
      </div>

      {loading ? (
        <div className="text-center py-12">
          <RefreshCw className="w-10 h-10 text-indigo-400 animate-spin mx-auto mb-4" />
          <p className="text-slate-400 text-sm">Syncing video index...</p>
        </div>
      ) : error ? (
        <div className="glass-panel rounded-2xl p-8 text-center text-slate-400 max-w-md mx-auto">
          <AlertCircle className="w-8 h-8 text-rose-500 mx-auto mb-2" />
          <p className="text-sm font-bold text-slate-300">Connection Offline</p>
          <p className="text-xs text-slate-500 mt-1">{error}</p>
        </div>
      ) : filteredVideos.length === 0 ? (
        <div className="glass-panel rounded-2xl p-12 text-center text-slate-400 max-w-md mx-auto">
          <Film className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <p className="text-sm font-bold text-slate-300">No Monitored Videos Found</p>
          <p className="text-xs text-slate-500 mt-1">Make sure you connect a channel first to fetch and monitor uploads.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filteredVideos.map((video) => (
            <div key={video.id} className="glass-panel rounded-2xl p-5 hover:border-slate-700/60 transition-all flex flex-col justify-between space-y-4">
              <div className="flex gap-4">
                <div className="w-20 h-20 rounded-xl bg-slate-950/60 border border-slate-900 flex items-center justify-center text-rose-500 flex-shrink-0 relative overflow-hidden">
                  <Video className="w-8 h-8" />
                  <div className="absolute bottom-1 right-1 bg-slate-950/80 px-1 py-0.5 rounded text-[8px] text-slate-400 font-bold">HD</div>
                </div>
                
                <div className="space-y-1.5 min-w-0">
                  <h3 className="font-bold text-sm text-slate-200 truncate pr-4">{video.title}</h3>
                  <div className="flex items-center gap-1.5 text-xs text-slate-400">
                    <Calendar className="w-3.5 h-3.5" />
                    <span>{new Date(video.publish_date || video.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`inline-block text-[10px] font-bold px-2 py-0.5 rounded-full uppercase border ${
                      video.status === "monitored" 
                        ? "bg-indigo-500/10 text-indigo-400 border-indigo-500/15" 
                        : "bg-slate-800 text-slate-500 border-slate-700/60"
                    }`}>
                      {video.status || "monitored"}
                    </span>
                    <span className={`inline-block text-[10px] font-bold px-2 py-0.5 rounded-full uppercase border ${
                      video.auto_reply !== false 
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/15" 
                        : "bg-slate-800 text-slate-500 border-slate-700/60"
                    }`}>
                      {video.auto_reply !== false ? "Auto-Reply On" : "Auto-Reply Off"}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex justify-between items-center border-t border-slate-800/80 pt-4">
                <div className="flex items-center gap-4 flex-wrap">
                  <span className="text-[10px] text-slate-500 font-bold uppercase">ID: {video.video_id}</span>
                  
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => handleToggleVideoMonitoring(video.video_id, video.status === "monitored")}
                      className="focus:outline-none flex items-center gap-1.5"
                      title={video.status === "monitored" ? "Stop Monitoring" : "Start Monitoring"}
                    >
                      <span className="text-[10px] font-semibold text-slate-400">Monitor:</span>
                      {video.status === "monitored" ? (
                        <ToggleRight className="w-6 h-6 text-indigo-400" />
                      ) : (
                        <ToggleLeft className="w-6 h-6 text-slate-500" />
                      )}
                    </button>

                    <button
                      onClick={() => handleToggleVideoAutoReply(video.video_id, video.auto_reply !== false)}
                      className="focus:outline-none flex items-center gap-1.5"
                      title={video.auto_reply !== false ? "Disable Auto-Reply" : "Enable Auto-Reply"}
                    >
                      <span className="text-[10px] font-semibold text-slate-400">Auto-Reply:</span>
                      {video.auto_reply !== false ? (
                        <ToggleRight className="w-6 h-6 text-emerald-400" />
                      ) : (
                        <ToggleLeft className="w-6 h-6 text-slate-500" />
                      )}
                    </button>
                  </div>
                </div>
                <a
                  href={`https://www.youtube.com/watch?v=${video.video_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-rose-400 hover:text-rose-300 text-xs font-semibold"
                >
                  Watch Video
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
