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
  Sparkles,
  Youtube,
  ShieldCheck,
  HelpCircle,
  LogOut,
  Instagram,
  ChevronRight,
  TrendingUp,
  Cpu
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DEFAULT_TENANT = "00000000-0000-0000-0000-000000000000";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<"whatsapp" | "youtube" | "nursery" | "instagram">("whatsapp");

  // Delivery Rules States
  const [deliveryEnabled, setDeliveryEnabled] = useState(true);
  const [freeMinDistance, setFreeMinDistance] = useState("5");
  const [freeMaxDistance, setFreeMaxDistance] = useState("10");
  const [chargeUnderMin, setChargeUnderMin] = useState("10");
  const [chargeOverMax, setChargeOverMax] = useState("15");
  const [hugePurchaseMinAmount, setHugePurchaseMinAmount] = useState("1500");
  const [hugePurchaseDiscountPct, setHugePurchaseDiscountPct] = useState("10");
  const [permanentCustomerMinOrders, setPermanentCustomerMinOrders] = useState("5");
  const [permanentCustomerDiscountPct, setPermanentCustomerDiscountPct] = useState("15");
  const [deliveryLoading, setDeliveryLoading] = useState(false);
  const [deliverySaveStatus, setDeliverySaveStatus] = useState<{ status: string; message: string }>({ status: "", message: "" });
  
  // WhatsApp States
  const [instanceName, setInstanceName] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeInstance, setActiveInstance] = useState<any>(null);
  const [qrCode, setQrCode] = useState<string | null>(null);
  const [whatsappStatus, setWhatsappStatus] = useState<string>("disconnected");
  const [polling, setPolling] = useState(false);
  const [waError, setWaError] = useState<string | null>(null);

  // YouTube States
  const [ytLoading, setYtLoading] = useState(true);
  const [ytChannel, setYtChannel] = useState<any>(null);
  const [ytError, setYtError] = useState<string | null>(null);
  const [ytActionLoading, setYtActionLoading] = useState(false);

  // Global ref to manage the active WhatsApp polling interval
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // --- 1. WhatsApp Lifecycle ---
  async function checkActiveInstances() {
    try {
      const res = await fetch(`${API_BASE}/whatsapp/instances?tenant_id=${DEFAULT_TENANT}`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === "success" && data.data && data.data.length > 0) {
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

  async function pollStatus(instanceId: string) {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setPolling(true);
    
    let qrFetchCount = 0;
    pollIntervalRef.current = setInterval(async () => {
      try {
        const statusRes = await fetch(`${API_BASE}/whatsapp/${instanceId}/status`);
        const statusData = await statusRes.json();
        if (statusRes.ok && statusData.status === "success") {
          const connectionStatus = statusData.connection_status;
          setWhatsappStatus(connectionStatus);
          
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

        if (qrFetchCount % 2 === 0) {
          const qrRes = await fetch(`${API_BASE}/whatsapp/${instanceId}/qrcode`);
          const qrData = await qrRes.json();
          if (qrRes.ok && qrData.status === "success" && qrData.qrcode) {
            setQrCode(qrData.qrcode);
          }
        }
        qrFetchCount++;

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

  async function handleConnect(e: React.FormEvent) {
    e.preventDefault();
    if (!instanceName.trim()) {
      setWaError("Please provide a valid instance name.");
      return;
    }

    setLoading(true);
    setWaError(null);
    setQrCode(null);
    setWhatsappStatus("connecting");

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
        setWaError(data.message || data.detail || "Failed to create connection instance.");
        setWhatsappStatus("disconnected");
      }
    } catch (err) {
      setWaError("Network error. Make sure the backend server is online.");
      setWhatsappStatus("disconnected");
    } finally {
      setLoading(false);
    }
  }

  async function handleDisconnect(deleteCompletely: boolean = false) {
    if (!activeInstance) return;
    setLoading(true);
    setWaError(null);

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
        setWhatsappStatus("disconnected");
      } else {
        setWaError("Failed to disconnect instance.");
      }
    } catch (err) {
      setWaError("Failed to disconnect due to network error.");
    } finally {
      setLoading(false);
    }
  }

  // --- 2. YouTube Lifecycle ---
  async function checkYoutubeStatus() {
    setYtLoading(true);
    setYtError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/youtube/status`);
      const data = await res.json();
      if (data.connected && data.channel) {
        setYtChannel(data.channel);
      } else {
        setYtChannel(null);
      }
    } catch (err) {
      console.error(err);
      setYtError("Failed to fetch connection status from VyaparAI backend.");
    } finally {
      setYtLoading(false);
    }
  }

  async function handleYoutubeDisconnect() {
    setYtActionLoading(true);
    setYtError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/youtube/disconnect`, {
        method: "POST",
      });
      if (res.ok) {
        setYtChannel(null);
      } else {
        setYtError("Failed to disconnect channel.");
      }
    } catch (err) {
      setYtError("Server connection failed.");
    } finally {
      setYtActionLoading(false);
    }
  }

  async function fetchDeliveryConfig() {
    try {
      const res = await fetch(`${API_BASE}/whatsapp/delivery-config`);
      if (res.ok) {
        const data = await res.json();
        setDeliveryEnabled(data.enabled);
        setFreeMinDistance(String(data.free_min_distance ?? 5));
        setFreeMaxDistance(String(data.free_max_distance ?? 10));
        setChargeUnderMin(String(data.charge_under_5km_per_km ?? 10));
        setChargeOverMax(String(data.charge_over_10km_per_km ?? 15));
        setHugePurchaseMinAmount(String(data.huge_purchase_min_amount ?? 1500));
        setHugePurchaseDiscountPct(String(data.huge_purchase_discount_pct ?? 10));
        setPermanentCustomerMinOrders(String(data.permanent_customer_min_orders ?? 5));
        setPermanentCustomerDiscountPct(String(data.permanent_customer_discount_pct ?? 15));
      }
    } catch (err) {
      console.warn("Failed to fetch delivery config:", err);
    }
  }

  async function handleSaveDelivery(e: React.FormEvent) {
    e.preventDefault();
    setDeliveryLoading(true);
    setDeliverySaveStatus({ status: "saving", message: "Saving rules..." });
    try {
      const res = await fetch(`${API_BASE}/whatsapp/delivery-config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          enabled: deliveryEnabled,
          free_min_distance: parseFloat(freeMinDistance) || 5.0,
          free_max_distance: parseFloat(freeMaxDistance) || 10.0,
          charge_under_5km_per_km: parseFloat(chargeUnderMin) || 10.0,
          charge_over_10km_per_km: parseFloat(chargeOverMax) || 15.0,
          huge_purchase_min_amount: parseFloat(hugePurchaseMinAmount) || 1500.0,
          huge_purchase_discount_pct: parseFloat(hugePurchaseDiscountPct) || 10.0,
          permanent_customer_min_orders: parseInt(permanentCustomerMinOrders) || 5,
          permanent_customer_discount_pct: parseFloat(permanentCustomerDiscountPct) || 15.0
        })
      });
      if (res.ok) {
        setDeliverySaveStatus({ status: "success", message: "Nursery Delivery Rules saved successfully!" });
        setTimeout(() => setDeliverySaveStatus({ status: "", message: "" }), 3000);
      } else {
        setDeliverySaveStatus({ status: "error", message: "Failed to save delivery rules." });
      }
    } catch (err) {
      setDeliverySaveStatus({ status: "error", message: "Network error saving delivery config." });
    } finally {
      setDeliveryLoading(false);
    }
  }

  useEffect(() => {
    // Check initially
    checkActiveInstances();
    checkYoutubeStatus();
    fetchDeliveryConfig();

    // Parse URL for YouTube callback messages
    const params = new URLSearchParams(window.location.search);
    if (params.get("status") === "success") {
      setActiveTab("youtube");
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (params.get("status") === "error") {
      setActiveTab("youtube");
      setYtError(params.get("error") || "Authentication failed.");
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-16">
      
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-2 text-indigo-400 text-xs font-bold uppercase tracking-widest mb-1.5">
          <Settings className="w-4.5 h-4.5" />
          System Settings & Integrations
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-slate-100 to-slate-400 bg-clip-text text-transparent">
          Platform Integrations Settings
        </h1>
        <p className="text-slate-400 text-sm mt-2 leading-relaxed">
          Manage your social channel integrations, configure automated chat gateways, and preview future expansion scopes.
        </p>
      </div>

      {/* Tabs Selector */}
      <div className="flex border-b border-slate-800/40 gap-6">
        <button
          onClick={() => setActiveTab("whatsapp")}
          className={`pb-4 text-xs font-bold uppercase tracking-widest border-b-2 transition-all ${
            activeTab === "whatsapp" 
              ? "text-indigo-400 border-indigo-500 font-extrabold" 
              : "text-slate-500 border-transparent hover:text-slate-300"
          }`}
        >
          WhatsApp Gateway
        </button>
        <button
          onClick={() => setActiveTab("youtube")}
          className={`pb-4 text-xs font-bold uppercase tracking-widest border-b-2 transition-all ${
            activeTab === "youtube" 
              ? "text-rose-400 border-rose-500 font-extrabold" 
              : "text-slate-500 border-transparent hover:text-slate-300"
          }`}
        >
          YouTube Channel
        </button>
        <button
          onClick={() => setActiveTab("nursery")}
          className={`pb-4 text-xs font-bold uppercase tracking-widest border-b-2 transition-all flex items-center gap-2 ${
            activeTab === "nursery" 
              ? "text-emerald-400 border-emerald-500 font-extrabold" 
              : "text-slate-500 border-transparent hover:text-slate-300"
          }`}
        >
          Nursery Delivery Rules
        </button>
        <button
          onClick={() => setActiveTab("instagram")}
          className={`pb-4 text-xs font-bold uppercase tracking-widest border-b-2 transition-all flex items-center gap-2 ${
            activeTab === "instagram" 
              ? "text-pink-400 border-pink-500 font-extrabold" 
              : "text-slate-500 border-transparent hover:text-slate-300"
          }`}
        >
          Instagram (Future Scope)
        </button>
      </div>

      {/* TAB CONTENT 1: WHATSAPP SETTINGS */}
      {activeTab === "whatsapp" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-fadeIn">
          {/* Form */}
          <div className="md:col-span-1 p-6 backdrop-blur-md bg-slate-900/60 border border-slate-800/40 rounded-2xl shadow-lg flex flex-col justify-between h-max space-y-6">
            <div className="flex items-center gap-2">
              <Settings className="w-4.5 h-4.5 text-indigo-400" />
              <h3 className="font-bold text-sm text-slate-100">WhatsApp Onboarding</h3>
            </div>

            <form onSubmit={handleConnect} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-widest block">
                  Instance Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. kochi_shop_whatsapp"
                  value={instanceName}
                  onChange={(e) => setInstanceName(e.target.value)}
                  disabled={activeInstance !== null}
                  className="w-full bg-slate-950 border border-slate-900 rounded-xl px-4 py-3 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 text-xs disabled:opacity-50"
                />
              </div>

              {waError && (
                <div className="flex items-start gap-2 bg-rose-500/10 border border-rose-500/20 rounded-xl p-3 text-xs text-rose-400">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <span>{waError}</span>
                </div>
              )}

              {!activeInstance ? (
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 bg-indigo-650 hover:bg-indigo-600 disabled:bg-slate-950 text-white font-bold py-3.5 rounded-xl shadow-lg transition active:scale-95 text-xs border border-indigo-650/40"
                >
                  {loading ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Create Connection Profile
                    </>
                  )}
                </button>
              ) : (
                <div className="space-y-2 pt-2">
                  <button
                    type="button"
                    onClick={() => handleDisconnect(false)}
                    disabled={loading}
                    className="w-full bg-slate-950 border border-slate-850 hover:border-slate-800 hover:text-white text-slate-400 font-bold py-3 rounded-xl transition text-xs"
                  >
                    Disconnect Active Session
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

          {/* QR Scan Status Monitor */}
          <div className="md:col-span-2 p-6 backdrop-blur-md bg-slate-900/60 border border-slate-800/40 rounded-2xl shadow-lg flex flex-col justify-between h-[420px]">
            <div className="flex justify-between items-start border-b border-slate-850/60 pb-4">
              <div>
                <h3 className="font-bold text-sm text-slate-100">Connection Monitor</h3>
                <p className="text-xs text-slate-500 mt-1">
                  Active Profile: <span className="font-mono text-indigo-400 font-semibold">{activeInstance?.instance_name || "Unconnected"}</span>
                </p>
              </div>

              {/* Status Badge */}
              <div>
                {whatsappStatus === "connected" ? (
                  <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3.5 py-1.5 rounded-full">
                    <Wifi className="w-3.5 h-3.5" />
                    Sync Active
                  </span>
                ) : whatsappStatus === "connecting" ? (
                  <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-3.5 py-1.5 rounded-full animate-pulse">
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    Handshaking
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest bg-slate-950 text-slate-500 border border-slate-850 px-3.5 py-1.5 rounded-full">
                    <WifiOff className="w-3.5 h-3.5" />
                    Offline
                  </span>
                )}
              </div>
            </div>

            {/* Scanning Panel */}
            <div className="flex-1 flex items-center justify-center py-6">
              {!activeInstance ? (
                <div className="text-center space-y-2 text-slate-500">
                  <MessageSquare className="w-10 h-10 mx-auto text-slate-800" />
                  <p className="text-xs font-bold text-slate-400">No Active WhatsApp Instance</p>
                  <p className="text-[11px] text-slate-500">Please connect a new profile in the left panel to scan QR codes.</p>
                </div>
              ) : whatsappStatus === "connected" ? (
                <div className="text-center space-y-3 max-w-sm">
                  <CheckCircle className="w-12 h-12 mx-auto text-emerald-400 animate-bounce" />
                  <div>
                    <h4 className="font-bold text-slate-200 text-sm">WhatsApp Sync Completed</h4>
                    <p className="text-xs text-slate-400 mt-2 leading-relaxed">
                      Your business number is active. The LangGraph Sales Agent is now listening to customer webhook checkouts in real-time.
                    </p>
                  </div>
                </div>
              ) : qrCode ? (
                <div className="flex flex-col sm:flex-row items-center gap-6 bg-slate-950/40 border border-slate-900 rounded-2xl p-5 shadow-xl">
                  {/* QR Image */}
                  <div className="bg-white p-3 rounded-lg flex items-center justify-center border border-slate-200 shadow-md">
                    <img src={qrCode} alt="WhatsApp Login Code" className="w-36 h-36 block" />
                  </div>
                  
                  {/* Instructions */}
                  <div className="space-y-3 text-left max-w-[240px]">
                    <div className="flex items-center gap-1.5 text-indigo-400">
                      <QrCode className="w-4.5 h-4.5" />
                      <h4 className="font-bold text-xs">Scan Linked Device</h4>
                    </div>
                    <ol className="list-decimal pl-4 space-y-1 text-[11px] text-slate-400 leading-normal">
                      <li>Open WhatsApp on your phone</li>
                      <li>Go to **Linked Devices** menu</li>
                      <li>Tap **Link a Device** and capture this QR code</li>
                    </ol>
                  </div>
                </div>
              ) : (
                <div className="text-center space-y-2">
                  <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin mx-auto" />
                  <p className="text-xs text-slate-400">Requesting Evolution API instance setup, please wait...</p>
                </div>
              )}
            </div>

            <div className="text-[9px] text-slate-500 border-t border-slate-900 pt-3 flex justify-between items-center">
              <span>Dynamic Evolution API Webhook Registrations</span>
              {polling && <span className="text-indigo-400 font-bold flex items-center gap-1"><RefreshCw className="w-2.5 h-2.5 animate-spin" /> Live syncing active</span>}
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT 2: YOUTUBE CONNECTION */}
      {activeTab === "youtube" && (
        <div className="animate-fadeIn">
          {ytLoading ? (
            <div className="p-12 backdrop-blur-md bg-slate-900/60 border border-slate-800/40 rounded-2xl flex flex-col items-center justify-center space-y-4">
              <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin" />
              <p className="text-slate-400 text-xs font-semibold">Auditing YouTube OAuth tokens...</p>
            </div>
          ) : ytError ? (
            <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 px-4 py-3 rounded-xl text-xs font-semibold flex items-center gap-2">
              <AlertCircle className="w-4.5 h-4.5" />
              {ytError}
            </div>
          ) : ytChannel ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              
              {/* Channel Profile card */}
              <div className="md:col-span-1 p-6 backdrop-blur-md bg-slate-900/60 border border-slate-800/40 rounded-2xl shadow-lg flex flex-col items-center text-center space-y-5 relative overflow-hidden h-max">
                <div className="absolute top-0 right-0 w-24 h-24 bg-rose-500/5 rounded-full blur-xl pointer-events-none" />
                <img
                  src={ytChannel.thumbnail || "https://images.unsplash.com/photo-1628157582853-a796fa650a6a?w=150&auto=format&fit=crop&q=80"}
                  alt={ytChannel.channel_name}
                  className="w-20 h-20 rounded-full border-4 border-slate-800 shadow-xl"
                />
                
                <div>
                  <h3 className="text-base font-black text-slate-100 flex items-center justify-center gap-1">
                    {ytChannel.channel_name}
                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  </h3>
                  <p className="text-slate-500 text-[10px] mt-1 font-mono">ID: {ytChannel.channel_id.slice(0, 16)}...</p>
                </div>

                <div className="w-full bg-slate-950/60 rounded-xl p-3 border border-slate-900 flex justify-around text-center">
                  <div>
                    <span className="text-[9px] text-slate-500 font-bold uppercase tracking-wider block">Subscribers</span>
                    <span className="text-base font-bold text-slate-100 mt-0.5 block">{ytChannel.subscriber_count.toLocaleString()}</span>
                  </div>
                  <div className="border-r border-slate-850/80 my-1" />
                  <div>
                    <span className="text-[9px] text-slate-500 font-bold uppercase tracking-wider block">Sync Status</span>
                    <span className="text-base font-bold text-emerald-400 mt-0.5 block">Active</span>
                  </div>
                </div>

                <button
                  onClick={handleYoutubeDisconnect}
                  disabled={ytActionLoading}
                  className="w-full flex items-center justify-center gap-2 bg-slate-950 hover:bg-slate-900 border border-slate-850 hover:border-slate-800 hover:text-rose-400 text-slate-400 font-bold py-3 rounded-xl transition text-xs"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  Disconnect Channel
                </button>
              </div>

              {/* Status details */}
              <div className="md:col-span-2 p-6 backdrop-blur-md bg-slate-900/60 border border-slate-800/40 rounded-2xl shadow-lg space-y-6">
                <h3 className="text-sm font-bold uppercase tracking-wider text-indigo-400 flex items-center gap-2">
                  <ShieldCheck className="w-4.5 h-4.5" />
                  Connected Permissions
                </h3>

                <div className="space-y-4 text-xs text-slate-300 leading-relaxed">
                  <div className="flex gap-2.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 flex-shrink-0" />
                    <div>
                      <strong className="text-slate-100">Authorized OAuth Read/Write Scopes:</strong>
                      <p className="text-[11px] text-slate-400 mt-0.5">Allows the autonomous CrewAI monitor to fetch comment threads and post auto-replies containing WA checkout links.</p>
                    </div>
                  </div>

                  <div className="flex gap-2.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 flex-shrink-0" />
                    <div>
                      <strong className="text-slate-100">Automated Polling Frequency:</strong>
                      <p className="text-[11px] text-slate-400 mt-0.5">The monitor checks active videos every 5 minutes. High-intent messages are qualifications-routed to leads instantly.</p>
                    </div>
                  </div>
                </div>

                <div className="p-4 bg-slate-950/40 border border-slate-900 rounded-xl flex gap-3">
                  <HelpCircle className="w-5 h-5 text-indigo-400 flex-shrink-0" />
                  <span className="text-[11px] text-slate-400 leading-normal">
                    To manually simulate YouTube comment streams, use the **Simulator Tool** inside the [Comment Inbox](/comment-inbox) to test pipeline actions instantly.
                  </span>
                </div>
              </div>

            </div>
          ) : (
            <div className="p-8 backdrop-blur-md bg-slate-900/60 border border-slate-800/40 rounded-2xl max-w-xl mx-auto flex flex-col items-center text-center space-y-6">
              <div className="w-12 h-12 rounded-full bg-rose-500/10 flex items-center justify-center text-rose-500">
                <Youtube className="w-6 h-6" />
              </div>

              <div className="space-y-1">
                <h3 className="text-base font-bold text-slate-200">Connect YouTube Channel</h3>
                <p className="text-slate-400 text-xs leading-normal max-w-sm">
                  Connect your business channel once. The autonomous monitoring agent will scan comment feeds and квалифицировать buyers instantly.
                </p>
              </div>

              <a
                href={`${API_BASE}/auth/youtube/login`}
                className="w-full max-w-xs flex items-center justify-center gap-2 bg-rose-650 hover:bg-rose-600 text-white font-bold py-3.5 rounded-xl shadow-md transition text-xs border border-rose-650/40"
              >
                <Youtube className="w-4 h-4 text-white" />
                Authorize YouTube Account
              </a>
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT 3: NURSERY DELIVERY RULES */}
      {activeTab === "nursery" && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 animate-fadeIn">
          {/* Rules Form */}
          <div className="md:col-span-1 p-6 backdrop-blur-md bg-slate-900/60 border border-slate-800/40 rounded-2xl shadow-lg flex flex-col justify-between h-max space-y-6">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4.5 h-4.5 text-emerald-400" />
              <h3 className="font-bold text-sm text-slate-100 font-heading">Nursery Delivery Logistics</h3>
            </div>

            <form onSubmit={handleSaveDelivery} className="space-y-4">
              
              {/* Enabled Checkbox */}
              <div className="flex items-center justify-between p-3 bg-slate-950/40 border border-slate-900 rounded-xl">
                <span className="text-[11px] font-bold text-slate-400 uppercase">Enable Shipping Rules</span>
                <input 
                  type="checkbox" 
                  checked={deliveryEnabled}
                  onChange={(e) => setDeliveryEnabled(e.target.checked)}
                  className="w-4 h-4 text-emerald-500 rounded bg-slate-900 border-slate-800 focus:ring-emerald-500 cursor-pointer"
                />
              </div>

              {/* Free Delivery Zone */}
              <div className="p-3.5 bg-slate-950/40 border border-slate-900 rounded-xl space-y-3">
                <span className="text-[11px] font-bold text-slate-400 uppercase block">Free Delivery Zone</span>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <span className="text-[9px] font-bold text-slate-500 uppercase">Min Radius (km)</span>
                    <input
                      type="number"
                      step="0.1"
                      value={freeMinDistance}
                      onChange={(e) => setFreeMinDistance(e.target.value)}
                      placeholder="5"
                      className="w-full bg-slate-950 border border-slate-900 rounded-lg px-3 py-2 text-slate-200 text-xs focus:outline-none focus:border-emerald-500 font-bold"
                      disabled={!deliveryEnabled}
                    />
                  </div>
                  <div className="space-y-1">
                    <span className="text-[9px] font-bold text-slate-500 uppercase">Max Radius (km)</span>
                    <input
                      type="number"
                      step="0.1"
                      value={freeMaxDistance}
                      onChange={(e) => setFreeMaxDistance(e.target.value)}
                      placeholder="10"
                      className="w-full bg-slate-950 border border-slate-900 rounded-lg px-3 py-2 text-slate-200 text-xs focus:outline-none focus:border-emerald-500 font-bold"
                      disabled={!deliveryEnabled}
                    />
                  </div>
                </div>
              </div>

              {/* Distance-Based Charges */}
              <div className="p-3.5 bg-slate-950/40 border border-slate-900 rounded-xl space-y-3">
                <span className="text-[11px] font-bold text-slate-400 uppercase block">Delivery Charge (INR / km)</span>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <span className="text-[9px] font-bold text-slate-500 uppercase">Under Min Radius</span>
                    <input
                      type="number"
                      value={chargeUnderMin}
                      onChange={(e) => setChargeUnderMin(e.target.value)}
                      placeholder="10"
                      className="w-full bg-slate-950 border border-slate-900 rounded-lg px-3 py-2 text-slate-200 text-xs focus:outline-none focus:border-emerald-500 font-bold"
                      disabled={!deliveryEnabled}
                    />
                  </div>
                  <div className="space-y-1">
                    <span className="text-[9px] font-bold text-slate-500 uppercase">Over Max Radius</span>
                    <input
                      type="number"
                      value={chargeOverMax}
                      onChange={(e) => setChargeOverMax(e.target.value)}
                      placeholder="15"
                      className="w-full bg-slate-950 border border-slate-900 rounded-lg px-3 py-2 text-slate-200 text-xs focus:outline-none focus:border-emerald-500 font-bold"
                      disabled={!deliveryEnabled}
                    />
                  </div>
                </div>
              </div>

              {/* Loyalty & Bulk Discounts */}
              <div className="p-3.5 bg-slate-950/40 border border-slate-900 rounded-xl space-y-3">
                <span className="text-[11px] font-bold text-slate-400 uppercase block">Huge Purchase Discount</span>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <span className="text-[9px] font-bold text-slate-500 uppercase">Min Value (INR)</span>
                    <input
                      type="number"
                      value={hugePurchaseMinAmount}
                      onChange={(e) => setHugePurchaseMinAmount(e.target.value)}
                      placeholder="1500"
                      className="w-full bg-slate-950 border border-slate-900 rounded-lg px-3 py-2 text-slate-200 text-xs focus:outline-none focus:border-emerald-500 font-bold"
                      disabled={!deliveryEnabled}
                    />
                  </div>
                  <div className="space-y-1">
                    <span className="text-[9px] font-bold text-slate-500 uppercase">Discount (%)</span>
                    <input
                      type="number"
                      value={hugePurchaseDiscountPct}
                      onChange={(e) => setHugePurchaseDiscountPct(e.target.value)}
                      placeholder="10"
                      className="w-full bg-slate-950 border border-slate-900 rounded-lg px-3 py-2 text-slate-200 text-xs focus:outline-none focus:border-emerald-500 font-bold"
                      disabled={!deliveryEnabled}
                    />
                  </div>
                </div>
                
                <span className="text-[11px] font-bold text-slate-400 uppercase block pt-1">Permanent Customer Tier</span>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <span className="text-[9px] font-bold text-slate-500 uppercase">Min Orders</span>
                    <input
                      type="number"
                      value={permanentCustomerMinOrders}
                      onChange={(e) => setPermanentCustomerMinOrders(e.target.value)}
                      placeholder="5"
                      className="w-full bg-slate-950 border border-slate-900 rounded-lg px-3 py-2 text-slate-200 text-xs focus:outline-none focus:border-emerald-500 font-bold"
                      disabled={!deliveryEnabled}
                    />
                  </div>
                  <div className="space-y-1">
                    <span className="text-[9px] font-bold text-slate-500 uppercase">Discount (%)</span>
                    <input
                      type="number"
                      value={permanentCustomerDiscountPct}
                      onChange={(e) => setPermanentCustomerDiscountPct(e.target.value)}
                      placeholder="15"
                      className="w-full bg-slate-950 border border-slate-900 rounded-lg px-3 py-2 text-slate-200 text-xs focus:outline-none focus:border-emerald-500 font-bold"
                      disabled={!deliveryEnabled}
                    />
                  </div>
                </div>
              </div>

              {deliverySaveStatus.message && (
                <div className={`p-3 rounded-xl text-xs font-semibold flex items-center gap-2 border ${
                  deliverySaveStatus.status === "success" 
                    ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" 
                    : deliverySaveStatus.status === "error"
                    ? "bg-rose-500/10 border-rose-500/20 text-rose-400"
                    : "bg-indigo-500/10 border-indigo-500/20 text-indigo-400 animate-pulse"
                }`}>
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{deliverySaveStatus.message}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={deliveryLoading}
                className="w-full flex items-center justify-center gap-2 bg-emerald-650 hover:bg-emerald-600 disabled:bg-slate-950 text-white font-bold py-3.5 rounded-xl shadow-lg transition active:scale-95 text-xs border border-emerald-650/40"
              >
                {deliveryLoading ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Save Delivery Rules
                  </>
                )}
              </button>

            </form>
          </div>

          {/* Guide & Operations Explanation */}
          <div className="md:col-span-2 p-6 backdrop-blur-md bg-slate-900/60 border border-slate-800/40 rounded-2xl shadow-lg space-y-6">
            <div>
              <h3 className="text-base font-bold text-slate-100 font-heading">Nursery Shipping & Loyalty Diagnostics</h3>
              <p className="text-xs text-slate-500 mt-1">How the AI sales bot handles delivery charges and customer rewards:</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              
              {/* Box 1: Address Parsing */}
              <div className="p-4 bg-slate-950/40 border border-slate-900 rounded-xl space-y-2">
                <div className="flex items-center gap-2 text-indigo-400 text-xs font-bold uppercase">
                  <Cpu className="w-4 h-4" />
                  Distance Detection
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  The bot parses the customer's text for a distance keyword (e.g. <code>8 km</code>). If none is specified, it uses a stable address hash fallback to estimate a distance between 2 and 15 km.
                </p>
              </div>

              {/* Box 2: Automated Loyalty Calculations */}
              <div className="p-4 bg-slate-950/40 border border-slate-900 rounded-xl space-y-2">
                <div className="flex items-center gap-2 text-emerald-400 text-xs font-bold uppercase">
                  <TrendingUp className="w-4 h-4" />
                  Loyalty & Bulk Discounts
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  The bot scans the database for completed past orders by the customer's username, applying the loyalty discount if order count exceeds the limit. It also tests total subtotal and quantity for bulk discounts.
                </p>
              </div>

            </div>

            {/* Sandbox details */}
            <div className="p-4 bg-slate-950/60 border border-slate-900 rounded-xl flex gap-3">
              <HelpCircle className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <h4 className="text-xs font-bold text-slate-200">How to test this pipeline:</h4>
                <ol className="list-decimal pl-4 text-[11px] text-slate-400 space-y-1 leading-normal">
                  <li>Go to your **WhatsApp Live Chat** and start checking out a product.</li>
                  <li>Simulate a delivery within the free radius: *"Deliver to MG Road, distance: 7 km"*. The bot applies **Free Delivery**.</li>
                  <li>Simulate a short distance address: *"Deliver to Bannerghatta, distance: 3 km"*. The bot applies a charge based on your under-limit rate (e.g., Rs. 30).</li>
                  <li>Simulate buying multiple items: *"I want to buy 3 plants, deliver to Sector 4, 12 km"*. The bot applies a **10% Huge Purchase Discount** and calculates distance surcharge for 12 km.</li>
                </ol>
              </div>
            </div>

          </div>
        </div>
      )}

      {/* TAB CONTENT 4: INSTAGRAM FUTURE SCOPE MOCKUP */}
      {activeTab === "instagram" && (
        <div className="animate-fadeIn space-y-6 max-w-xl mx-auto">
          <div className="p-8 backdrop-blur-md bg-slate-900/60 border border-slate-800/40 rounded-2xl flex flex-col items-center text-center space-y-6 relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-24 h-24 bg-pink-500/5 rounded-full blur-xl pointer-events-none" />
            <div className="absolute -bottom-8 -left-8 w-32 h-32 bg-purple-500/5 rounded-full blur-2xl pointer-events-none" />
            
            {/* Future Scope Badge */}
            <div className="flex items-center gap-1.5 text-[9px] font-bold text-pink-400 uppercase tracking-widest bg-pink-500/10 border border-pink-500/20 px-3 py-1 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-pink-500 animate-pulse" />
              Future Scope
            </div>

            {/* Gradient Logo */}
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-yellow-500 via-pink-500 to-purple-600 flex items-center justify-center text-white shadow-lg shadow-purple-500/10">
              <Instagram className="w-7 h-7" />
            </div>

            <div className="space-y-1">
              <h3 className="text-base font-bold text-slate-200">Instagram DM & Reels Sales Bot</h3>
              <p className="text-slate-400 text-xs leading-normal max-w-sm">
                Scale checkout conversions across Instagram. Automate story reply triggers, listen to comment tags, and answer inquiry details in DMs.
              </p>
            </div>

            {/* Simulated Configuration Form fields for Mockup display */}
            <div className="w-full space-y-3 bg-slate-950/60 p-4 border border-slate-900 rounded-xl text-left">
              <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Simulated Config Settings</span>
              
              <div className="space-y-1.5">
                <span className="text-[9px] text-slate-400 font-bold uppercase">Trigger Keyword</span>
                <input 
                  type="text" 
                  disabled 
                  placeholder="e.g. #buy or #price" 
                  className="w-full bg-slate-950 border border-slate-900 rounded-lg px-3 py-2 text-slate-500 text-xs cursor-not-allowed opacity-50"
                />
              </div>

              <div className="flex items-center gap-2 text-[10px] text-slate-500 font-semibold mt-1">
                <HelpCircle className="w-3.5 h-3.5 text-slate-600" />
                <span>Will use same LangGraph checkout graph state machine</span>
              </div>
            </div>

            {/* Locked Connection Button */}
            <button
              disabled
              className="w-full max-w-xs flex items-center justify-center gap-2 bg-slate-950 text-slate-500 border border-slate-850 font-bold py-3.5 rounded-xl cursor-not-allowed opacity-60 text-xs"
            >
              <Instagram className="w-4 h-4" />
              Instagram Connection Locked
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
