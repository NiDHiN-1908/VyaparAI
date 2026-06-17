// frontend/app/live-chat/page.tsx
"use client";

import { useEffect, useState, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { 
  MessageCircle, 
  Send, 
  Bot, 
  User, 
  RefreshCw, 
  ShieldCheck, 
  Sparkles,
  Search,
  MessageSquare,
  DollarSign,
  Package,
  Activity,
  ToggleLeft,
  ToggleRight
} from "lucide-react";

const API_BASE = "http://localhost:8000";

export default function UnifiedLiveChatPage() {
  const searchParams = useSearchParams();
  const leadIdParam = searchParams.get("lead_id");

  // Navigation / Lead states
  const [leads, setLeads] = useState<any[]>([]);
  const [selectedLead, setSelectedLead] = useState<any>(null);
  const [products, setProducts] = useState<any[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<any>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [loadingLeads, setLoadingLeads] = useState(true);
  
  // Autopilot toggle state (synced with the active lead)
  const [autopilot, setAutopilot] = useState(true);
  const [updatingAutopilot, setUpdatingAutopilot] = useState(false);

  // Chat History states (Unified WhatsApp Feed)
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [sendingMessage, setSendingMessage] = useState(false);
  const [messageText, setMessageText] = useState("");
  const [isProduction, setIsProduction] = useState(false); 

  // AI Pipeline tracking states
  const [aiState, setAiState] = useState("WELCOME");
  const [activeOrderId, setActiveOrderId] = useState<string | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);

  const aiSteps = [
    { key: "WELCOME", label: "Welcome" },
    { key: "PRODUCT_INFO", label: "Product Specs" },
    { key: "QA_LOOP", label: "Objection Q&A" },
    { key: "ADDRESS_COLLECTION", label: "Address Collection" },
    { key: "PAYMENT", label: "Payment Request" },
    { key: "ORDER_CONFIRMED", label: "Confirmed" }
  ];

  // 1. Fetch leads and products on mount
  async function fetchInitialData() {
    setLoadingLeads(true);
    try {
      const leadsRes = await fetch(`${API_BASE}/youtube/leads`);
      const leadsData = await leadsRes.json();
      if (leadsData.status === "success" && leadsData.data) {
        setLeads(leadsData.data);
        if (leadsData.data.length > 0) {
          const matchedLead = leadIdParam 
            ? leadsData.data.find((l: any) => String(l.id) === String(leadIdParam)) || leadsData.data[0]
            : leadsData.data[0];
          setSelectedLead(matchedLead);
          setAutopilot(matchedLead.autopilot !== false); // default to true
        }
      }
      
      const mockProds = [
        { id: "prod_cardamom", name: "Organic Cardamom", price: 350.00 },
        { id: "prod_oil", name: "Virgin Coconut Oil", price: 299.00 }
      ];
      setProducts(mockProds);
      setSelectedProduct(mockProds[0]);
    } catch (err) {
      console.error("Failed to load initial data:", err);
    } finally {
      setLoadingLeads(false);
    }
  }

  // 2. Fetch history for selected lead
  async function fetchHistory(leadId: string, silent = false) {
    if (!silent) setLoadingHistory(true);
    try {
      const res = await fetch(`${API_BASE}/whatsapp/history/${leadId}`);
      const data = await res.json();
      if (data.status === "success" && data.data) {
        setChatHistory(data.data);
        
        // Dynamically detect if AI requested payment in previous messages
        const paymentMsg = [...data.data].reverse().find(m => m.sender === "ai" && m.text.includes("order_id="));
        if (paymentMsg) {
          const match = paymentMsg.text.match(/order_id=([^&? )]+)/);
          if (match) {
            setActiveOrderId(match[1]);
            setAiState("PAYMENT");
          }
        }
      }
    } catch (err) {
      console.error("Failed to fetch WhatsApp history:", err);
    } finally {
      if (!silent) setLoadingHistory(false);
    }
  }

  useEffect(() => {
    fetchInitialData();
  }, [leadIdParam]);

  // Handle switching leads
  useEffect(() => {
    if (selectedLead) {
      setAutopilot(selectedLead.autopilot !== false);
      fetchHistory(selectedLead.id);
      setActiveOrderId(null);
      setAiState("WELCOME");
    } else {
      setChatHistory([]);
    }
  }, [selectedLead]);

  // 3. Scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  // 4. Polling for real-time customer and AI replies
  useEffect(() => {
    if (!selectedLead) return;
    const interval = setInterval(() => {
      fetchHistory(selectedLead.id, true);
    }, 2000);
    return () => clearInterval(interval);
  }, [selectedLead]);

  // 5. Toggle Autopilot state
  async function handleToggleAutopilot() {
    if (!selectedLead || updatingAutopilot) return;
    const nextAutopilot = !autopilot;
    setUpdatingAutopilot(true);
    try {
      const res = await fetch(`${API_BASE}/whatsapp/toggle-autopilot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lead_id: selectedLead.id,
          autopilot: nextAutopilot
        })
      });
      if (res.ok) {
        setAutopilot(nextAutopilot);
        // Update leads list in place
        setLeads(prev => prev.map(l => l.id === selectedLead.id ? { ...l, autopilot: nextAutopilot } : l));
      }
    } catch (err) {
      console.error("Failed to toggle autopilot:", err);
    } finally {
      setUpdatingAutopilot(false);
    }
  }

  // 6. Send message
  async function handleSendMessage(e: React.FormEvent) {
    e.preventDefault();
    if (!messageText.trim() || !selectedLead || sendingMessage) return;

    const currentText = messageText;
    setMessageText("");
    setSendingMessage(true);

    // If autopilot is ON, we send as 'customer' (pretending to be customer to test AI)
    // If autopilot is OFF, we send as 'business' (business takeover)
    const senderRole = autopilot ? "customer" : "business";

    try {
      const res = await fetch(`${API_BASE}/whatsapp/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lead_id: selectedLead.id,
          message: currentText,
          sender: senderRole,
          product_id: selectedProduct?.id
        })
      });
      const data = await res.json();
      if (res.ok && data.status === "success") {
        setIsProduction(data.mode === "production");
        
        // In AI mode, the endpoint returns both the customer's message and the AI response
        if (data.mode === "ai_agent") {
          setAiState(data.state);
          if (data.ai_msg?.text.includes("order_id=")) {
            const match = data.ai_msg.text.match(/order_id=([^&? )]+)/);
            if (match) setActiveOrderId(match[1]);
          }
        }
        
        // Reload history to ensure in sync
        fetchHistory(selectedLead.id, true);
      }
    } catch (err) {
      console.error("Failed to send message:", err);
    } finally {
      setSendingMessage(false);
    }
  }

  // Simulate payment callback
  async function handleSimulatePayment() {
    if (!activeOrderId) return;
    try {
      const res = await fetch(`${API_BASE}/payment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_id: activeOrderId,
          status: "paid"
        })
      });
      if (res.ok) {
        setAiState("ORDER_CONFIRMED");
        setActiveOrderId(null);
        fetchHistory(selectedLead.id, true);
      }
    } catch (err) {
      console.error("Payment simulation failed:", err);
    }
  }

  // Filter leads
  const filteredLeads = leads.filter(l => 
    l.username.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            WhatsApp Live Chat
          </h1>
          <p className="text-slate-400 mt-2">
            A single unified console to chat with clients, monitor active AI sales agent autopilots, and manually take over conversations.
          </p>
        </div>
        
        {/* Active Product display */}
        {selectedProduct && (
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-300">
            <Package className="w-4 h-4 text-indigo-400" />
            Selling: <span className="font-bold text-white">{selectedProduct.name}</span>
          </div>
        )}
      </div>

      {/* Main Container Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[700px]">
        
        {/* Left Sidebar: Leads & Settings */}
        <div className="glass-panel rounded-2xl p-4 flex flex-col justify-between overflow-hidden h-full">
          <div className="space-y-5 flex-1 flex flex-col overflow-hidden">
            
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">Target Lead</h3>
            
            {/* Search leads */}
            <div className="relative">
              <Search className="absolute left-3.5 top-3.5 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search leads..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-900 rounded-xl pl-10 pr-4 py-2.5 text-xs text-slate-300 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            {/* Leads list */}
            <div className="flex-1 overflow-y-auto space-y-2 pr-1">
              {loadingLeads ? (
                <div className="text-center py-12">
                  <RefreshCw className="w-6 h-6 text-indigo-400 animate-spin mx-auto mb-2" />
                  <p className="text-xs text-slate-500">Loading leads...</p>
                </div>
              ) : filteredLeads.length === 0 ? (
                <div className="text-center py-12 text-slate-500 text-xs">
                  No leads found.
                </div>
              ) : (
                filteredLeads.map((l) => {
                  const isSelected = selectedLead?.id === l.id;
                  return (
                    <button
                      key={l.id}
                      onClick={() => setSelectedLead(l)}
                      className={`w-full text-left p-3.5 rounded-xl border transition flex flex-col gap-1 ${
                        isSelected 
                          ? "bg-indigo-600/20 border-indigo-500/50 text-white" 
                          : "bg-slate-900/40 border-slate-800/60 hover:bg-slate-800/40 text-slate-300"
                      }`}
                    >
                      <div className="flex justify-between items-center w-full">
                        <span className="font-bold text-xs truncate">@{l.username}</span>
                        <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded border ${
                          l.intent === "HIGH_INTENT" 
                            ? "bg-rose-500/10 text-rose-400 border-rose-500/20" 
                            : "bg-slate-800 text-slate-400 border-slate-700/60"
                        }`}>
                          {l.intent === "HIGH_INTENT" ? "HIGH" : "MEDIUM"}
                        </span>
                      </div>
                      <p className="text-[10px] text-slate-500 truncate mt-0.5">
                        "{l.reply || "Inquired about product"}"
                      </p>
                    </button>
                  );
                })
              )}
            </div>

            {/* Product selection */}
            {products.length > 0 && (
              <div className="border-t border-slate-800/80 pt-4 space-y-2.5">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Target Product</label>
                <select
                  onChange={(e) => setSelectedProduct(products.find(p => p.id === e.target.value))}
                  value={selectedProduct?.id || ""}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2.5 text-slate-300 focus:outline-none focus:border-indigo-500 text-xs"
                >
                  {products.map(prod => (
                    <option key={prod.id} value={prod.id}>{prod.name} (Rs. {prod.price})</option>
                  ))}
                </select>
              </div>
            )}

          </div>
          
          <button 
            onClick={fetchInitialData} 
            className="w-full flex items-center justify-center gap-2 bg-slate-950 border border-slate-800/80 hover:bg-slate-900 text-xs font-bold text-slate-400 py-3 rounded-xl transition mt-4"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh Data
          </button>
        </div>

        {/* Right Pane: Unified Live Chat & State Machine Console */}
        <div className="lg:col-span-3 glass-panel rounded-2xl flex flex-col justify-between overflow-hidden h-full relative">
          
          {/* Top Bar Navigation: Autopilot Switch & Connection Details */}
          <div className="h-16 border-b border-slate-800 px-6 flex items-center justify-between bg-slate-900/40">
            {selectedLead ? (
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-emerald-600/10 border border-emerald-500/20 flex items-center justify-center">
                  <User className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <h4 className="font-bold text-sm text-white">@{selectedLead.username}</h4>
                  <p className="text-[10px] text-slate-400 truncate max-w-xs">
                    Original Query: "{selectedLead.reply || "Interested in ordering"}"
                  </p>
                </div>
              </div>
            ) : (
              <span className="text-slate-500 text-sm">No lead selected</span>
            )}

            {/* Connection badge & Autopilot Switch */}
            {selectedLead && (
              <div className="flex items-center gap-6">
                {/* Autopilot Switch */}
                <div className="flex items-center gap-2.5 border-r border-slate-800 pr-5">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">
                    AI Autopilot:
                  </span>
                  <button
                    onClick={handleToggleAutopilot}
                    disabled={updatingAutopilot}
                    className="focus:outline-none transition active:scale-95"
                  >
                    {autopilot ? (
                      <ToggleRight className="w-9 h-9 text-indigo-500" />
                    ) : (
                      <ToggleLeft className="w-9 h-9 text-slate-600" />
                    )}
                  </button>
                </div>

                {/* API / Sandbox Badge */}
                <div>
                  {isProduction ? (
                    <span className="flex items-center gap-1 text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      WhatsApp API Live
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-3 py-1 rounded-full">
                      <Sparkles className="w-3.5 h-3.5" />
                      Sandbox Active
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* LangGraph State Timeline Overlay (Active when Autopilot is enabled) */}
          {autopilot && selectedLead && (
            <div className="bg-slate-950/60 border-b border-slate-900 px-6 py-3 flex flex-wrap justify-between items-center gap-2 animate-fade-in">
              {aiSteps.map((step, idx) => {
                const isCurrent = aiState === step.key;
                const isDone = aiSteps.findIndex(s => s.key === aiState) > idx || aiState === "ORDER_CONFIRMED";
                return (
                  <div key={step.key} className="flex items-center gap-1.5">
                    <span className={`w-5 h-5 rounded-full flex items-center justify-center font-bold text-[9px] border ${
                      isCurrent 
                        ? "bg-indigo-600 border-indigo-500 text-white animate-pulse" 
                        : isDone 
                        ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" 
                        : "bg-slate-900 border-slate-800 text-slate-500"
                    }`}>
                      {isDone ? "✓" : idx + 1}
                    </span>
                    <span className={`text-[10px] font-semibold ${isCurrent ? "text-indigo-300" : isDone ? "text-slate-300" : "text-slate-600"}`}>
                      {step.label}
                    </span>
                    {idx < aiSteps.length - 1 && (
                      <span className="text-slate-800 font-bold ml-1">→</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Alert Bar indicating active mode */}
          {selectedLead && (
            <div className={`px-6 py-2.5 text-xs border-b font-medium flex items-center gap-2 ${
              autopilot 
                ? "bg-indigo-950/40 border-indigo-900/50 text-indigo-300" 
                : "bg-amber-950/40 border-amber-900/50 text-amber-300"
            }`}>
              {autopilot ? (
                <>
                  <Bot className="w-4 h-4 text-indigo-400" />
                  <span>AI Autopilot active: Sales agent responds automatically. Typing below lets you <b>test/simulate the customer</b> response.</span>
                </>
              ) : (
                <>
                  <User className="w-4 h-4 text-amber-400" />
                  <span>AI Autopilot paused: You are in manual takeover. Typing below sends <b>direct WhatsApp outreach</b>.</span>
                </>
              )}
            </div>
          )}

          {/* Messages Body (Unified Chat History Feed) */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-950/20">
            {!selectedLead ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-2">
                <MessageSquare className="w-12 h-12 text-slate-700" />
                <p className="text-sm font-semibold text-slate-400">Select a lead to start chatting</p>
                <p className="text-xs text-slate-600">Active leads will appear in the sidebar list.</p>
              </div>
            ) : loadingHistory && chatHistory.length === 0 ? (
              <div className="h-full flex items-center justify-center">
                <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin" />
              </div>
            ) : chatHistory.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-600 space-y-2">
                <MessageCircle className="w-10 h-10 text-slate-800" />
                <p className="text-xs italic">No messages sent yet. Send the first message to initiate outreach.</p>
              </div>
            ) : (
              chatHistory.map((msg, index) => {
                const isBusiness = msg.sender === "business";
                const isAi = msg.sender === "ai";
                
                return (
                  <div key={msg.id || index} className={`flex gap-3 max-w-[85%] ${isBusiness ? "ml-auto flex-row-reverse" : ""}`}>
                    
                    {/* Icon mapping */}
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-[10px] flex-shrink-0 ${
                      isBusiness 
                        ? "bg-indigo-600 text-white" 
                        : isAi 
                        ? "bg-indigo-500/10 border border-indigo-500/30 text-indigo-400" 
                        : "bg-slate-800 text-slate-400"
                    }`}>
                      {isBusiness ? "ME" : isAi ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                    </div>

                    <div className="space-y-1">
                      {/* Sender label */}
                      <span className={`text-[9px] font-bold block px-1 ${isBusiness ? "text-right text-indigo-400" : isAi ? "text-indigo-400" : "text-slate-500"}`}>
                        {isBusiness ? "You (Business Owner)" : isAi ? "AI Sales Assistant (Autopilot)" : "Customer"}
                      </span>

                      {/* Bubble content */}
                      <div className={`p-4 rounded-2xl text-sm leading-relaxed border ${
                        isBusiness 
                          ? "bg-indigo-600/10 border-indigo-500/25 text-slate-100" 
                          : isAi
                          ? "bg-slate-900 border-indigo-500/20 text-slate-200"
                          : "bg-slate-900 border-slate-800/80 text-slate-200"
                      }`}>
                        {msg.text}
                      </div>

                      {/* Timestamp */}
                      <span className="text-[8px] text-slate-600 block px-1 text-right">
                        {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
            
            {/* UPI simulated QR overlay (AI Mode only) */}
            {autopilot && aiState === "PAYMENT" && activeOrderId && (
              <div className="flex gap-3 max-w-[80%]">
                <div className="w-8 h-8 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="p-5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-slate-200 text-sm space-y-4 shadow-lg">
                  <h4 className="font-bold text-emerald-400 flex items-center gap-1.5">
                    <DollarSign className="w-5 h-5" />
                    Simulated UPI Payment Sandbox
                  </h4>
                  <p className="text-xs text-slate-400">
                    Order ID: <span className="font-mono text-slate-300">{activeOrderId}</span><br />
                    Amount: <span className="font-bold text-slate-300">Rs. {selectedProduct?.price}.00</span>
                  </p>
                  <button
                    onClick={handleSimulatePayment}
                    className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 rounded-xl shadow-lg transition"
                  >
                    Click to Pay with UPI (Success Callback)
                  </button>
                </div>
              </div>
            )}

            {/* Sending Loading indicator */}
            {sendingMessage && (
              <div className={`flex gap-3 max-w-[80%] ${!autopilot ? "ml-auto flex-row-reverse" : ""}`}>
                <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center flex-shrink-0 font-bold text-xs">
                  {autopilot ? <Bot className="w-4 h-4 animate-spin" /> : "ME"}
                </div>
                <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 text-slate-400 text-sm italic">
                  {autopilot ? "AI Agent is typing..." : "Sending..."}
                </div>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Dynamic Chat Form Input */}
          <form onSubmit={handleSendMessage} className="h-20 border-t border-slate-800 px-6 flex items-center gap-3 bg-slate-900/30">
            <input
              type="text"
              placeholder={
                !selectedLead 
                  ? "Please select a lead first"
                  : autopilot 
                  ? "Type message as customer to test AI autopilot response..."
                  : `Type message as business owner to outreach @${selectedLead.username}...`
              }
              value={messageText}
              onChange={(e) => setMessageText(e.target.value)}
              className="flex-1 bg-slate-950 border border-slate-900 rounded-xl px-4 py-3.5 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-sm"
              disabled={!selectedLead || sendingMessage}
            />
            <button
              type="submit"
              className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-900 text-white font-bold p-3.5 rounded-xl shadow-lg transition"
              disabled={!selectedLead || !messageText.trim() || sendingMessage}
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

        </div>

      </div>
    </div>
  );
}
