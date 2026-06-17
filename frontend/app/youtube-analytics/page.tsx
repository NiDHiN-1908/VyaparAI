// frontend/app/youtube-analytics/page.tsx
"use client";

import { useEffect, useState } from "react";
import { BarChart3, Users, MessageSquare, Award, Percent, RefreshCw, AlertCircle, Video } from "lucide-react";

const API_BASE = "http://localhost:8000";

export default function YouTubeAnalytics() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<any>({
    comments_processed: 0,
    reply_rate: 0,
    lead_count: 0,
    conversion_rate: 0,
    top_videos: []
  });
  const [error, setError] = useState<string | null>(null);

  async function fetchAnalytics() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/youtube/analytics`);
      const data = await res.json();
      if (data.status === "success" && data.data) {
        setStats(data.data);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to fetch analytics from backend.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const cardStats = [
    { name: "Comments Processed", value: stats.comments_processed, icon: MessageSquare, color: "text-blue-400", bg: "bg-blue-500/10" },
    { name: "Auto Reply Rate", value: `${stats.reply_rate}%`, icon: Percent, color: "text-emerald-400", bg: "bg-emerald-500/10" },
    { name: "CRM Leads Created", value: stats.lead_count, icon: Users, color: "text-rose-400", bg: "bg-rose-500/10" },
    { name: "Lead Conversion Rate", value: `${stats.conversion_rate}%`, icon: Award, color: "text-indigo-400", bg: "bg-indigo-500/10" },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            YouTube Analytics
          </h1>
          <p className="text-slate-400 mt-2">
            Performance analytics tracking comments processed, intent detection accuracy, and qualified CRM leads.
          </p>
        </div>

        <button
          onClick={fetchAnalytics}
          disabled={loading}
          className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700/60 text-slate-300 font-bold px-5 py-3 rounded-xl transition"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Sync Analytics
        </button>
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 px-4 py-3.5 rounded-xl text-sm font-semibold flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      {/* Grid counters */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {cardStats.map((stat) => (
          <div key={stat.name} className="glass-panel glass-card-hover rounded-2xl p-6 relative overflow-hidden">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm font-medium text-slate-400">{stat.name}</p>
                <h3 className="text-3xl font-bold mt-2 text-white">{stat.value}</h3>
              </div>
              <div className={`p-4 rounded-xl ${stat.bg}`}>
                <stat.icon className={`w-6 h-6 ${stat.color}`} />
              </div>
            </div>
            <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500/20 to-transparent" />
          </div>
        ))}
      </div>

      {/* Main Analysis Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Top Videos by Lead Generation */}
        <div className="glass-panel rounded-2xl p-6 space-y-6">
          <h3 className="text-lg font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-4">
            <Video className="w-5 h-5 text-indigo-400" />
            Top Performing Videos
          </h3>

          {loading ? (
            <div className="text-center py-6">
              <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin mx-auto mb-2" />
              <p className="text-xs text-slate-400">Loading campaign stats...</p>
            </div>
          ) : !stats.top_videos || stats.top_videos.length === 0 ? (
            <p className="text-xs text-slate-500 italic text-center py-6">No top video data recorded yet.</p>
          ) : (
            <div className="space-y-4">
              {stats.top_videos.map((vid: any, idx: number) => (
                <div key={vid.video_id} className="flex justify-between items-center p-4 rounded-xl bg-slate-900/50 border border-slate-800/80 hover:border-slate-700/60 transition">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center font-bold text-indigo-400 text-xs">
                      #{idx + 1}
                    </div>
                    <div>
                      <h4 className="font-semibold text-sm text-slate-200">{vid.title}</h4>
                      <p className="text-xs text-slate-400">Video ID: {vid.video_id}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-slate-400 font-medium">{vid.comments} Comments</p>
                    <p className="text-xs text-rose-400 font-bold mt-0.5">{vid.leads} Leads</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* System Funnel Analytics */}
        <div className="glass-panel rounded-2xl p-6 space-y-6">
          <h3 className="text-lg font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-4">
            <BarChart3 className="w-5 h-5 text-indigo-400" />
            Social Conversion Funnel
          </h3>

          <div className="space-y-5 pt-2">
            {/* Processed comments */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Comments Processed</span>
                <span className="text-slate-200 font-bold">100%</span>
              </div>
              <div className="w-full bg-slate-950 rounded-full h-2">
                <div className="bg-blue-500 h-2 rounded-full" style={{ width: "100%" }} />
              </div>
            </div>

            {/* Qualified Leads */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Qualified Leads (HIGH_INTENT)</span>
                <span className="text-slate-200 font-bold">
                  {stats.comments_processed > 0 ? `${round((stats.lead_count / stats.comments_processed) * 100)}%` : "0%"}
                </span>
              </div>
              <div className="w-full bg-slate-950 rounded-full h-2">
                <div 
                  className="bg-rose-500 h-2 rounded-full transition-all duration-500" 
                  style={{ width: stats.comments_processed > 0 ? `${(stats.lead_count / stats.comments_processed) * 100}%` : "0%" }} 
                />
              </div>
            </div>

            {/* Sales Conversion */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-slate-400">Sales Conversion Rate</span>
                <span className="text-slate-200 font-bold">{stats.conversion_rate}%</span>
              </div>
              <div className="w-full bg-slate-950 rounded-full h-2">
                <div 
                  className="bg-indigo-500 h-2 rounded-full transition-all duration-500" 
                  style={{ width: `${stats.conversion_rate}%` }} 
                />
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

function round(val: number) {
  return Math.round(val * 10) / 10;
}
