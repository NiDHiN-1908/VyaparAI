// frontend/app/whatsapp-settings/page.tsx
"use client";

import { useState, useEffect, useRef } from "react";
import { 
  MessageSquare, 
  QrCode, 
  Wifi, 
  WifiOff, 
  CheckCircle, 
  RefreshCw, 
  AlertCircle, 
  Trash2,
  Settings,
  Sparkles
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const DEFAULT_TENANT = "00000000-0000-0000-0000-000000000000";

export default function WhatsAppSettingsPage() {
  const [instanceName, setInstanceName] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeInstance, setActiveInstance] = useState<any>(null);
  const [qrCode, setQrCode] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("disconnected");
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Global ref to manage the active polling interval and prevent stale/ghost intervals
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // 1. Check for any active instances for the default tenant on mount
  async function checkActiveInstances() {
    try {
      const res = await fetch(`${API_BASE}/whatsapp/instances?tenant_id=${DEFAULT_TENANT}`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === "success" && data.data && data.data.length > 0) {
          // Find the first instance
          const active = data.data[0];
          setActiveInstance(active);
          setInstanceName(active.instance_name);
          pollStatus(active.id);
        }
      }
    } catch (err) {
      console.warn("Failed to check active instances:", err);
    }
  }

  useEffect(() => {
    // Check initially
    checkActiveInstances();
    
    // Cleanup polling interval on component unmount
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  // 2. Poll QR code & status
  async function pollStatus(instanceId: string) {
    // Clear any existing active interval to prevent duplicate polling leaks
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setPolling(true);
    
    let qrFetchCount = 0;
    pollIntervalRef.current = setInterval(async () => {
      try {
        // Fetch status
        const statusRes = await fetch(`${API_BASE}/whatsapp/${instanceId}/status`);
        const statusData = await statusRes.json();
        if (statusRes.ok && statusData.status === "success") {
          const connectionStatus = statusData.connection_status;
          setStatus(connectionStatus);
          
          if (connectionStatus === "connected") {
            setQrCode(null);
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setPolling(false);
            return;
          }
        }

        // Fetch QR Code if not connected
        if (qrFetchCount % 2 === 0) { // Fetch QR code every 4 seconds
          const qrRes = await fetch(`${API_BASE}/whatsapp/${instanceId}/qrcode`);
          const qrData = await qrRes.json();
          if (qrRes.ok && qrData.status === "success" && qrData.qrcode) {
            setQrCode(qrData.qrcode);
          }
        }
        qrFetchCount++;

        // Timeout safety after 5 minutes of polling
        if (qrFetchCount > 75) {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
          setPolling(false);
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    }, 2000);
  }

  // 3. Connect WhatsApp Instance
  async function handleConnect(e: React.FormEvent) {
    e.preventDefault();
    if (!instanceName.trim()) {
      setError("Please provide a valid instance name.");
      return;
    }

    setLoading(true);
    setError(null);
    setQrCode(null);
    setStatus("connecting");

    // Clear existing interval before starting connect flow
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }

    try {
      const res = await fetch(`${API_BASE}/whatsapp/connect`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          tenant_id: DEFAULT_TENANT,
          instance_name: instanceName.trim().toLowerCase()
        })
      });

      const data = await res.json();
      if (res.ok && data.status === "success") {
        setActiveInstance(data.data);
        pollStatus(data.data.id);
      } else {
        setError(data.message || data.detail || "Failed to create connection instance.");
        setStatus("disconnected");
      }
    } catch (err) {
      setError("Network error. Make sure the backend server is online.");
      setStatus("disconnected");
    } finally {
      setLoading(false);
    }
  }

  // 4. Disconnect WhatsApp Instance
  async function handleDisconnect(deleteCompletely: boolean = false) {
    if (!activeInstance) return;
    setLoading(true);
    setError(null);

    // Clear active interval immediately to stop polling a disconnected/deleted session
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setPolling(false);

    try {
      const res = await fetch(`${API_BASE}/whatsapp/${activeInstance.id}/disconnect?delete=${deleteCompletely}`, {
        method: "POST"
      });
      if (res.ok) {
        if (deleteCompletely) {
          setActiveInstance(null);
          setInstanceName("");
          setQrCode(null);
        }
        setStatus("disconnected");
      } else {
        setError("Failed to disconnect instance.");
      }
    } catch (err) {
      setError("Failed to disconnect due to network error.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
          WhatsApp Integration Settings
        </h1>
        <p className="text-slate-400 mt-2">
          Connect your business WhatsApp account using Evolution API gateway. Synchronize incoming chats, configure automatic AI replies, and manage customer communications.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Connection Form Column */}
        <div className="md:col-span-1 glass-panel rounded-2xl p-6 space-y-6 h-max">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-indigo-400" />
            <h3 className="font-bold text-lg text-white">Configure Connection</h3>
          </div>

          <form onSubmit={handleConnect} className="space-y-4">
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                Instance Name
              </label>
              <input
                type="text"
                placeholder="e.g. kochi_spice_whatsapp"
                value={instanceName}
                onChange={(e) => setInstanceName(e.target.value)}
                disabled={activeInstance !== null}
                className="w-full bg-slate-950 border border-slate-900 rounded-xl px-4 py-3 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 text-sm disabled:opacity-50"
              />
              <p className="text-[10px] text-slate-500">
                A unique name to identify this WhatsApp instance in the API gateway.
              </p>
            </div>

            {error && (
              <div className="flex items-start gap-2 bg-rose-500/10 border border-rose-500/20 rounded-xl p-3.5 text-xs text-rose-400">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {!activeInstance ? (
              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-900 text-white font-bold py-3.5 rounded-xl shadow-lg transition active:scale-95 text-sm"
              >
                {loading ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Connect WhatsApp
                  </>
                )}
              </button>
            ) : (
              <div className="space-y-2 pt-2">
                <button
                  type="button"
                  onClick={() => handleDisconnect(false)}
                  disabled={loading}
                  className="w-full bg-slate-900 border border-slate-800 hover:bg-slate-800 hover:text-white text-slate-300 font-bold py-3 rounded-xl transition text-xs"
                >
                  Disconnect Session
                </button>
                <button
                  type="button"
                  onClick={() => handleDisconnect(true)}
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-1.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 font-bold py-3 rounded-xl transition text-xs border border-rose-500/10"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Delete Connection Profile
                </button>
              </div>
            )}
          </form>
        </div>

        {/* Display Status & QR Code Panel Column */}
        <div className="md:col-span-2 glass-panel rounded-2xl p-6 flex flex-col justify-between h-[460px]">
          {/* Top Panel Status Info */}
          <div className="flex justify-between items-start border-b border-slate-800/80 pb-4">
            <div>
              <h3 className="font-bold text-lg text-white">Status Monitor</h3>
              <p className="text-xs text-slate-400 mt-1">
                Instance Name: <span className="font-mono text-indigo-400">{activeInstance?.instance_name || "N/A"}</span>
              </p>
            </div>

            {/* Connection Badge */}
            <div>
              {status === "connected" ? (
                <span className="flex items-center gap-1.5 text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3.5 py-1.5 rounded-full">
                  <Wifi className="w-4 h-4" />
                  Connected
                </span>
              ) : status === "connecting" ? (
                <span className="flex items-center gap-1.5 text-xs font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-3.5 py-1.5 rounded-full animate-pulse">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Connecting
                </span>
              ) : (
                <span className="flex items-center gap-1.5 text-xs font-bold bg-slate-800 text-slate-400 border border-slate-700 px-3.5 py-1.5 rounded-full">
                  <WifiOff className="w-4 h-4" />
                  Disconnected
                </span>
              )}
            </div>
          </div>

          {/* Middle Body */}
          <div className="flex-1 flex items-center justify-center py-6">
            {!activeInstance ? (
              <div className="text-center space-y-2 text-slate-500">
                <MessageSquare className="w-12 h-12 mx-auto text-slate-800" />
                <p className="text-sm font-semibold text-slate-400">No Active WhatsApp Instance</p>
                <p className="text-xs text-slate-600">Please type a name and connect to initialize onboarding.</p>
              </div>
            ) : status === "connected" ? (
              <div className="text-center space-y-4 max-w-sm">
                <CheckCircle className="w-16 h-16 mx-auto text-emerald-400 animate-bounce" />
                <div>
                  <h4 className="font-bold text-white text-lg">WhatsApp Sync Active!</h4>
                  <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                    Your WhatsApp profile is successfully linked. Incoming messages will now appear automatically in your WhatsApp Live Chat dashboard.
                  </p>
                </div>
              </div>
            ) : qrCode ? (
              <div className="flex flex-col md:flex-row items-center gap-8 bg-slate-950/40 border border-slate-900 rounded-2xl p-6 shadow-xl">
                {/* QR Code image */}
                <div className="bg-white p-4 rounded-xl flex items-center justify-center shadow-lg border border-slate-200">
                  <img 
                    src={qrCode} 
                    alt="WhatsApp QR Login Code" 
                    className="w-48 h-48 block"
                  />
                </div>

                {/* Scanning instructions */}
                <div className="space-y-4 text-left max-w-xs">
                  <div className="flex items-center gap-2 text-indigo-400">
                    <QrCode className="w-5 h-5" />
                    <h4 className="font-bold text-sm">Scan to Connect</h4>
                  </div>
                  <ol className="list-decimal pl-4 space-y-1.5 text-xs text-slate-300 leading-relaxed">
                    <li>Open WhatsApp on your phone.</li>
                    <li>Tap Menu (Settings) and select <b>Linked Devices</b>.</li>
                    <li>Tap <b>Link a Device</b>.</li>
                    <li>Point your phone camera to this QR code to login.</li>
                  </ol>
                </div>
              </div>
            ) : (
              <div className="text-center space-y-3">
                <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin mx-auto" />
                <p className="text-xs text-slate-400">Initializing connection session, generating secure QR login...</p>
              </div>
            )}
          </div>

          {/* Bottom Panel Info */}
          <div className="text-[10px] text-slate-500 border-t border-slate-900 pt-3 flex justify-between items-center">
            <span>Provider Instance Status Monitor</span>
            {polling && <span className="text-indigo-400 font-medium flex items-center gap-1"><RefreshCw className="w-2.5 h-2.5 animate-spin" /> Real-time Sync Active</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
