// frontend/app/page.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  Users, 
  Video, 
  TrendingUp, 
  DollarSign, 
  ArrowRight, 
  PlusCircle, 
  CheckCircle, 
  Clock 
} from "lucide-react";

const API_BASE = "http://localhost:8000";

export default function Dashboard() {
  const [stats, setStats] = useState({
    total_leads: 8,
    total_conversions: 3,
    videos_generated: 4,
    avg_engagement_rate: 6.8,
    conversion_rate: 37.5
  });
  
  const [recentLeads, setRecentLeads] = useState<any[]>([]);
  const [recentVideos, setRecentVideos] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        // Fetch businesses first
        const bizRes = await fetch(`${API_BASE}/business`);
        // We look up for existing records, otherwise fallback to defaults
        const bizList = await bizRes.json();
        
        let businessId = "";
        if (bizList && bizList.data && bizList.data.length > 0) {
          businessId = bizList.data[0].id;
        }

        if (businessId) {
          const analyticsRes = await fetch(`${API_BASE}/analytics?business_id=${businessId}`);
          const analyticsData = await analyticsRes.json();
          if (analyticsData && analyticsData.summary) {
            setStats(analyticsData.summary);
          }
        }
      } catch (err) {
        console.warn("Could not load real-time analytics. Using simulated metrics.", err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();

    // Populate mock feed data for rich dashboard demonstration
    setRecentLeads([
      { id: "1", username: "rahul_sharma", intent: "HIGH_INTENT", language: "Hindi", status: "new", created_at: "Just Now" },
      { id: "2", username: "priya_menon", intent: "HIGH_INTENT", language: "Malayalam", status: "contacting", created_at: "2 hours ago" },
      { id: "3", username: "karthik_v", intent: "MEDIUM_INTENT", language: "Tamil", status: "qualified", created_at: "5 hours ago" },
      { id: "4", username: "suresh_kumar", intent: "HIGH_INTENT", language: "Telugu", status: "customer", created_at: "1 day ago" }
    ]);

    setRecentVideos([
      { id: "1", name: "Coconut Oil Campaign (Hindi)", lang: "Hindi", approval: "approved", views: 240 },
      { id: "2", name: "Handmade Saree Promo (Tamil)", lang: "Tamil", approval: "pending", views: 0 },
      { id: "3", name: "Organic Soap Clip (Malayalam)", lang: "Malayalam", approval: "approved", views: 180 },
      { id: "4", name: "Spices Intro Reel (Telugu)", lang: "Telugu", approval: "revision_requested", views: 50 }
    ]);
  }, []);

  const cardStats = [
    { name: "Total Leads", value: stats.total_leads, icon: Users, color: "text-blue-400", bg: "bg-blue-500/10" },
    { name: "Sales Conversions", value: stats.total_conversions, icon: DollarSign, color: "text-emerald-400", bg: "bg-emerald-500/10" },
    { name: "Videos Created", value: stats.videos_generated, icon: Video, color: "text-indigo-400", bg: "bg-indigo-500/10" },
    { name: "Engagement Rate", value: `${stats.avg_engagement_rate}%`, icon: TrendingUp, color: "text-purple-400", bg: "bg-purple-500/10" },
  ];

  return (
    <div className="space-y-8">
      {/* Header bar */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            VyaparAI Dashboard
          </h1>
          <p className="text-slate-400 mt-2">
            Automating SEO keyword research, localization, and automated sales loops for your products.
          </p>
        </div>
        
        <Link href="/upload" className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-5 py-3 rounded-xl shadow-lg shadow-indigo-600/20 transition-all duration-300 transform hover:-translate-y-0.5">
          <PlusCircle className="w-5 h-5" />
          Create New Campaign
        </Link>
      </div>

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

      {/* Dynamic Activity Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Recent CRM Leads */}
        <div className="glass-panel rounded-2xl p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Users className="w-5 h-5 text-indigo-400" />
              Hot Leads Queue
            </h2>
            <Link href="/crm" className="text-indigo-400 hover:text-indigo-300 text-xs font-semibold flex items-center gap-1">
              View CRM
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          
          <div className="space-y-4">
            {recentLeads.map((lead) => (
              <div key={lead.id} className="flex justify-between items-center p-4 rounded-xl bg-slate-900/50 border border-slate-800/80 hover:border-slate-700/60 transition-all">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center font-bold text-indigo-300 uppercase">
                    {lead.username.slice(0, 2)}
                  </div>
                  <div>
                    <h4 className="font-semibold text-sm text-slate-200">@{lead.username}</h4>
                    <p className="text-xs text-slate-400">Lang: {lead.language} • {lead.created_at}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase ${
                    lead.intent === "HIGH_INTENT" 
                      ? "bg-rose-500/10 text-rose-400 border border-rose-500/20" 
                      : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                  }`}>
                    {lead.intent.replace("_", " ")}
                  </span>
                  
                  <Link href={`/chat?lead_id=${lead.id}`} className="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3 py-1.5 rounded-lg border border-slate-700 transition">
                    Chat
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Video Drafts approval */}
        <div className="glass-panel rounded-2xl p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Video className="w-5 h-5 text-indigo-400" />
              Marketing Assets
            </h2>
            <Link href="/preview" className="text-indigo-400 hover:text-indigo-300 text-xs font-semibold flex items-center gap-1">
              View Clips
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="space-y-4">
            {recentVideos.map((video) => (
              <div key={video.id} className="flex justify-between items-center p-4 rounded-xl bg-slate-900/50 border border-slate-800/80 hover:border-slate-700/60 transition-all">
                <div>
                  <h4 className="font-semibold text-sm text-slate-200">{video.name}</h4>
                  <p className="text-xs text-slate-400">Lang: {video.lang} {video.views > 0 && `• ${video.views} views`}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`flex items-center gap-1 text-[10px] font-bold px-2.5 py-1 rounded-full uppercase ${
                    video.approval === "approved"
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      : video.approval === "pending"
                      ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                      : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                  }`}>
                    {video.approval === "approved" ? (
                      <CheckCircle className="w-3 h-3" />
                    ) : (
                      <Clock className="w-3 h-3" />
                    )}
                    {video.approval.replace("_", " ")}
                  </span>
                  
                  <Link href="/approval" className="text-indigo-400 hover:text-indigo-300 text-xs font-semibold px-2 py-1">
                    Review
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}
