// frontend/app/live-chat/page.tsx
"use client";

import { useEffect, useState, useRef, Suspense } from "react";
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
  ToggleLeft,
  ToggleRight,
  Paperclip,
  FileText,
  Play,
  Volume2,
  Image as ImageIcon,
  Youtube,
  Trash2
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DEFAULT_TENANT = "00000000-0000-0000-0000-000000000000";

function LiveChatContent() {
  const searchParams = useSearchParams();
  const leadIdParam = searchParams.get("lead_id");

  // CRM/Conversations states
  const [conversations, setConversations] = useState<any[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<any>(null);
  const [products, setProducts] = useState<any[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<any>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [loadingConversations, setLoadingConversations] = useState(true);
  
  // Autopilot toggle state
  const [autopilot, setAutopilot] = useState(true);
  const [updatingAutopilot, setUpdatingAutopilot] = useState(false);

  // Chat History states
  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [sendingMessage, setSendingMessage] = useState(false);
  const [messageText, setMessageText] = useState("");
  const [isProduction, setIsProduction] = useState(false); 

  // AI Pipeline tracking states
  const [aiState, setAiState] = useState("WELCOME");
  const [activeOrderId, setActiveOrderId] = useState<string | null>(null);
  
  // Message editing states
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState("");

  const chatEndRef = useRef<HTMLDivElement>(null);

  const aiSteps = [
    { key: "WELCOME", label: "Welcome" },
    { key: "PRODUCT_INFO", label: "Product Specs" },
    { key: "QA_LOOP", label: "Objection Q&A" },
    { key: "ADDRESS_COLLECTION", label: "Address Collection" },
    { key: "PAYMENT", label: "Payment Request" },
    { key: "ORDER_CONFIRMED", label: "Confirmed" }
  ];

  // 1. Fetch conversations and products
  async function fetchConversations() {
    setLoadingConversations(true);
    try {
      // Fetch conversations from clean architecture endpoint
      const res = await fetch(`${API_BASE}/conversations?tenant_id=${DEFAULT_TENANT}`);
      const data = await res.json();
      if (res.ok && data.status === "success" && data.data) {
        setConversations(data.data);
        
        // If there are conversations, select one matching lead_id param or default to first
        if (data.data.length > 0) {
          let matched = null;
          if (leadIdParam) {
            matched = data.data.find((c: any) => String(c.lead_id) === String(leadIdParam));
          }
          const defaultSelect = matched || data.data[0];
          setSelectedConversation(defaultSelect);
          setAutopilot(defaultSelect.ai_enabled !== false);
          setAiState(defaultSelect.state || "WELCOME");
        }
      }
    } catch (err) {
      console.error("Failed to load initial conversation data:", err);
    } finally {
      setLoadingConversations(false);
    }
  }

  // Fetch all products from master catalog and pre-select the video's linked product
  async function fetchProductsForVideo(videoId?: string) {
    try {
      // 1. Fetch full product catalog from master product service
      const prodRes = await fetch(`${API_BASE}/product`);
      let allCatalogProducts: any[] = [];
      if (prodRes.ok) {
        allCatalogProducts = await prodRes.json();
      }

      // 2. Fetch specific products for this video if available
      let videoProducts: any[] = [];
      if (videoId) {
        try {
          const vRes = await fetch(`${API_BASE}/youtube/videos/${videoId}/products`);
          const vData = await vRes.json();
          if (vRes.ok && vData.status === "success" && vData.data) {
            videoProducts = vData.data;
          }
        } catch (e) {
          console.warn("Error fetching video specific products:", e);
        }
      }

      // Merge video products with all catalog products, deduplicating strictly by product name
      const excludedKw = ["saree", "fabric", "paint", "emulsion", "cardamom", "coconut", "oil"];
      const isAllowed = (key: string) => key && !excludedKw.some(kw => key.includes(kw));

      const mergedMap = new Map<string, any>();
      videoProducts.forEach(p => {
        const nameKey = (p.name || "").toLowerCase().trim();
        if (isAllowed(nameKey)) {
          mergedMap.set(nameKey, p);
        }
      });
      allCatalogProducts.forEach(p => {
        const nameKey = (p.name || "").toLowerCase().trim();
        if (isAllowed(nameKey)) {
          if (!mergedMap.has(nameKey)) {
            mergedMap.set(nameKey, p);
          }
        }
      });

      const finalProductList = Array.from(mergedMap.values());
      setProducts(finalProductList);

      if (finalProductList.length > 0) {
        // Pre-select the video product if found, else default to first item
        const defaultSel = videoProducts.length > 0 ? videoProducts[0] : finalProductList[0];
        setSelectedProduct(defaultSel);
      } else {
        setSelectedProduct(null);
      }
    } catch (err) {
      console.error("Failed to fetch products for live chat:", err);
      setProducts([]);
      setSelectedProduct(null);
    }
  }

  // 2. Fetch messages for the selected conversation
  async function fetchMessages(conversationId: string, silent = false) {
    if (!silent) setLoadingHistory(true);
    try {
      const res = await fetch(`${API_BASE}/conversations/${conversationId}/messages`);
      const data = await res.json();
      if (res.ok && data.status === "success" && data.data) {
        setChatHistory(data.data);
        
        // Resolve active order from message contents
        const paymentMsg = [...data.data].reverse().find(m => m.sender_type === "ai" && m.content.includes("order_id="));
        if (paymentMsg) {
          const match = paymentMsg.content.match(/order_id=([^&? )]+)/);
          if (match) {
            setActiveOrderId(match[1]);
          }
        }
      }
    } catch (err) {
      console.error("Failed to fetch messages:", err);
    } finally {
      if (!silent) setLoadingHistory(false);
    }
  }

  // 3. Mount and check active connection badge (polling evolution api gateway status)
  async function checkLiveStatus() {
    try {
      const res = await fetch(`${API_BASE}/whatsapp/instances?tenant_id=${DEFAULT_TENANT}`);
      if (res.ok) {
        const data = await res.json();
        if (data.status === "success" && data.data && data.data.length > 0) {
          const active = data.data[0];
          const statusRes = await fetch(`${API_BASE}/whatsapp/${active.id}/status`);
          const statusData = await statusRes.json();
          if (statusRes.ok && statusData.status === "success") {
            setIsProduction(statusData.connection_status === "connected");
          }
        } else {
          setIsProduction(false);
        }
      }
    } catch (e) {
      console.warn("Connection provider offline. Defaulting badge to sandbox.");
    }
  }

  useEffect(() => {
    fetchConversations();
    checkLiveStatus();
  }, [leadIdParam]);

  // Handle switching active conversation thread
  useEffect(() => {
    if (selectedConversation) {
      setAutopilot(selectedConversation.ai_enabled !== false);
      setAiState(selectedConversation.state || "WELCOME");
      fetchMessages(selectedConversation.id);
      setActiveOrderId(null);
      
      // Load products dynamically for the conversation's video
      const videoId = selectedConversation.lead?.video_id;
      fetchProductsForVideo(videoId);
    } else {
      setChatHistory([]);
      setProducts([]);
      setSelectedProduct(null);
    }
  }, [selectedConversation]);

  // Scroll viewport down on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  // 4. WebSocket setup for real-time dashboard events
  useEffect(() => {
    if (!selectedConversation) return;

    const ws_protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws_host = API_BASE.replace("http://", "").replace("https://", "");
    
    // Connect to tenant websocket
    const socket = new WebSocket(`${ws_protocol}//${ws_host}/ws?tenant_id=${DEFAULT_TENANT}`);
    
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        const eventType = payload.event;
        const eventData = payload.data;
        
        if (
          eventType === "message.created" || 
          eventType === "message.sent" || 
          eventType === "message.delivered" || 
          eventType === "message.failed" ||
          eventType === "message.read"
        ) {
          // If message is for the currently viewed conversation
          if (eventData.conversation_id === selectedConversation.id) {
            setChatHistory(prev => {
              if (prev.some(m => m.id === eventData.id)) {
                // Replace existing message to update its metadata / status
                return prev.map(m => m.id === eventData.id ? eventData : m);
              }
              return [...prev, eventData];
            });
            
            // Extract order ID if AI generated checkout link
            if (eventData.sender_type === "ai" && eventData.content.includes("order_id=")) {
              const match = eventData.content.match(/order_id=([^&? )]+)/);
              if (match) setActiveOrderId(match[1]);
            }
          }
        } else if (eventType === "conversation.updated") {
          if (eventData.id === selectedConversation.id) {
            setAutopilot(eventData.ai_enabled);
            setAiState(eventData.state || "WELCOME");
          }
          // Sync changes in lists
          setConversations(prev => prev.map(c => c.id === eventData.id ? eventData : c));
        } else if (eventType === "conversation.created") {
          setConversations(prev => {
            if (prev.some(c => c.id === eventData.id)) return prev;
            return [eventData, ...prev];
          });
        } else if (eventType === "conversation.deleted") {
          setConversations(prev => prev.filter(c => c.id !== eventData.id));
          if (selectedConversation?.id === eventData.id) {
            setSelectedConversation(null);
            setChatHistory([]);
          }
        } else if (eventType === "conversations.cleared") {
          setConversations([]);
          setSelectedConversation(null);
          setChatHistory([]);
        }
      } catch (err) {
        console.error("WS parse error:", err);
      }
    };

    return () => socket.close();
  }, [selectedConversation]);

  // 5. Toggle AI Autopilot (Takeover toggle)
  async function handleToggleAutopilot() {
    if (!selectedConversation || updatingAutopilot) return;
    const nextAutopilot = !autopilot;
    setUpdatingAutopilot(true);
    try {
      const res = await fetch(`${API_BASE}/conversations/${selectedConversation.id}/toggle-autopilot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ai_enabled: nextAutopilot
        })
      });
      if (res.ok) {
        setAutopilot(nextAutopilot);
        setConversations(prev => prev.map(c => c.id === selectedConversation.id ? { ...c, ai_enabled: nextAutopilot } : c));
      }
    } catch (err) {
      console.error("Failed to toggle autopilot:", err);
    } finally {
      setUpdatingAutopilot(false);
    }
  }

  // 6. Simulate Incoming Customer Message (Sandbox helper)
  async function handleSimulateCustomerMessage() {
    if (!selectedConversation || sendingMessage) return;
    setSendingMessage(true);
    try {
      // Simulate Evolution Webhook payload
      const mockPayload = {
        event: "messages.upsert",
        instance: "kochi_farm_whatsapp",
        data: {
          key: {
            remoteJid: `${selectedConversation.customer_phone}@s.whatsapp.net`,
            fromMe: false,
            id: "msg_" + Math.random().toString(36).substr(2, 9)
          },
          pushName: "Customer Sandbox",
          message: {
            conversation: "Hi, I want to order a Fiddle Leaf Fig plant. What is the price and shipping?"
          },
          messageType: "conversation"
        }
      };

      await fetch(`${API_BASE}/webhooks/whatsapp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(mockPayload)
      });
    } catch (err) {
      console.error("Failed to simulate message:", err);
    } finally {
      setSendingMessage(false);
    }
  }

  // 7. Send Agent Outbound Message
  async function handleSendMessage(e: React.FormEvent) {
    e.preventDefault();
    if (!messageText.trim() || !selectedConversation || sendingMessage) return;

    const currentText = messageText;
    setMessageText("");
    setSendingMessage(true);

    try {
      const res = await fetch(`${API_BASE}/conversations/${selectedConversation.id}/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: currentText,
          message_type: "text"
        })
      });
      if (res.ok) {
        // Toggle autopilot to manual mode locally to match server side takeover rules
        if (autopilot) {
          setAutopilot(false);
          setConversations(prev => prev.map(c => c.id === selectedConversation.id ? { ...c, ai_enabled: false } : c));
        }
      }
    } catch (err) {
      console.error("Failed to send message:", err);
    } finally {
      setSendingMessage(false);
    }
  }

  // UPI payment success simulation
  async function handleSimulatePayment() {
    if (!activeOrderId) return;
    try {
      await fetch(`${API_BASE}/payment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_id: activeOrderId,
          status: "paid"
        })
      });
    } catch (err) {
      console.error("Simulated payment failed:", err);
    }
  }

  // 8. Clear All Chats (Local database only)
  async function handleClearAllChats() {
    const confirmed = window.confirm("Are you sure you want to clear all chat conversations? This will delete all local chat history and messages permanently. This action cannot be undone.");
    if (!confirmed) return;

    try {
      const res = await fetch(`${API_BASE}/conversations?tenant_id=${DEFAULT_TENANT}`, {
        method: "DELETE"
      });
      if (res.ok) {
        setConversations([]);
        setSelectedConversation(null);
        setChatHistory([]);
      } else {
        alert("Failed to clear conversations.");
      }
    } catch (err) {
      console.error("Error clearing chats:", err);
      alert("Error clearing chats.");
    }
  }

  // 9. Delete Individual Chat (Local database only)
  async function handleDeleteChat(conversationId: string, phone: string) {
    const confirmed = window.confirm(`Are you sure you want to delete the chat conversation with +${phone}? All messages will be permanently deleted from the local database.`);
    if (!confirmed) return;

    try {
      const res = await fetch(`${API_BASE}/conversations/${conversationId}`, {
        method: "DELETE"
      });
      if (res.ok) {
        setConversations(prev => prev.filter(c => c.id !== conversationId));
        if (selectedConversation?.id === conversationId) {
          setSelectedConversation(null);
          setChatHistory([]);
        }
      } else {
        alert("Failed to delete conversation.");
      }
    } catch (err) {
      console.error("Error deleting chat:", err);
      alert("Error deleting chat.");
    }
  }

  // 9b. Reset Autopilot Session state (Keeps history, resets AI memory & checkout stage)
  async function handleResetConversation() {
    if (!selectedConversation) return;
    const confirmed = window.confirm("Are you sure you want to reset the conversation state, AI memory, and order progress for this customer? This will clear all AI memory context but preserve chat message history.");
    if (!confirmed) return;

    try {
      const res = await fetch(`${API_BASE}/conversations/${selectedConversation.id}/reset`, {
        method: "POST"
      });
      if (res.ok) {
        setConversations(prev => prev.map(c => c.id === selectedConversation.id ? { ...c, state: "WELCOME", state_metadata: {} } : c));
        setSelectedConversation((prev: any) => prev ? { ...prev, state: "WELCOME", state_metadata: {} } : null);
        setAiState("WELCOME");
        alert("Conversation session reset successfully!");
      } else {
        alert("Failed to reset conversation.");
      }
    } catch (err) {
      console.error("Error resetting conversation:", err);
      alert("Error resetting conversation.");
    }
  }

  // 10. Edit Message Helpers
  function handleStartEditMessage(msg: any) {
    setEditingMessageId(msg.id);
    setEditingText(msg.content);
  }

  async function handleSaveEditMessage(messageId: string) {
    if (!editingText.trim()) return;
    try {
      const res = await fetch(`${API_BASE}/conversations/messages/${messageId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: editingText })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.status === "success" && data.data) {
          // Update chat history locally
          setChatHistory(prev => prev.map(m => m.id === messageId ? data.data : m));
          setEditingMessageId(null);
          setEditingText("");
        }
      } else {
        alert("Failed to save edited message.");
      }
    } catch (err) {
      console.error("Error editing message:", err);
      alert("Error editing message.");
    }
  }

  // Filter conversations
  const filteredConversations = conversations.filter(c => 
    c.customer_phone.includes(searchQuery) || (c.lead_id && String(c.lead_id).includes(searchQuery))
  );

  return (
    <div className="space-y-6">
      {/* Top Banner Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            WhatsApp Live Chat
          </h1>
          <p className="text-slate-400 mt-2">
            A single unified console to chat with clients, monitor active AI sales agent autopilots, and manually take over conversations.
          </p>
        </div>
        
        {selectedProduct && (
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-300">
            <Package className="w-4 h-4 text-indigo-400" />
            Selling: <span className="font-bold text-white">{selectedProduct.name}</span>
          </div>
        )}
      </div>

      {/* Workspace Panel Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[700px]">
        
        {/* Left Side Navigation: Inbox Leads List */}
        <div className="glass-panel rounded-2xl p-4 flex flex-col justify-between overflow-hidden h-full">
          <div className="space-y-5 flex-1 flex flex-col overflow-hidden">
            
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider">Inbox Threads</h3>
            
            <div className="relative">
              <Search className="absolute left-3.5 top-3.5 w-4 h-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search phone numbers..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-slate-950 border border-slate-900 rounded-xl pl-10 pr-4 py-2.5 text-xs text-slate-300 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            {/* Conversation Feed Items */}
            <div className="flex-1 overflow-y-auto space-y-2 pr-1">
              {loadingConversations ? (
                <div className="text-center py-12">
                  <RefreshCw className="w-6 h-6 text-indigo-400 animate-spin mx-auto mb-2" />
                  <p className="text-xs text-slate-500">Loading inbox...</p>
                </div>
              ) : filteredConversations.length === 0 ? (
                <div className="text-center py-12 text-slate-500 text-xs">
                  No active chats.
                </div>
              ) : (
                filteredConversations.map((c) => {
                  const isSelected = selectedConversation?.id === c.id;
                  return (
                    <button
                      key={c.id}
                      onClick={() => setSelectedConversation(c)}
                      className={`w-full text-left p-3.5 rounded-xl border transition flex flex-col gap-1 ${
                        isSelected 
                          ? "bg-indigo-600/20 border-indigo-500/50 text-white" 
                          : "bg-slate-900/40 border-slate-800/60 hover:bg-slate-800/40 text-slate-300"
                      }`}
                    >
                      <div className="flex justify-between items-center w-full">
                        <span className="font-bold text-xs truncate">+{c.customer_phone}</span>
                        <div className="flex items-center gap-1.5">
                          <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded border ${
                            c.status === "open"
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/25" 
                              : "bg-slate-800 text-slate-400 border-slate-700/60"
                          }`}>
                            {c.status.toUpperCase()}
                          </span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteChat(c.id, c.customer_phone);
                            }}
                            className="text-slate-500 hover:text-rose-400 transition p-0.5"
                            title="Delete Chat"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                      <div className="flex justify-between items-center text-[10px] text-slate-500 mt-1">
                        <span>Channel: {c.channel}</span>
                        {c.ai_enabled ? (
                          <span className="text-indigo-400 flex items-center gap-0.5 font-bold">🤖 AI</span>
                        ) : (
                          <span className="text-amber-400 flex items-center gap-0.5 font-bold">👤 Human</span>
                        )}
                      </div>
                    </button>
                  );
                })
              )}
            </div>

            {/* Product catalog display */}
            <div className="border-t border-slate-800/80 pt-4 space-y-2.5">
              <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Target Catalog Product</label>
              {products.length > 0 ? (
                <select
                  onChange={(e) => setSelectedProduct(products.find(p => p.id === e.target.value))}
                  value={selectedProduct?.id || ""}
                  className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2.5 text-slate-300 focus:outline-none focus:border-indigo-500 text-xs"
                >
                  {products.map(prod => (
                    <option key={prod.id} value={prod.id}>{prod.name} (Rs. {prod.price})</option>
                  ))}
                </select>
              ) : (
                <div className="text-[11px] text-amber-400 bg-amber-950/20 border border-amber-900/30 px-3 py-2 rounded-xl text-center font-medium">
                  No products are linked to this monitored video.
                </div>
              )}
            </div>

          </div>
          
          <div className="flex gap-2 mt-4">
            <button 
              onClick={fetchConversations} 
              className="flex-1 flex items-center justify-center gap-2 bg-slate-950 border border-slate-800/80 hover:bg-slate-900 text-xs font-bold text-slate-400 py-3 rounded-xl transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh
            </button>
            <button 
              onClick={handleClearAllChats} 
              className="flex-1 flex items-center justify-center gap-2 bg-rose-500/10 border border-rose-500/25 hover:bg-rose-500/20 text-xs font-bold text-rose-450 py-3 rounded-xl transition"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Clear Chats
            </button>
          </div>
        </div>

        {/* Right Pane: Unified Chat Terminal */}
        <div className="lg:col-span-3 glass-panel rounded-2xl flex flex-col justify-between overflow-hidden h-full relative">
          
          {/* Header controls */}
          <div className="h-16 border-b border-slate-800 px-6 flex items-center justify-between bg-slate-900/40">
            {selectedConversation ? (
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-full bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center">
                  <User className="w-5 h-5 text-indigo-400" />
                </div>
                <div>
                  <h4 className="font-bold text-sm text-white">+{selectedConversation.customer_phone}</h4>
                  <p className="text-[10px] text-slate-400">Active conversation session ID: {selectedConversation.id.substring(0,8)}...</p>
                </div>
              </div>
            ) : (
              <span className="text-slate-500 text-sm">No thread selected</span>
            )}

            {/* AI toggle switches */}
            {selectedConversation && (
              <div className="flex items-center gap-6">
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

                {autopilot && !isProduction && (
                  <button
                    type="button"
                    onClick={handleSimulateCustomerMessage}
                    disabled={sendingMessage}
                    className="flex items-center gap-1.5 text-[10px] font-bold bg-indigo-600 hover:bg-indigo-500 text-white border border-indigo-500/20 px-3.5 py-2 rounded-xl transition active:scale-95 disabled:opacity-50"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    Simulate Customer Inbound
                  </button>
                )}

                {selectedConversation && (
                  <button
                    type="button"
                    onClick={handleResetConversation}
                    className="flex items-center gap-1.5 text-[10px] font-bold bg-rose-950/20 border border-rose-500/30 hover:bg-rose-900/30 text-rose-400 px-3.5 py-2 rounded-xl transition active:scale-95"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    Reset Session
                  </button>
                )}

                <div>
                  {isProduction ? (
                    <span className="flex items-center gap-1 text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      Evolution API Live
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

          {/* LangGraph State Machine timeline */}
          {autopilot && selectedConversation && (
            <div className="bg-slate-950/60 border-b border-slate-900 px-6 py-3 flex flex-wrap justify-between items-center gap-2">
              {aiSteps.map((step, idx) => {
                const isCurrent = aiState === step.key;
                const isDone = aiSteps.findIndex(s => s.key === aiState) > idx || aiState === "ORDER_CONFIRMED" || aiState === "COMPLETE";
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

          {/* Autopilot Alerts banner */}
          {selectedConversation && (
            <div className={`px-6 py-2.5 text-xs border-b font-medium flex items-center gap-2 ${
              autopilot 
                ? "bg-indigo-950/40 border-indigo-900/50 text-indigo-300" 
                : "bg-amber-950/40 border-amber-900/50 text-amber-300"
            }`}>
              {autopilot ? (
                <>
                  <Bot className="w-4 h-4 text-indigo-400" />
                  <span>AI Autopilot active: responding automatically. Manual replies will switch session to <b>takeover mode</b>.</span>
                </>
              ) : (
                <>
                  <User className="w-4 h-4 text-amber-400" />
                  <span>Autopilot paused (Takeover): messages route directly. Click switch to restore AI loop.</span>
                </>
              )}
            </div>
          )}

          {/* YouTube lead context banner */}
          {selectedConversation && selectedConversation.lead && (
            <div className="px-6 py-3 bg-indigo-950/20 border-b border-indigo-900/40 text-xs flex items-start gap-3">
              <Youtube className="w-5 h-5 text-rose-500 mt-0.5 flex-shrink-0" />
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-200">YouTube Marketing Funnel</span>
                  {selectedConversation.lead.intent && (
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${
                      selectedConversation.lead.intent === "HIGH_INTENT"
                        ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                        : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                    }`}>
                      {selectedConversation.lead.intent.replace("_", " ")}
                    </span>
                  )}
                </div>
                <p className="text-slate-300">
                  Acquired from commenter <span className="font-semibold text-indigo-400">@{selectedConversation.lead.username}</span> on video <span className="italic text-slate-200">"{selectedConversation.lead.video_title}"</span>
                </p>
                {selectedConversation.lead.comment_text && (
                  <p className="text-slate-400 italic text-[11px] bg-slate-950/40 border border-slate-900 rounded-lg p-2.5 mt-1.5 leading-relaxed">
                    Source Comment: "{selectedConversation.lead.comment_text}"
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Messages Body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-slate-950/20">
            {!selectedConversation ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-2">
                <MessageSquare className="w-12 h-12 text-slate-700" />
                <p className="text-sm font-semibold text-slate-400">Select a chat from the sidebar</p>
                <p className="text-xs text-slate-600">Active conversations appear in the left-hand menu.</p>
              </div>
            ) : loadingHistory && chatHistory.length === 0 ? (
              <div className="h-full flex items-center justify-center">
                <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin" />
              </div>
            ) : chatHistory.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-600 space-y-2">
                <MessageCircle className="w-10 h-10 text-slate-800" />
                <p className="text-xs italic">Awaiting message sync. Send outbound outreach below.</p>
              </div>
            ) : (
              chatHistory.map((msg, index) => {
                const isAgent = msg.sender_type === "agent";
                const isAi = msg.sender_type === "ai";
                const isSystem = msg.sender_type === "system";

                if (isSystem) {
                  return (
                    <div key={msg.id || index} className="flex justify-center w-full my-2">
                      <div className="bg-slate-900/80 border border-slate-800 text-xs text-slate-400 py-1.5 px-4 rounded-full max-w-lg shadow flex items-center gap-2">
                        <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
                        <span>{msg.content}</span>
                      </div>
                    </div>
                  );
                }
                
                return (
                  <div key={msg.id || index} className={`flex gap-3 max-w-[85%] ${isAgent ? "ml-auto flex-row-reverse" : ""}`}>
                    
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-[10px] flex-shrink-0 ${
                      isAgent 
                        ? "bg-indigo-600 text-white" 
                        : isAi 
                        ? "bg-indigo-500/10 border border-indigo-500/30 text-indigo-400" 
                        : "bg-slate-800 text-slate-400"
                    }`}>
                      {isAgent ? "ME" : isAi ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                    </div>

                    <div className="space-y-1">
                      <span className={`text-[9px] font-bold block px-1 ${isAgent ? "text-right text-indigo-400" : isAi ? "text-indigo-400" : "text-slate-500"}`}>
                        {isAgent ? "You (Agent)" : isAi ? "AI Assistant (Autopilot)" : "Customer"}
                      </span>

                      {/* Message Bubble rendering media/text */}
                      <div className={`p-4 rounded-2xl text-sm leading-relaxed border space-y-2 ${
                        isAgent 
                          ? "bg-indigo-600/10 border-indigo-500/25 text-slate-100" 
                          : isAi
                          ? "bg-slate-900 border-indigo-500/20 text-slate-200"
                          : "bg-slate-900 border-slate-800/80 text-slate-200"
                      }`}>
                        {msg.message_type === "text" && (
                          editingMessageId === msg.id ? (
                            <div className="space-y-2 min-w-[200px]">
                              <textarea
                                value={editingText}
                                onChange={(e) => setEditingText(e.target.value)}
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                                rows={3}
                              />
                              <div className="flex justify-end gap-1.5">
                                <button
                                  type="button"
                                  onClick={() => setEditingMessageId(null)}
                                  className="px-2.5 py-1 text-[10px] font-bold bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition"
                                >
                                  Cancel
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleSaveEditMessage(msg.id)}
                                  className="px-2.5 py-1 text-[10px] font-bold bg-indigo-600 hover:bg-indigo-500 text-white rounded transition"
                                >
                                  Save
                                </button>
                              </div>
                            </div>
                          ) : (
                            <p>{msg.content}</p>
                          )
                        )}

                        {msg.message_type === "image" && (
                          <div className="space-y-1">
                            <img src={msg.content} alt="WhatsApp Image attachment" className="rounded-lg max-h-48 max-w-full block border border-slate-800 shadow" />
                            {msg.metadata?.caption && <p className="text-xs text-slate-400 italic">{msg.metadata.caption}</p>}
                          </div>
                        )}

                        {msg.message_type === "video" && (
                          <div className="space-y-1">
                            <video src={msg.content} controls className="rounded-lg max-h-48 max-w-full block border border-slate-800 shadow" />
                            {msg.metadata?.caption && <p className="text-xs text-slate-400 italic">{msg.metadata.caption}</p>}
                          </div>
                        )}

                        {msg.message_type === "audio" && (
                          <audio src={msg.content} controls className="block w-full max-w-xs scale-90 origin-left" />
                        )}

                        {msg.message_type === "document" && (
                          <a 
                            href={msg.content} 
                            target="_blank" 
                            rel="noopener noreferrer" 
                            className="flex items-center gap-2 p-2 bg-slate-950 hover:bg-slate-900 rounded-lg text-xs text-indigo-400 border border-slate-800"
                          >
                            <FileText className="w-4 h-4 flex-shrink-0" />
                            <span className="truncate">{msg.metadata?.fileName || "Download Document"}</span>
                          </a>
                        )}
                      </div>

                      <div className="flex items-center justify-between gap-3 px-1">
                        {msg.message_type === "text" && editingMessageId !== msg.id && (
                          <button
                            onClick={() => handleStartEditMessage(msg)}
                            className="text-[10px] text-slate-500 hover:text-indigo-400 transition"
                          >
                            Edit
                          </button>
                        )}
                        {msg.metadata?.edited && (
                          <span 
                            className="text-[9px] text-slate-500 italic block cursor-help" 
                            title={
                              msg.metadata.edit_history && msg.metadata.edit_history.length > 0
                                ? `Original: "${msg.metadata.edit_history[0].content}" at ${new Date(msg.metadata.edit_history[0].edited_at).toLocaleTimeString()}`
                                : "Edited"
                            }
                          >
                            (edited)
                          </span>
                        )}
                        {msg.metadata?.status === "failed" && (
                          <span className="text-[9px] text-rose-500 font-semibold max-w-[220px] truncate block" title={msg.metadata.error}>
                            ⚠️ {msg.metadata.error || "Delivery failed"}
                          </span>
                        )}
                        <span className="text-[8px] text-slate-600 block ml-auto text-right">
                          {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
            
            {/* Payment simulator sandbox card */}
            {autopilot && activeOrderId && (aiState === "PAYMENT" || chatHistory.some(m => m.sender_type === "ai" && m.content.includes("order_id="))) && (
              <div className="flex gap-3 max-w-[80%]">
                <div className="w-8 h-8 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="p-5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-slate-200 text-sm space-y-4 shadow-lg">
                  <h4 className="font-bold text-emerald-400 flex items-center gap-1.5">
                    <DollarSign className="w-5 h-5" />
                    Simulated UPI Checkout Link
                  </h4>
                  <p className="text-xs text-slate-400">
                    Order ID: <span className="font-mono text-slate-300">{activeOrderId}</span><br />
                    Amount: <span className="font-bold text-slate-300">Rs. {selectedProduct?.price}.00</span>
                  </p>
                  <button
                    onClick={handleSimulatePayment}
                    className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 rounded-xl shadow-lg transition"
                  >
                    Simulate Payment Completion Callback
                  </button>
                </div>
              </div>
            )}

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

          {/* Form input field */}
          <form onSubmit={handleSendMessage} className="h-20 border-t border-slate-800 px-6 flex items-center gap-3 bg-slate-900/30">
            <input
              type="text"
              placeholder={
                !selectedConversation 
                  ? "Please select a conversation"
                  : autopilot 
                  ? `Reply to +${selectedConversation.customer_phone} (AI Autopilot will pause)...`
                  : `Reply to +${selectedConversation.customer_phone}...`
              }
              value={messageText}
              onChange={(e) => setMessageText(e.target.value)}
              className="flex-1 bg-slate-950 border border-slate-900 rounded-xl px-4 py-3.5 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-sm"
              disabled={!selectedConversation || sendingMessage}
            />
            <button
              type="submit"
              className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-900 text-white font-bold p-3.5 rounded-xl shadow-lg transition"
              disabled={!selectedConversation || !messageText.trim() || sendingMessage}
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

        </div>

      </div>
    </div>
  );
}

export default function UnifiedLiveChatPage() {
  return (
    <Suspense fallback={<div className="text-center py-12 text-slate-400 text-sm">Loading Live Chat Console...</div>}>
      <LiveChatContent />
    </Suspense>
  );
}
