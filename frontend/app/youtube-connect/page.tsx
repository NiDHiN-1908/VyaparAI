// frontend/app/youtube-connect/page.tsx
"use client";

import { useEffect, useState } from "react";
import { Youtube, Link2, ShieldCheck, HelpCircle, LogOut, RefreshCw, AlertCircle } from "lucide-react";

const API_BASE = "http://localhost:8000";

export default function YouTubeConnect() {
  const [loading, setLoading] = useState(true);
  const [channel, setChannel] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  async function checkStatus() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/youtube/status`);
      const data = await res.json();
      if (data.connected && data.channel) {
        setChannel(data.channel);
      } else {
        setChannel(null);
      }
    } catch (err) {
      console.error(err);
      setError("Failed to fetch connection status from VyaparAI backend.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    checkStatus();
    // Parse query params for redirect status
    const params = new URLSearchParams(window.location.search);
    if (params.get("status") === "success") {
      // Clear URL params
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (params.get("status") === "error") {
      setError(params.get("error") || "Authentication failed.");
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  async function handleMockConnect() {
    setActionLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/youtube/mock-connect`, {
        method: "POST",
      });
      const data = await res.json();
      if (res.ok && data.status === "success") {
        setChannel(data.data);
      } else {
        setError("Failed to connect mock channel.");
      }
    } catch (err) {
      setError("Server connection failed.");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleDisconnect() {
    setActionLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/youtube/disconnect`, {
        method: "POST",
      });
      if (res.ok) {
        setChannel(null);
      } else {
        setError("Failed to disconnect channel.");
      }
    } catch (err) {
      setError("Server connection failed.");
    } finally {
      setActionLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
          YouTube Integration
        </h1>
        <p className="text-slate-400 mt-2">
          Connect your brand's YouTube channel once to automate video polling, intent analysis, and intelligent comment replies.
        </p>
      </div>

      {error && (
        <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 px-4 py-3.5 rounded-xl text-sm font-semibold flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      {loading ? (
        <div className="glass-panel rounded-2xl p-12 flex flex-col items-center justify-center space-y-4">
          <RefreshCw className="w-10 h-10 text-indigo-400 animate-spin" />
          <p className="text-slate-400 text-sm">Checking channel authentication status...</p>
        </div>
      ) : channel ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Profile Card */}
          <div className="glass-panel rounded-2xl p-6 flex flex-col items-center text-center space-y-4 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 bg-rose-500/5 rounded-full blur-xl pointer-events-none" />
            <img
              src={channel.thumbnail || "https://images.unsplash.com/photo-1628157582853-a796fa650a6a?w=150&auto=format&fit=crop&q=80"}
              alt={channel.channel_name}
              className="w-24 h-24 rounded-full border-4 border-slate-800 shadow-xl shadow-rose-500/5"
            />
            <div>
              <h3 className="text-xl font-bold text-white flex items-center justify-center gap-1.5">
                {channel.channel_name}
                <ShieldCheck className="w-5 h-5 text-emerald-400 fill-emerald-500/10" />
              </h3>
              <p className="text-slate-400 text-xs mt-1">Channel ID: {channel.channel_id.slice(0, 15)}...</p>
            </div>
            
            <div className="w-full bg-slate-950/60 rounded-xl p-3 border border-slate-900 flex justify-around">
              <div>
                <p className="text-[10px] text-slate-500 font-bold uppercase">Subscribers</p>
                <p className="text-lg font-bold text-white mt-0.5">{channel.subscriber_count.toLocaleString()}</p>
              </div>
              <div className="border-r border-slate-800/80 my-1" />
              <div>
                <p className="text-[10px] text-slate-500 font-bold uppercase">Role Permissions</p>
                <p className="text-lg font-bold text-emerald-400 mt-0.5">Active</p>
              </div>
            </div>

            <button
              onClick={handleDisconnect}
              disabled={actionLoading}
              className="w-full flex items-center justify-center gap-2 bg-slate-900 border border-slate-800 hover:border-slate-700/60 hover:text-rose-400 text-slate-300 font-bold py-3.5 rounded-xl transition"
            >
              <LogOut className="w-4 h-4" />
              Disconnect Channel
            </button>
          </div>

          {/* Details Panel */}
          <div className="md:col-span-2 glass-panel rounded-2xl p-6 space-y-6">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-indigo-400" />
              Integration Permissions Summary
            </h3>
            
            <div className="space-y-4 text-sm text-slate-300">
              <div className="flex gap-3">
                <div className="mt-1 w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold text-white">OAuth Read & Write Scopes Authorized</h4>
                  <p className="text-xs text-slate-400 mt-0.5">Access tokens grant VyaparAI permissions to fetch recent videos and reply comments automatically.</p>
                </div>
              </div>
              
              <div className="flex gap-3">
                <div className="mt-1 w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold text-white">Continuous Background Polling Enabled</h4>
                  <p className="text-xs text-slate-400 mt-0.5">The VideoMonitoringAgent indexes your video uploads every 5 minutes and runs qualification analyses.</p>
                </div>
              </div>

              <div className="flex gap-3">
                <div className="mt-1 w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold text-white">Automatic Token Refresh Active</h4>
                  <p className="text-xs text-slate-400 mt-0.5">Authentication keys refresh automatically, guaranteeing uninterrupted monitoring services.</p>
                </div>
              </div>
            </div>

            <div className="bg-indigo-500/5 border border-indigo-500/10 rounded-xl p-4 flex gap-3">
              <HelpCircle className="w-6 h-6 text-indigo-400 flex-shrink-0" />
              <div className="text-xs text-slate-400 leading-relaxed">
                <span className="font-bold text-slate-300 block mb-1">Testing the pipeline offline?</span>
                Use the Comment Simulator in the Inbox or CRM menu to inject customer comments immediately and observe Agent reply generation in real-time.
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="glass-panel rounded-2xl p-8 max-w-2xl mx-auto flex flex-col items-center text-center space-y-6">
          <div className="w-16 h-16 rounded-full bg-rose-500/10 flex items-center justify-center text-rose-500">
            <Youtube className="w-8 h-8" />
          </div>

          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-white">Connect YouTube Channel</h2>
            <p className="text-slate-400 text-sm max-w-md">
              Link your channel once. Our agentic pipeline will continuously index comments, qualify buyers, and prepare replies.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full pt-4">
            <a
              href={`${API_BASE}/auth/youtube/login`}
              className="flex items-center justify-center gap-2 bg-rose-600 hover:bg-rose-500 text-white font-bold py-4 rounded-xl shadow-lg shadow-rose-600/15 transition transform hover:-translate-y-0.5"
            >
              <Youtube className="w-5 h-5" />
              Connect YouTube Channel
            </a>

            <button
              onClick={handleMockConnect}
              disabled={actionLoading}
              className="flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-slate-700 font-bold py-4 rounded-xl transition transform hover:-translate-y-0.5"
            >
              <Link2 className="w-4 h-4" />
              Simulate Connection (Sandbox)
            </button>
          </div>

          <p className="text-[10px] text-slate-500 leading-relaxed max-w-sm">
            Sandbox mode connects a simulated channel and seeds mock videos for instant verification without needing a Google developer account.
          </p>
        </div>
      )}
    </div>
  );
}
