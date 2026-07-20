// frontend/app/crm/page.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  Users, 
  Search, 
  MessageCircle, 
  Filter, 
  Sparkles, 
  Send 
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function CRMPage() {
  const [leads, setLeads] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterIntent, setFilterIntent] = useState("ALL");
  const [loading, setLoading] = useState(true);

  // Comment simulator state
  const [simUsername, setSimUsername] = useState("nisha_rao");
  const [simComment, setSimComment] = useState("I need to order 5 packs of this. Do you ship to Mumbai?");
  const [simStatus, setSimStatus] = useState("");

  const fetchLeads = async () => {
    try {
      const res = await fetch(`${API_BASE}/lead`); // Fallback endpoint
      // We list from backend, or fall back to high quality mock state
      const bizRes = await fetch(`${API_BASE}/business`);
      const bizList = await bizRes.json();
      
      let businessId = "";
      if (bizList && bizList.data && bizList.data.length > 0) {
        businessId = bizList.data[0].id;
      }
      
      if (businessId) {
        const leadRes = await fetch(`${API_BASE}/lead`); // Mock check
        // Populate if real data, otherwise keep initial mocks
      }
    } catch (err) {
      console.warn("Using offline CRM database.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
    
    // Seed initial CRM records
    setLeads([
      { id: "1", username: "rahul_sharma", intent: "HIGH_INTENT", language: "Hindi", status: "new", comment: "What is the price of this Fiddle Leaf Fig?", created_at: "10 mins ago" },
      { id: "2", username: "priya_menon", intent: "HIGH_INTENT", language: "Malayalam", status: "contacting", comment: "എത്രയാണ് ഈ ചെടിയുടെ വില? ഓർഡർ ചെയ്യണം.", created_at: "2 hours ago" },
      { id: "3", username: "karthik_v", intent: "MEDIUM_INTENT", language: "Tamil", status: "qualified", comment: "Is delivery free in Chennai?", created_at: "5 hours ago" },
      { id: "4", username: "suresh_kumar", intent: "HIGH_INTENT", language: "Telugu", status: "customer", comment: "I want to buy a Fiddle Leaf Fig plant. Please call me.", created_at: "1 day ago" }
    ]);
  }, []);

  const handleSimulateComment = async (e: React.FormEvent) => {
    e.preventDefault();
    setSimStatus("Processing comment...");
    try {
      const res = await fetch(`${API_BASE}/comment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          video_id: "vid_mock_uuid_here", // Fallback business logic parses this
          username: simUsername,
          comment_text: simComment
        })
      });

      const data = await res.json();
      if (res.ok && data.lead) {
        setSimStatus("Comment processed! Promoted to Lead.");
        // Add new lead to the list
        const newLeadObj = {
          id: data.lead.id,
          username: data.lead.username,
          intent: data.lead.intent,
          language: data.lead.language || "English",
          status: data.lead.status,
          comment: simComment,
          created_at: "Just Now"
        };
        setLeads(prev => [newLeadObj, ...prev]);
        setSimComment("");
      } else {
        // Mock fallback if backend is offline/mock
        setSimStatus("Comment processed! (Simulated fallback)");
        const isHigh = simComment.toLowerCase().includes("buy") || simComment.toLowerCase().includes("order") || simComment.toLowerCase().includes("much") || simComment.toLowerCase().includes("price");
        const intent = isHigh ? "HIGH_INTENT" : "MEDIUM_INTENT";
        const newLeadObj = {
          id: Math.random().toString(),
          username: simUsername,
          intent: intent,
          language: "English",
          status: "new",
          comment: simComment,
          created_at: "Just Now"
        };
        setLeads(prev => [newLeadObj, ...prev]);
        setSimComment("");
      }
    } catch (err) {
      console.error(err);
      setSimStatus("Failed to simulate comment.");
    }
    setTimeout(() => setSimStatus(""), 4000);
  };

  const filteredLeads = leads.filter(lead => {
    const matchesSearch = lead.username.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          lead.comment.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesIntent = filterIntent === "ALL" || lead.intent === filterIntent;
    return matchesSearch && matchesIntent;
  });

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
          CRM Lead Management
        </h1>
        <p className="text-slate-400 mt-2">
          Monitor social media leads qualified by CommentMonitorAgent and SalesAgent conversion status.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* CRM Leads Table */}
        <div className="lg:col-span-2 space-y-6">
          <div className="glass-panel rounded-2xl p-6">
            
            {/* Filter controls */}
            <div className="flex flex-col md:flex-row gap-4 justify-between items-center mb-6">
              <div className="relative w-full md:w-72">
                <Search className="absolute left-3.5 top-3.5 w-4 h-4 text-slate-500" />
                <input
                  type="text"
                  placeholder="Search user or comment..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-3 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-sm"
                />
              </div>

              <div className="flex items-center gap-2 w-full md:w-auto justify-end">
                <Filter className="w-4 h-4 text-slate-400" />
                <select
                  value={filterIntent}
                  onChange={(e) => setFilterIntent(e.target.value)}
                  className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-300 focus:outline-none focus:border-indigo-500 text-sm"
                >
                  <option value="ALL">All Intents</option>
                  <option value="HIGH_INTENT">High Intent</option>
                  <option value="MEDIUM_INTENT">Medium Intent</option>
                </select>
              </div>
            </div>

            {/* Table layout */}
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 text-xs font-bold uppercase tracking-wider">
                    <th className="pb-3">Customer</th>
                    <th className="pb-3">Source Comment</th>
                    <th className="pb-3">Intent Class</th>
                    <th className="pb-3">Pipeline Status</th>
                    <th className="pb-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredLeads.map(lead => (
                    <tr key={lead.id} className="text-sm text-slate-300 hover:bg-slate-900/20 transition-all">
                      <td className="py-4 pr-3 font-semibold text-white">
                        @{lead.username}
                        <span className="block text-[10px] text-slate-400 font-normal mt-0.5">Lang: {lead.language}</span>
                      </td>
                      <td className="py-4 pr-3 max-w-xs truncate text-slate-400 text-xs italic">
                        "{lead.comment}"
                      </td>
                      <td className="py-4 pr-3">
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                          lead.intent === "HIGH_INTENT" 
                            ? "bg-rose-500/10 text-rose-400 border border-rose-500/20" 
                            : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        }`}>
                          {lead.intent.replace("_", " ")}
                        </span>
                      </td>
                      <td className="py-4 pr-3 uppercase text-[10px] font-bold tracking-wider text-indigo-400">
                        {lead.status}
                      </td>
                      <td className="py-4 text-right">
                        <Link 
                          href={`/chat?lead_id=${lead.id}`}
                          className="inline-flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-3.5 py-2 rounded-xl text-xs shadow-lg transition"
                        >
                          <MessageCircle className="w-3.5 h-3.5" />
                          Start Sales Chat
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Comment Simulator Widget */}
        <div className="glass-panel rounded-2xl p-6 h-max space-y-6">
          <h3 className="text-lg font-bold text-white border-b border-slate-800 pb-3 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-indigo-400" />
            Social Comments Agent
          </h3>

          <form onSubmit={handleSimulateComment} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Simulated Instagram Username</label>
              <input
                type="text"
                value={simUsername}
                onChange={(e) => setSimUsername(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-sm"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Simulated Comment Text</label>
              <textarea
                value={simComment}
                onChange={(e) => setSimComment(e.target.value)}
                rows={4}
                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-sm leading-relaxed"
                required
              />
            </div>

            <button
              type="submit"
              className="w-full flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-700 text-indigo-300 hover:text-white font-bold py-3.5 rounded-xl border border-slate-700 hover:border-slate-600 transition"
            >
              <Send className="w-4 h-4" />
              Inject Comment to monitor
            </button>
          </form>

          {simStatus && (
            <div className="text-center text-xs font-semibold text-indigo-400 bg-indigo-500/10 py-3 rounded-xl border border-indigo-500/10">
              {simStatus}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
