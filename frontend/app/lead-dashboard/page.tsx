// frontend/app/lead-dashboard/page.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Users, Search, RefreshCw, MessageSquare, ExternalLink, MessageCircle, AlertCircle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function LeadDashboard() {
  const [loading, setLoading] = useState(true);
  const [leads, setLeads] = useState<any[]>([]);
  const [contactPhone, setContactPhone] = useState("917306796590");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function fetchBusinessContact() {
    try {
      const res = await fetch(`${API_BASE}/business`);
      const data = await res.json();
      if (data.status === "success" && data.data && data.data.length > 0) {
        const rawPhone = data.data[0].contact || "";
        const cleaned = rawPhone.replace(/\D/g, "");
        if (cleaned.length === 10) {
          setContactPhone("91" + cleaned);
        } else if (cleaned) {
          setContactPhone(cleaned);
        }
      }
    } catch (err) {
      console.warn("Failed to fetch business contact details.");
    }
  }

  async function fetchLeads() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/youtube/leads`);
      const data = await res.json();
      if (data.status === "success" && data.data) {
        setLeads(data.data);
      } else {
        setLeads([]);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to fetch YouTube leads from backend.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchBusinessContact();
    fetchLeads();
  }, []);

  const filteredLeads = leads.filter(l => 
    l.username.toLowerCase().includes(search.toLowerCase()) ||
    (l.comment_text && l.comment_text.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            YouTube Leads
          </h1>
          <p className="text-slate-400 mt-2">
            Hot buyer leads qualified by LeadCreationAgent from high-intent YouTube comment interactions.
          </p>
        </div>

        <button
          onClick={fetchLeads}
          disabled={loading}
          className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700/60 text-slate-300 font-bold px-5 py-3 rounded-xl transition"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh Leads
        </button>
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 px-4 py-3.5 rounded-xl text-sm font-semibold flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <div className="glass-panel rounded-2xl p-6 relative overflow-hidden">
          <p className="text-sm font-medium text-slate-400">Total Leads Qualified</p>
          <h3 className="text-3xl font-bold mt-2 text-white">{leads.length}</h3>
          <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-rose-500/20 to-transparent" />
        </div>
        <div className="glass-panel rounded-2xl p-6 relative overflow-hidden">
          <p className="text-sm font-medium text-slate-400">Contact Rate</p>
          <h3 className="text-3xl font-bold mt-2 text-emerald-400">100%</h3>
          <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-emerald-500/20 to-transparent" />
        </div>
        <div className="glass-panel rounded-2xl p-6 relative overflow-hidden">
          <p className="text-sm font-medium text-slate-400">Status</p>
          <h3 className="text-3xl font-bold mt-2 text-indigo-400">Sync Active</h3>
          <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500/20 to-transparent" />
        </div>
      </div>

      {/* Search and Filters */}
      <div className="relative max-w-md">
        <Search className="absolute left-3.5 top-3.5 w-4 h-4 text-slate-500" />
        <input
          type="text"
          placeholder="Search leads..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-3 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-sm"
        />
      </div>

      {loading && leads.length === 0 ? (
        <div className="text-center py-12">
          <RefreshCw className="w-10 h-10 text-indigo-400 animate-spin mx-auto mb-4" />
          <p className="text-slate-400 text-sm">Syncing lead registry...</p>
        </div>
      ) : filteredLeads.length === 0 ? (
        <div className="glass-panel rounded-2xl p-12 text-center text-slate-400 max-w-md mx-auto">
          <Users className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <p className="text-sm font-bold text-slate-300">No YouTube Leads</p>
          <p className="text-xs text-slate-500 mt-1">High-intent comments will appear here automatically as leads.</p>
        </div>
      ) : (
        <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800/80">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 text-xs font-bold uppercase tracking-wider bg-slate-950/40">
                  <th className="p-4">Lead Info</th>
                  <th className="p-4">YouTube Query</th>
                  <th className="p-4">AI Reply Suggested</th>
                  <th className="p-4">Qualified Date</th>
                  <th className="p-4 text-right">Outreach</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40">
                {filteredLeads.map((l) => (
                  <tr key={l.id} className="text-sm text-slate-300 hover:bg-slate-900/10 transition">
                    <td className="p-4 font-semibold text-white">
                      @{l.username}
                      <span className="block text-[10px] font-bold text-rose-400 uppercase mt-0.5">{l.intent.replace("_", " ")}</span>
                    </td>
                    <td className="p-4 max-w-xs truncate text-slate-400 italic">
                      "{l.comment_text || "Checking price / Buy options"}"
                    </td>
                    <td className="p-4 max-w-xs truncate text-slate-400">
                      {l.reply || "CTA sent"}
                    </td>
                    <td className="p-4 text-slate-500 text-xs">
                      {new Date(l.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          href={`/live-chat?lead_id=${l.id}`}
                          className="inline-flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-3.5 py-2 rounded-xl text-xs shadow-lg transition"
                        >
                          <MessageSquare className="w-4 h-4" />
                          Live Chat
                        </Link>
                        <a
                          href={`https://wa.me/${contactPhone}?text=Hi%20@${l.username},%20we%20saw%20your%20comment%20on%20our%20video.%20How%20can%20we%20help%20you%20order?`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold px-3 py-2 rounded-xl text-xs border border-slate-700 transition"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                          External
                        </a>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
