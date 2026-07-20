// frontend/components/BackendHealthGuard.tsx
"use client";

import React, { useState, useEffect } from "react";
import { 
  Activity, 
  Database, 
  Smartphone, 
  Network, 
  Cpu, 
  RefreshCw, 
  AlertTriangle, 
  CheckCircle2, 
  Loader2,
  Lock
} from "lucide-react";

interface HealthComponentStatus {
  status: string;
  mode?: string;
  provider?: string;
  public_url?: string;
  duration?: number;
  uptime_seconds?: number;
  ollama_model?: string;
  // Tunnel diagnostics fields
  ssh_process_status?: string;
  tunnel_start_time?: string;
  tunnel_uptime_seconds?: number;
  last_success_health_check?: string;
  current_public_url?: string;
  tunnel_provider?: string;
  restart_count?: number;
  last_restart_reason?: string;
  error_reason?: string;
  configured_port?: number;
}

interface HealthReport {
  ready: boolean;
  total_startup_duration_seconds: number;
  components: {
    backend: HealthComponentStatus;
    database: HealthComponentStatus;
    whatsapp: HealthComponentStatus;
    tunnel: HealthComponentStatus;
    external_apis: HealthComponentStatus;
  };
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function BackendHealthGuard({ children }: { children: React.ReactNode }) {
  const [report, setReport] = useState<HealthReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorCount, setErrorCount] = useState(0);

  useEffect(() => {
    let active = true;

    async function checkHealth() {
      try {
        const res = await fetch(`${API_BASE}/health`, { cache: 'no-store' });
        if (!res.ok) {
          throw new Error(`HTTP error ${res.status}`);
        }
        const data = await res.json();
        if (active) {
          setReport(data);
          setErrorCount(0);
          if (data.ready) {
            setLoading(false);
          }
        }
      } catch (err) {
        console.warn("Backend health check failed. Retrying...", err);
        if (active) {
          setErrorCount(prev => prev + 1);
          // Set custom report when backend is unreachable/offline
          setReport({
            ready: false,
            total_startup_duration_seconds: 0,
            components: {
              backend: { status: "offline" },
              database: { status: "pending" },
              whatsapp: { status: "pending" },
              tunnel: { status: "pending" },
              external_apis: { status: "pending" }
            }
          });
        }
      }
    }

    checkHealth();
    const interval = setInterval(checkHealth, 1500);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  // While the backend is loading or starting up, show the beautiful dashboard
  if (loading || !report || !report.ready) {
    const backendStatus = report?.components?.backend?.status || "offline";
    const dbStatus = report?.components?.database?.status || "pending";
    const waStatus = report?.components?.whatsapp?.status || "pending";
    const tunnelStatus = report?.components?.tunnel?.status || "pending";
    const aiStatus = report?.components?.external_apis?.status || "pending";

    return (
      <div className="fixed inset-0 bg-slate-950 flex flex-col items-center justify-center p-6 z-[9999] font-sans antialiased overflow-y-auto">
        {/* Animated background glow */}
        <div className="absolute top-1/4 left-1/4 w-[300px] h-[300px] rounded-full bg-cyan-500/10 blur-[100px] animate-pulse pointer-events-none" />
        <div className="absolute bottom-1/4 right-1/4 w-[300px] h-[300px] rounded-full bg-indigo-500/10 blur-[100px] animate-pulse pointer-events-none" style={{ animationDelay: '2s' }} />

        {/* Dashboard Container */}
        <div className="w-full max-w-xl bg-slate-900/60 border border-slate-800 rounded-2xl p-8 backdrop-blur-xl shadow-2xl relative overflow-hidden">
          
          {/* Header */}
          <div className="flex items-center justify-between mb-8 pb-6 border-b border-slate-800">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                <Activity className="h-6 w-6 text-cyan-400 animate-pulse" />
                VyaparAI Dev Suite
              </h1>
              <p className="text-sm text-slate-400 mt-1">Checking startup dependencies & tunnels</p>
            </div>
            
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700 text-xs text-slate-300">
              {backendStatus === "offline" ? (
                <>
                  <Loader2 className="h-3 w-3 text-amber-400 animate-spin" />
                  Backend Offline (Retrying...)
                </>
              ) : (
                <>
                  <Loader2 className="h-3 w-3 text-cyan-400 animate-spin" />
                  Booting...
                </>
              )}
            </div>
          </div>

          {/* Locked Message */}
          <div className="mb-8 p-4 rounded-xl bg-indigo-950/40 border border-indigo-900/50 flex items-start gap-3">
            <Lock className="h-5 w-5 text-indigo-400 shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-semibold text-indigo-200">Requests Intercepted</h4>
              <p className="text-xs text-indigo-300/80 mt-0.5">
                Frontend client requests are locked. The dashboard will mount and initialize as soon as all critical backend checklist services report READY.
              </p>
            </div>
          </div>

          {/* Diagnostics Checklist */}
          <div className="space-y-4">
            
            {/* 1. API Server */}
            <div className="flex items-center justify-between p-4 rounded-xl bg-slate-800/30 border border-slate-800/80 hover:border-slate-700 transition-colors">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${backendStatus === "healthy" ? "bg-emerald-500/10" : "bg-slate-800"}`}>
                  <Activity className={`h-5 w-5 ${backendStatus === "healthy" ? "text-emerald-400" : "text-slate-400"}`} />
                </div>
                <div>
                  <h3 className="text-sm font-medium text-white">API Server Status</h3>
                  <p className="text-xs text-slate-400">Core FastAPI service framework</p>
                </div>
              </div>
              <div>
                {backendStatus === "healthy" ? (
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">HEALTHY</span>
                ) : (
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">OFFLINE</span>
                )}
              </div>
            </div>

            {/* 2. Database Connection */}
            <div className="flex items-center justify-between p-4 rounded-xl bg-slate-800/30 border border-slate-800/80 hover:border-slate-700 transition-colors">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${dbStatus !== "pending" && dbStatus !== "offline" ? "bg-emerald-500/10" : "bg-slate-800"}`}>
                  <Database className={`h-5 w-5 ${dbStatus !== "pending" && dbStatus !== "offline" ? "text-emerald-400" : "text-slate-400"}`} />
                </div>
                <div>
                  <h3 className="text-sm font-medium text-white">Database (Supabase)</h3>
                  <p className="text-xs text-slate-400">
                    {report?.components?.database?.mode === "mock" ? "Running in Mock (In-Memory) mode" : "Real-time Supabase connection"}
                  </p>
                </div>
              </div>
              <div>
                {dbStatus === "healthy" ? (
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">CONNECTED</span>
                ) : dbStatus === "mock" ? (
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">MOCK DB</span>
                ) : (
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-800 text-slate-500 border border-slate-700">PENDING</span>
                )}
              </div>
            </div>

            {/* 3. WhatsApp Service */}
            <div className="flex items-center justify-between p-4 rounded-xl bg-slate-800/30 border border-slate-800/80 hover:border-slate-700 transition-colors">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${waStatus !== "pending" && waStatus !== "offline" ? "bg-emerald-500/10" : "bg-slate-800"}`}>
                  <Smartphone className={`h-5 w-5 ${waStatus !== "pending" && waStatus !== "offline" ? "text-emerald-400" : "text-slate-400"}`} />
                </div>
                <div>
                  <h3 className="text-sm font-medium text-white">WhatsApp Integration</h3>
                  <p className="text-xs text-slate-400">
                    {report?.components?.whatsapp?.provider === "meta" ? "Meta Cloud API provider" : "Evolution API container"}
                  </p>
                </div>
              </div>
              <div>
                {waStatus === "healthy" ? (
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">CONNECTED</span>
                ) : waStatus === "mock" || waStatus === "fallback" ? (
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">SANDBOX</span>
                ) : (
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-800 text-slate-500 border border-slate-700">PENDING</span>
                )}
              </div>
            </div>

            {/* 4. Public Tunnel */}
            <div className="flex flex-col p-4 rounded-xl bg-slate-800/30 border border-slate-800/80 hover:border-slate-700 transition-colors gap-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${tunnelStatus === "healthy" ? "bg-emerald-500/10" : "bg-slate-800"}`}>
                    <Network className={`h-5 w-5 ${tunnelStatus === "healthy" ? "text-emerald-400" : "text-slate-400"}`} />
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-white">Public SSH Tunnel ({report?.components?.tunnel?.tunnel_provider || "localhost.run"})</h3>
                    <p className="text-xs text-slate-400 truncate max-w-[250px]">
                      {report?.components?.tunnel?.public_url || "Waiting for SSH connection..."}
                    </p>
                  </div>
                </div>
                <div>
                  {tunnelStatus === "healthy" ? (
                    <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">FORWARDING</span>
                  ) : report?.components?.tunnel?.error_reason ? (
                    <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-red-500/10 text-red-400 border border-red-500/20">ERROR</span>
                  ) : (
                    <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-800 text-slate-500 border border-slate-700 animate-pulse">SYNCING</span>
                  )}
                </div>
              </div>

              {/* Advanced Diagnostics block (Requirements 5 & 6) */}
              {(report?.components?.tunnel?.ssh_process_status || report?.components?.tunnel?.error_reason) && (
                <div className="mt-1 pt-3 border-t border-slate-800/50 text-xs text-slate-400 space-y-1 bg-slate-900/40 p-2.5 rounded-lg border border-slate-850">
                  <div className="grid grid-cols-2 gap-y-1">
                    <div>SSH Process: <span className={report?.components?.tunnel?.ssh_process_status === "Running" ? "text-emerald-400" : "text-red-400 font-semibold"}>{report?.components?.tunnel?.ssh_process_status || "Stopped"}</span></div>
                    <div>Uptime: <span className="text-slate-200 font-mono">{report?.components?.tunnel?.tunnel_uptime_seconds ? `${report.components.tunnel.tunnel_uptime_seconds}s` : "0s"}</span></div>
                    <div>Restarts: <span className="text-slate-200">{report?.components?.tunnel?.restart_count ?? 0}</span></div>
                    <div>Last Check: <span className="text-slate-300 font-mono truncate">{report?.components?.tunnel?.last_success_health_check ? report.components.tunnel.last_success_health_check.split(" ")[1] : "Never"}</span></div>
                  </div>
                  {report?.components?.tunnel?.last_restart_reason && (
                    <div className="text-[10px] text-indigo-300 italic truncate mt-1">
                      Last Recover: {report.components.tunnel.last_restart_reason}
                    </div>
                  )}
                  {report?.components?.tunnel?.error_reason && (
                    <div className="text-[10px] text-amber-400 font-semibold mt-1">
                      Error Code: {report.components.tunnel.error_reason}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* 5. External APIs / Ollama */}
            <div className="flex items-center justify-between p-4 rounded-xl bg-slate-800/30 border border-slate-800/80 hover:border-slate-700 transition-colors">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${aiStatus === "healthy" ? "bg-emerald-500/10" : "bg-slate-800"}`}>
                  <Cpu className={`h-5 w-5 ${aiStatus === "healthy" ? "text-emerald-400" : "text-slate-400"}`} />
                </div>
                <div>
                  <h3 className="text-sm font-medium text-white">Ollama Local LLM</h3>
                  <p className="text-xs text-slate-400">
                    Model: {report?.components?.external_apis?.ollama_model || "llama3.1"}
                  </p>
                </div>
              </div>
              <div>
                {aiStatus === "healthy" ? (
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">ONLINE</span>
                ) : (
                  <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-800 text-slate-500 border border-slate-700 animate-pulse">WARMING</span>
                )}
              </div>
            </div>

          </div>

          {/* Footer Uptime & Timing details */}
          <div className="mt-8 pt-6 border-t border-slate-800 flex items-center justify-between text-xs text-slate-500">
            <div>
              Total Startup Duration: <span className="text-slate-300 font-mono">{report?.total_startup_duration_seconds ? `${report.total_startup_duration_seconds.toFixed(2)}s` : "Calculating..."}</span>
            </div>
            <div>
              Uptime: <span className="text-slate-300 font-mono">{report?.components?.backend?.uptime_seconds ? `${report.components.backend.uptime_seconds}s` : "0s"}</span>
            </div>
          </div>

        </div>
      </div>
    );
  }

  // Once backend is ready, render app pages normally
  return <>{children}</>;
}
