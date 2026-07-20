// frontend/app/youtube-analytics/page.tsx
"use client";

import { useEffect, useState } from "react";
import { 
  BarChart3, 
  Users, 
  MessageSquare, 
  Award, 
  Percent, 
  RefreshCw, 
  AlertCircle, 
  Video, 
  Eye, 
  Clock, 
  ThumbsUp, 
  Share2, 
  TrendingUp, 
  ShieldCheck 
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function YouTubeAnalytics() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<any>({
    comments_processed: 0,
    reply_rate: 0,
    lead_count: 0,
    conversion_rate: 0,
    views: 0,
    likes: 0,
    watch_time: "0h",
    subscribers: 0,
    engagement_rate: 0.0,
    shares: 0,
    monitored_videos_count: 0,
    traffic_trends: [],
    audience_growth: [],
    top_videos: []
  });
  const [error, setError] = useState<string | null>(null);
  const [pollingActive, setPollingActive] = useState(true);

  async function fetchAnalytics() {
    try {
      const res = await fetch(`${API_BASE}/youtube/analytics`);
      const data = await res.json();
      if (res.ok && data.status === "success" && data.data) {
        setStats(data.data);
        setError(null);
      } else {
        setError("Failed to fetch analytics data from server.");
      }
    } catch (err) {
      console.error(err);
      setError("Failed to fetch analytics from backend.");
    } finally {
      setLoading(false);
    }
  }

  // Initial fetch and automatic polling interval
  useEffect(() => {
    fetchAnalytics();
    
    const interval = setInterval(() => {
      if (pollingActive) {
        fetchAnalytics();
      }
    }, 15000); // Poll every 15s

    return () => clearInterval(interval);
  }, [pollingActive]);

  const cards = [
    { name: "Channel Subscribers", value: stats.subscribers.toLocaleString(), icon: Users, color: "text-blue-400", bg: "bg-blue-500/10" },
    { name: "Video Views", value: stats.views.toLocaleString(), icon: Eye, color: "text-emerald-400", bg: "bg-emerald-500/10" },
    { name: "Watch Time", value: stats.watch_time, icon: Clock, color: "text-indigo-400", bg: "bg-indigo-500/10" },
    { name: "Likes Received", value: stats.likes.toLocaleString(), icon: ThumbsUp, color: "text-purple-400", bg: "bg-purple-500/10" },
    { name: "Engagement Rate", value: `${stats.engagement_rate}%`, icon: Percent, color: "text-yellow-400", bg: "bg-yellow-500/10" },
    { name: "Comments Processed", value: stats.comments_processed, icon: MessageSquare, color: "text-cyan-400", bg: "bg-cyan-500/10" },
    { name: "Auto Reply Rate", value: `${stats.reply_rate}%`, icon: Percent, color: "text-teal-400", bg: "bg-teal-500/10" },
    { name: "CRM Leads Promoted", value: stats.lead_count, icon: Award, color: "text-rose-400", bg: "bg-rose-500/10" },
  ];

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            YouTube Live Channel Analytics
          </h1>
          <p className="text-slate-400 mt-2">
            Live channel audit, campaign views, watch time, subscribers, and agent lead conversion rates.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setPollingActive(!pollingActive)}
            className={`text-xs px-3.5 py-2.5 rounded-xl border font-bold transition ${
              pollingActive 
                ? "bg-indigo-500/10 border-indigo-500/25 text-indigo-400" 
                : "bg-slate-900 border-slate-800 text-slate-500"
            }`}
          >
            {pollingActive ? "● Real-time Polling ON" : "Polling Paused"}
          </button>

          <button
            onClick={fetchAnalytics}
            disabled={loading}
            className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700/60 text-slate-300 font-bold px-5 py-3 rounded-xl transition text-sm"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Sync Analytics
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 px-4 py-3.5 rounded-xl text-sm font-semibold flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      {/* Stats Counters Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {cards.map((stat) => (
          <div key={stat.name} className="glass-panel glass-card-hover rounded-2xl p-6 relative overflow-hidden">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{stat.name}</p>
                <h3 className="text-2xl font-bold mt-2 text-white">{stat.value}</h3>
              </div>
              <div className={`p-3.5 rounded-xl border border-slate-800/80 ${stat.bg}`}>
                <stat.icon className={`w-5 h-5 ${stat.color}`} />
              </div>
            </div>
            <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500/10 to-transparent" />
          </div>
        ))}
      </div>

      {/* Interactive Charts section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Traffic Trends Chart */}
        <div className="glass-panel rounded-2xl p-6 space-y-6">
          <h3 className="text-lg font-bold text-white border-b border-slate-800 pb-3 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-indigo-400" />
            Traffic Trends (Views over the last 7 Days)
          </h3>
          
          <div className="h-48 flex items-end justify-between gap-4 pt-4 px-2">
            {stats.traffic_trends && stats.traffic_trends.map((item: any) => {
              const maxVal = Math.max(...stats.traffic_trends.map((t: any) => t.views), 1);
              const pct = (item.views / maxVal) * 100;
              return (
                <div key={item.day} className="flex flex-col items-center gap-2 flex-1 group">
                  <span className="text-[10px] text-indigo-400 font-bold opacity-0 group-hover:opacity-100 transition-all">{item.views.toLocaleString()}</span>
                  <div className="w-full bg-slate-950 border border-slate-800/50 rounded-lg h-36 flex flex-col justify-end overflow-hidden group-hover:border-indigo-500/40 transition">
                    <div 
                      className="w-full bg-indigo-600/90 rounded-b-md shadow-lg shadow-indigo-600/10 hover:bg-indigo-500 transition-all cursor-pointer" 
                      style={{ height: `${pct}%` }} 
                    />
                  </div>
                  <span className="text-xs text-slate-400 font-semibold">{item.day}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Audience Growth line simulation */}
        <div className="glass-panel rounded-2xl p-6 space-y-6">
          <h3 className="text-lg font-bold text-white border-b border-slate-800 pb-3 flex items-center gap-2">
            <Users className="w-5 h-5 text-indigo-400" />
            Audience Growth (Monthly Subscriber Trend)
          </h3>
          
          <div className="relative h-48 w-full pt-4">
            {/* Draw a custom SVG line chart */}
            {stats.audience_growth && stats.audience_growth.length > 0 && (
              <svg className="w-full h-36" viewBox="0 0 500 100" preserveAspectRatio="none">
                <defs>
                  <linearGradient id="subGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6366f1" stopOpacity="0.25" />
                    <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
                  </linearGradient>
                </defs>
                {/* Area under the path */}
                <path
                  d={`M 0 100 
                      L 0 ${100 - (stats.audience_growth[0].subscribers / stats.subscribers) * 80} 
                      L 100 ${100 - (stats.audience_growth[1].subscribers / stats.subscribers) * 80} 
                      L 200 ${100 - (stats.audience_growth[2].subscribers / stats.subscribers) * 80} 
                      L 300 ${100 - (stats.audience_growth[3].subscribers / stats.subscribers) * 80} 
                      L 400 ${100 - (stats.audience_growth[4].subscribers / stats.subscribers) * 80} 
                      L 500 ${100 - (stats.audience_growth[5].subscribers / stats.subscribers) * 80} 
                      L 500 100 Z`}
                  fill="url(#subGradient)"
                />
                {/* Trend line */}
                <path
                  d={`M 0 ${100 - (stats.audience_growth[0].subscribers / stats.subscribers) * 80} 
                      L 100 ${100 - (stats.audience_growth[1].subscribers / stats.subscribers) * 80} 
                      L 200 ${100 - (stats.audience_growth[2].subscribers / stats.subscribers) * 80} 
                      L 300 ${100 - (stats.audience_growth[3].subscribers / stats.subscribers) * 80} 
                      L 400 ${100 - (stats.audience_growth[4].subscribers / stats.subscribers) * 80} 
                      L 500 ${100 - (stats.audience_growth[5].subscribers / stats.subscribers) * 80}`}
                  fill="none"
                  stroke="#6366f1"
                  strokeWidth="3.5"
                  strokeLinecap="round"
                />
              </svg>
            )}
            <div className="flex justify-between text-xs text-slate-500 font-semibold px-2 mt-1">
              {stats.audience_growth && stats.audience_growth.map((item: any) => (
                <span key={item.month}>{item.month} ({item.subscribers.toLocaleString()})</span>
              ))}
            </div>
          </div>
        </div>

      </div>

      {/* Main Analysis Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Top Videos by Lead Generation */}
        <div className="glass-panel rounded-2xl p-6 space-y-6">
          <h3 className="text-lg font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-4">
            <Video className="w-5 h-5 text-indigo-400" />
            Top Performing Marketing Videos
          </h3>

          {loading ? (
            <div className="text-center py-6">
              <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin mx-auto mb-2" />
              <p className="text-xs text-slate-400">Loading channel video statistics...</p>
            </div>
          ) : !stats.top_videos || stats.top_videos.length === 0 ? (
            <p className="text-xs text-slate-500 italic text-center py-6">No top video data recorded yet.</p>
          ) : (
            <div className="space-y-4">
              {stats.top_videos.map((vid: any, idx: number) => (
                <div key={vid.video_id} className="flex justify-between items-center p-4 rounded-xl bg-slate-900/50 border border-slate-800/80 hover:border-slate-700/60 transition">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-slate-850 border border-slate-850 flex items-center justify-center font-bold text-indigo-450 text-xs">
                      #{idx + 1}
                    </div>
                    <div>
                      <h4 className="font-semibold text-sm text-slate-200">{vid.title}</h4>
                      <p className="text-xs text-slate-500">Video ID: {vid.video_id} • {vid.views.toLocaleString()} views</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-slate-400 font-semibold">{vid.comments} Comments</p>
                    <p className="text-xs text-rose-400 font-bold mt-0.5">{vid.leads} CRM Leads</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Monitored Campaign Video details */}
        <div className="glass-panel rounded-2xl p-6 space-y-6">
          <h3 className="text-lg font-bold text-white flex items-center gap-2 border-b border-slate-800 pb-4">
            <ShieldCheck className="w-5 h-5 text-indigo-400" />
            Monitoring Status
          </h3>

          <div className="p-5 rounded-2xl bg-slate-950 border border-slate-900/60 space-y-4">
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-400 font-medium">Videos Currently Monitored:</span>
              <span className="text-indigo-400 font-bold text-sm bg-indigo-500/10 px-2.5 py-1 rounded-lg border border-indigo-500/10">{stats.monitored_videos_count} / {stats.top_videos.length} videos</span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-400 font-medium">Real-time API Call Support:</span>
              <span className="text-emerald-400 font-bold text-xs bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-500/10">Active</span>
            </div>
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-400 font-medium">Lead Conversion Target:</span>
              <span className="text-rose-450 font-bold text-xs bg-rose-500/10 px-2.5 py-1 rounded-lg border border-rose-500/10">{stats.conversion_rate}%</span>
            </div>
          </div>

          <div className="text-xs leading-normal text-slate-400 bg-slate-900/40 p-4 rounded-xl border border-slate-800/40">
            <strong>System Note:</strong> The active monitor scans comment threads every 5 minutes in background. Turn auto-reply mode ON in the comments inbox page to publish responses automatically.
          </div>
        </div>

      </div>
    </div>
  );
}
