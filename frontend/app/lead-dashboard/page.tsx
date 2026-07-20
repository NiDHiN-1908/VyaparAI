// frontend/app/lead-dashboard/page.tsx
"use client";

import { useEffect, useState } from "react";
import { 
  Users, 
  Award, 
  MessageSquare, 
  Search, 
  RefreshCw, 
  TrendingUp, 
  DollarSign, 
  PhoneCall, 
  Activity, 
  ArrowRight,
  Flame,
  Thermometer,
  CloudLightning,
  Workflow,
  AlertCircle,
  Clock,
  Sparkles,
  ShoppingBag,
  Share2
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LeadDashboard() {
  const [loading, setLoading] = useState(true);
  const [crmData, setCrmData] = useState<any>({
    summary: {
      total_leads: 0,
      contacted_leads: 0,
      contact_rate: 0.0,
      hot_leads: 0,
      warm_leads: 0,
      cold_leads: 0,
      youtube_to_lead_rate: 0.0,
      avg_messages_per_chat: 0.0,
      autopilot_chats: 0,
      revenue_attributed: 0.0
    },
    funnel: [],
    trends: [],
    sources: {},
    leads: [],
    activity: []
  });
  
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("ALL");
  const [pollingActive, setPollingActive] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function fetchCRMData() {
    try {
      const res = await fetch(`${API_BASE}/youtube/leads/dashboard`);
      const data = await res.json();
      if (res.ok && data.status === "success" && data.summary) {
        setCrmData(data);
        setError(null);
      } else {
        setError("Error loading CRM dashboard statistics.");
      }
    } catch (err) {
      console.error("Failed to load CRM data:", err);
      setError("Failed to communicate with the CRM API backend.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchCRMData();
    
    const interval = setInterval(() => {
      if (pollingActive) {
        fetchCRMData();
      }
    }, 15000);

    return () => clearInterval(interval);
  }, [pollingActive]);

  // Handle manual outreach trigger
  async function triggerManualOutreach(leadId: string) {
    try {
      const res = await fetch(`${API_BASE}/conversations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lead_id: leadId })
      });
      const result = await res.json();
      if (res.ok && result.status === "success") {
        alert("Outreach WhatsApp session generated successfully!");
        fetchCRMData();
      } else {
        alert("Outreach failed: " + (result.detail || "Server error"));
      }
    } catch (err) {
      console.error(err);
      alert("Network error starting outreach.");
    }
  }

  // Filter leads based on search query and category dropdown
  const filteredLeads = crmData.leads.filter((l: any) => {
    const nameStr = (l.username || l.name || "").toLowerCase();
    const phoneStr = (l.phone || "").toLowerCase();
    const matchesSearch = nameStr.includes(searchQuery.toLowerCase()) || phoneStr.includes(searchQuery.toLowerCase());
    const matchesCategory = categoryFilter === "ALL" || l.category.toUpperCase() === categoryFilter.toUpperCase();
    return matchesSearch && matchesCategory;
  });

  const kpis = [
    { label: "Qualified CRM Leads", value: crmData.summary.total_leads, icon: Users, color: "text-blue-400", bg: "bg-blue-500/10" },
    { label: "Outreach Contact Rate", value: `${crmData.summary.contact_rate}%`, icon: PhoneCall, color: "text-indigo-400", bg: "bg-indigo-500/10" },
    { label: "Autopilot AI Chats", value: crmData.summary.autopilot_chats, icon: Workflow, color: "text-purple-400", bg: "bg-purple-500/10" },
    { label: "Attributed Revenue", value: `Rs. ${crmData.summary.revenue_attributed.toLocaleString()}`, icon: DollarSign, color: "text-emerald-400", bg: "bg-emerald-500/10" },
  ];

  const maxTrendLeads = Math.max(...(crmData.trends || []).map((t: any) => t.leads || 0), 1);

  return (
    <div className="space-y-8 animate-fade-in pb-16">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl md:text-4xl font-black tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            Lead Management CRM Dashboard
          </h1>
          <p className="text-slate-400 text-sm mt-1.5 font-medium">
            Real customer lead pipeline, automated outreach statuses, intent analytics, and revenue attribution.
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
            onClick={fetchCRMData}
            disabled={loading}
            className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700/60 text-slate-300 font-bold px-4 py-2.5 rounded-xl transition text-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Sync CRM
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 px-4 py-3.5 rounded-xl text-sm font-semibold flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      {/* KPI Counters */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="glass-panel glass-card-hover rounded-2xl p-5 relative overflow-hidden">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">{kpi.label}</p>
                <h3 className="text-2xl font-black mt-1.5 text-white">{kpi.value}</h3>
              </div>
              <div className={`p-3 rounded-xl border border-slate-800/80 ${kpi.bg}`}>
                <kpi.icon className={`w-5 h-5 ${kpi.color}`} />
              </div>
            </div>
            <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500/20 to-transparent" />
          </div>
        ))}
      </div>

      {/* Lead Scoring, Funnel, & Sources Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Lead Category distribution */}
        <div className="glass-panel rounded-2xl p-6 space-y-5">
          <h3 className="text-base font-extrabold text-white border-b border-slate-800/80 pb-3 flex items-center gap-2">
            <Activity className="w-4 h-4 text-indigo-400" />
            Lead Intent Distribution
          </h3>

          <div className="space-y-3">
            {/* Hot Leads */}
            <div className="p-3.5 rounded-xl bg-rose-500/5 border border-rose-500/15 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-rose-500/10 text-rose-400 rounded-lg"><Flame className="w-4 h-4" /></div>
                <div>
                  <h4 className="font-bold text-slate-200 text-xs">Hot (High Buying Intent)</h4>
                  <p className="text-[10px] text-slate-500 font-mono">Score: 90</p>
                </div>
              </div>
              <span className="text-base font-black text-rose-400">{crmData.summary.hot_leads}</span>
            </div>

            {/* Warm Leads */}
            <div className="p-3.5 rounded-xl bg-amber-500/5 border border-amber-500/15 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-amber-500/10 text-amber-400 rounded-lg"><Thermometer className="w-4 h-4" /></div>
                <div>
                  <h4 className="font-bold text-slate-200 text-xs">Warm (Medium Intent)</h4>
                  <p className="text-[10px] text-slate-500 font-mono">Score: 65</p>
                </div>
              </div>
              <span className="text-base font-black text-amber-400">{crmData.summary.warm_leads}</span>
            </div>

            {/* Cold Leads */}
            <div className="p-3.5 rounded-xl bg-blue-500/5 border border-blue-500/15 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg"><CloudLightning className="w-4 h-4" /></div>
                <div>
                  <h4 className="font-bold text-slate-200 text-xs">Cold (General Inquiry)</h4>
                  <p className="text-[10px] text-slate-500 font-mono">Score: 25</p>
                </div>
              </div>
              <span className="text-base font-black text-blue-400">{crmData.summary.cold_leads}</span>
            </div>
          </div>
        </div>

        {/* Funnel Pipeline */}
        <div className="glass-panel rounded-2xl p-6 space-y-5 lg:col-span-2">
          <h3 className="text-base font-extrabold text-white border-b border-slate-800/80 pb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-indigo-400" />
            Empirical Lead Conversion Funnel
          </h3>

          <div className="space-y-3.5 pt-1">
            {crmData.funnel && crmData.funnel.map((item: any) => (
              <div key={item.step} className="space-y-1">
                <div className="flex justify-between items-center text-xs font-bold text-slate-300">
                  <span>{item.step}</span>
                  <span className="text-indigo-400 font-mono">{item.count} ({item.pct}%)</span>
                </div>
                <div className="h-3.5 w-full bg-slate-950 border border-slate-850 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-emerald-500 to-indigo-500 rounded-full transition-all duration-500" 
                    style={{ width: `${Math.max(item.pct, 4)}%` }} 
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* Weekly Trends & Lead Sources */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Weekly Acquisition Trends */}
        <div className="glass-panel rounded-2xl p-6 space-y-4 lg:col-span-2">
          <h3 className="text-base font-extrabold text-white border-b border-slate-800/80 pb-3 flex items-center gap-2">
            <Clock className="w-4 h-4 text-cyan-400" />
            Weekly Lead Acquisition Trend
          </h3>

          <div className="flex items-end justify-between gap-3 pt-4 h-36 border-b border-slate-800/60 pb-2">
            {(crmData.trends || []).map((t: any) => {
              const heightPct = Math.round(((t.leads || 0) / maxTrendLeads) * 100);
              return (
                <div key={t.day} className="flex-1 flex flex-col items-center gap-2 h-full justify-end group">
                  <span className="text-[10px] font-mono font-extrabold text-cyan-400 opacity-0 group-hover:opacity-100 transition">
                    {t.leads}
                  </span>
                  <div 
                    className="w-full max-w-[32px] bg-gradient-to-t from-indigo-600 to-cyan-400 rounded-t-lg transition-all duration-300 group-hover:brightness-125"
                    style={{ height: `${Math.max(heightPct, 8)}%` }}
                  />
                  <span className="text-[10px] font-bold text-slate-400 uppercase">{t.day}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Lead Sources Breakdown */}
        <div className="glass-panel rounded-2xl p-6 space-y-4">
          <h3 className="text-base font-extrabold text-white border-b border-slate-800/80 pb-3 flex items-center gap-2">
            <Share2 className="w-4 h-4 text-emerald-400" />
            Lead Acquisition Channels
          </h3>

          <div className="space-y-3 pt-1">
            {Object.entries(crmData.sources || {}).map(([source, count]: [string, any]) => (
              <div key={source} className="flex items-center justify-between p-3 rounded-xl bg-slate-950/60 border border-slate-850">
                <span className="text-xs font-bold text-slate-300">{source}</span>
                <span className="text-xs font-mono font-extrabold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  {count}
                </span>
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* Leads Table & CRM Outreaches */}
      <div className="glass-panel rounded-2xl p-6 space-y-6">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800/80 pb-5">
          <h3 className="text-base font-extrabold text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-indigo-400" />
            Live CRM Lead Roster ({filteredLeads.length})
          </h3>

          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            {/* Search Input */}
            <div className="relative flex-1 md:w-64">
              <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
              <input
                type="text"
                placeholder="Search by handle..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 placeholder-slate-500"
              />
            </div>

            {/* Category Filter */}
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-300 focus:outline-none focus:border-indigo-500 font-bold"
            >
              <option value="ALL">All Categories</option>
              <option value="HOT">Hot Only</option>
              <option value="WARM">Warm Only</option>
              <option value="COLD">Cold Only</option>
            </select>
          </div>
        </div>

        {/* Lead Rows Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 text-[10px] font-bold uppercase tracking-wider bg-slate-950/60">
                <th className="p-4">Customer Profile</th>
                <th className="p-4">Target Plant Product</th>
                <th className="p-4 text-center">Score</th>
                <th className="p-4 text-center">Intent Category</th>
                <th className="p-4 text-right">CRM Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40 text-slate-350 font-medium">
              {filteredLeads.length > 0 ? (
                filteredLeads.map((lead: any) => (
                  <tr key={lead.id} className="hover:bg-slate-900/40 transition">
                    <td className="p-4">
                      <div className="font-extrabold text-white">@{lead.username}</div>
                      <div className="text-[10px] font-mono text-slate-500 mt-0.5">{lead.id.slice(0, 8)}...</div>
                    </td>
                    <td className="p-4">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-bold text-[11px]">
                        <ShoppingBag className="w-3 h-3" />
                        {lead.interested_product || "Jasmine Plant"}
                      </span>
                    </td>
                    <td className="p-4 text-center font-extrabold font-mono text-indigo-400 text-sm">{lead.score}</td>
                    <td className="p-4 text-center">
                      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-extrabold border ${
                        lead.category === "Hot" 
                          ? "bg-rose-500/10 border-rose-500/25 text-rose-400" 
                          : lead.category === "Warm"
                          ? "bg-amber-500/10 border-amber-500/25 text-amber-400"
                          : "bg-blue-500/10 border-blue-500/25 text-blue-400"
                      }`}>
                        {lead.category === "Hot" && <Flame className="w-3 h-3" />}
                        {lead.category === "Warm" && <Thermometer className="w-3 h-3" />}
                        {lead.category === "Cold" && <CloudLightning className="w-3 h-3" />}
                        {lead.category}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => triggerManualOutreach(lead.id)}
                        className="inline-flex items-center gap-1.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold px-3.5 py-1.5 rounded-xl text-xs transition active:scale-95 shadow-md shadow-indigo-500/20"
                      >
                        Launch Outreach
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="text-center py-8 text-slate-500 italic">No qualified CRM leads found matching query.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
