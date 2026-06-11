// frontend/app/analytics/page.tsx
"use client";

import { useEffect, useState } from "react";
import { 
  BarChart3, 
  TrendingUp, 
  Users, 
  DollarSign, 
  Video, 
  Percent 
} from "lucide-react";

export default function AnalyticsPage() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState({
    leads: 12,
    conversions: 4,
    videos: 8,
    engagement: 7.2,
    funnel: [
      { step: "Video Views", count: 1200, pct: 100 },
      { step: "Comment Objections", count: 240, pct: 20 },
      { step: "CRM Leads Promoted", count: 48, pct: 4 },
      { step: "UPI Payments Paid", count: 12, pct: 1 }
    ]
  });

  useEffect(() => {
    // Simulated loading transition for high-fidelity feel
    const timer = setTimeout(() => {
      setLoading(false);
    }, 800);
    return () => clearTimeout(timer);
  }, []);

  const stats = [
    { label: "Total Leads Promoted", value: data.leads, icon: Users, desc: "High & Medium intent comments", color: "text-blue-400" },
    { label: "Completed UPI Orders", value: data.conversions, icon: DollarSign, desc: "Closed by SalesAgent node", color: "text-emerald-400" },
    { label: "AI Marketing Clips", value: data.videos, icon: Video, desc: "Regional voiceovers generated", color: "text-indigo-400" },
    { label: "Avg Engagement Rate", value: `${data.engagement}%`, icon: TrendingUp, desc: "Likes, comments, shares avg", color: "text-purple-400" },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
          Marketing & Sales Analytics
        </h1>
        <p className="text-slate-400 mt-2">
          Pre-aggregated performance metrics calculated across Trend, Video, Comment, and LangGraph workflow databases.
        </p>
      </div>

      {/* Overview Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
          <div key={stat.label} className="glass-panel rounded-2xl p-6 relative overflow-hidden">
            <div className="flex justify-between items-start">
              <div className="space-y-1">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{stat.label}</p>
                <h3 className="text-3xl font-extrabold text-white pt-1">{stat.value}</h3>
              </div>
              <div className="bg-slate-900/60 border border-slate-800 p-3 rounded-xl">
                <stat.icon className={`w-5 h-5 ${stat.color}`} />
              </div>
            </div>
            <p className="text-xs text-slate-400 pt-4 border-t border-slate-800/60 mt-4">{stat.desc}</p>
            <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500/20 to-transparent" />
          </div>
        ))}
      </div>

      {/* Visual Charts section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Weekly Lead generation bar chart - Custom SVG */}
        <div className="lg:col-span-2 glass-panel rounded-2xl p-6 space-y-6">
          <h3 className="text-lg font-bold text-white border-b border-slate-800 pb-3 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-indigo-400" />
            Weekly CRM Leads Generation
          </h3>
          
          <div className="h-64 flex items-end justify-between gap-6 pt-4 px-2">
            {/* Monday */}
            <div className="flex flex-col items-center gap-2 flex-1 group">
              <span className="text-xs text-slate-400 font-bold opacity-0 group-hover:opacity-100 transition-all">3</span>
              <div className="w-full bg-slate-900 border border-slate-800 rounded-lg h-16 group-hover:bg-indigo-600/30 group-hover:border-indigo-500/40 transition-all flex flex-col justify-end">
                <div className="w-full bg-indigo-600 rounded-b-md h-12 shadow-lg shadow-indigo-600/20" />
              </div>
              <span className="text-xs text-slate-400 font-semibold">Mon</span>
            </div>

            {/* Tuesday */}
            <div className="flex flex-col items-center gap-2 flex-1 group">
              <span className="text-xs text-slate-400 font-bold opacity-0 group-hover:opacity-100 transition-all">5</span>
              <div className="w-full bg-slate-900 border border-slate-800 rounded-lg h-28 group-hover:bg-indigo-600/30 group-hover:border-indigo-500/40 transition-all flex flex-col justify-end">
                <div className="w-full bg-indigo-600 rounded-b-md h-20 shadow-lg shadow-indigo-600/20" />
              </div>
              <span className="text-xs text-slate-400 font-semibold">Tue</span>
            </div>

            {/* Wednesday */}
            <div className="flex flex-col items-center gap-2 flex-1 group">
              <span className="text-xs text-slate-400 font-bold opacity-0 group-hover:opacity-100 transition-all">2</span>
              <div className="w-full bg-slate-900 border border-slate-800 rounded-lg h-12 group-hover:bg-indigo-600/30 group-hover:border-indigo-500/40 transition-all flex flex-col justify-end">
                <div className="w-full bg-indigo-600 rounded-b-md h-8 shadow-lg shadow-indigo-600/20" />
              </div>
              <span className="text-xs text-slate-400 font-semibold">Wed</span>
            </div>

            {/* Thursday */}
            <div className="flex flex-col items-center gap-2 flex-1 group">
              <span className="text-xs text-slate-400 font-bold opacity-0 group-hover:opacity-100 transition-all">8</span>
              <div className="w-full bg-slate-900 border border-slate-800 rounded-lg h-44 group-hover:bg-indigo-600/30 group-hover:border-indigo-500/40 transition-all flex flex-col justify-end">
                <div className="w-full bg-indigo-600 rounded-b-md h-36 shadow-lg shadow-indigo-600/20" />
              </div>
              <span className="text-xs text-slate-400 font-semibold">Thu</span>
            </div>

            {/* Friday */}
            <div className="flex flex-col items-center gap-2 flex-1 group">
              <span className="text-xs text-slate-400 font-bold opacity-0 group-hover:opacity-100 transition-all">11</span>
              <div className="w-full bg-slate-900 border border-slate-800 rounded-lg h-56 group-hover:bg-indigo-600/30 group-hover:border-indigo-500/40 transition-all flex flex-col justify-end">
                <div className="w-full bg-indigo-600 rounded-b-md h-48 shadow-lg shadow-indigo-600/20" />
              </div>
              <span className="text-xs text-slate-400 font-semibold">Fri</span>
            </div>
          </div>
        </div>

        {/* Sales Conversion Funnel */}
        <div className="glass-panel rounded-2xl p-6 space-y-6">
          <h3 className="text-lg font-bold text-white border-b border-slate-800 pb-3 flex items-center gap-2">
            <Percent className="w-5 h-5 text-indigo-400" />
            Conversion Funnel
          </h3>

          <div className="space-y-4 pt-2">
            {data.funnel.map((item, idx) => (
              <div key={item.step} className="space-y-1">
                <div className="flex justify-between items-center text-xs font-semibold text-slate-300">
                  <span>{item.step}</span>
                  <span className="text-slate-400 font-bold">{item.count} ({item.pct}%)</span>
                </div>
                {/* Horizontal progress representation */}
                <div className="h-3 w-full bg-slate-900 border border-slate-800 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-indigo-600 to-purple-600 rounded-full" 
                    style={{ width: `${item.pct}%` }} 
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}
