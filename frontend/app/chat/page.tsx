// frontend/app/chat/page.tsx
"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { 
  MessageCircle, 
  Send, 
  Sparkles, 
  DollarSign, 
  CheckCircle, 
  User, 
  Bot,
  Building2
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function ChatContent() {
  const searchParams = useSearchParams();
  const leadIdParam = searchParams.get("lead_id");

  const [leadList, setLeadList] = useState<any[]>([]);
  const [selectedLead, setSelectedLead] = useState<any>(null);
  const [productList, setProductList] = useState<any[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<any>(null);

  const [chatHistory, setChatHistory] = useState<any[]>([]);
  const [userMsg, setUserMsg] = useState("");
  const [currentState, setCurrentState] = useState("WELCOME");
  const [loading, setLoading] = useState(false);
  const [activeOrderId, setActiveOrderId] = useState<string | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);

  const steps = [
    { key: "WELCOME", label: "Welcome" },
    { key: "PRODUCT_INFO", label: "Product Info" },
    { key: "QA_LOOP", label: "objection Q&A" },
    { key: "ADDRESS_COLLECTION", label: "Address Collection" },
    { key: "PAYMENT", label: "Payment Request" },
    { key: "ORDER_CONFIRMED", label: "Confirmed" }
  ];

  const fetchInitialData = async () => {
    try {
      // Mock / Fetch Leads
      const mockLeads = [
        { id: "1", username: "rahul_sharma", intent: "HIGH_INTENT", language: "Hindi", status: "new" },
        { id: "2", username: "priya_menon", intent: "HIGH_INTENT", language: "Malayalam", status: "contacting" },
        { id: "3", username: "karthik_v", intent: "MEDIUM_INTENT", language: "Tamil", status: "qualified" },
        { id: "4", username: "suresh_kumar", intent: "HIGH_INTENT", language: "Telugu", status: "customer" }
      ];
      setLeadList(mockLeads);
      
      const matchedLead = mockLeads.find(l => l.id === leadIdParam) || mockLeads[0];
      setSelectedLead(matchedLead);

      // Mock / Fetch Products
      const mockProducts = [
        { id: "prod_fig", name: "Fiddle Leaf Fig", price: 499.00 },
        { id: "prod_oil", name: "Virgin Coconut Oil", price: 299.00 }
      ];
      setProductList(mockProducts);
      setSelectedProduct(mockProducts[0]);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchInitialData();
  }, [leadIdParam]);

  // Handle starting a fresh conversation
  useEffect(() => {
    if (selectedLead && selectedProduct) {
      setChatHistory([
        {
          role: "assistant",
          content: `Namaste @${selectedLead.username}! 🙏 Welcome to VyaparAI Sales. We noticed you were interested in our ${selectedProduct.name}. Can I tell you more about its pricing and features?`
        }
      ]);
      setCurrentState("PRODUCT_INFO");
      setActiveOrderId(null);
    }
  }, [selectedLead, selectedProduct]);

  // Scroll to bottom of chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userMsg.trim() || !selectedLead || !selectedProduct) return;

    const currentMsg = userMsg;
    setUserMsg("");
    setChatHistory(prev => [...prev, { role: "user", content: currentMsg }]);
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lead_id: selectedLead.id,
          product_id: selectedProduct.id,
          message: currentMsg
        })
      });

      const data = await res.json();
      if (res.ok && data.reply) {
        setChatHistory(prev => [...prev, { role: "assistant", content: data.reply }]);
        setCurrentState(data.state);
        
        // If reply contains payment link, extract simulated order id
        if (data.reply.includes("order_id=")) {
          const match = data.reply.match(/order_id=([^)]+)/);
          if (match) setActiveOrderId(match[1]);
        }
      } else {
        // Fallback mock responses based on simulated LangGraph rules
        simulateSalesAgentResponses(currentMsg);
      }
    } catch (err) {
      console.warn("Backend chat endpoint offline. Simulating LangGraph transition.");
      simulateSalesAgentResponses(currentMsg);
    } finally {
      setLoading(false);
    }
  };

  const simulateSalesAgentResponses = (msg: string) => {
    const msgLower = msg.toLowerCase();
    let reply = "";
    let nextState = currentState;

    if (currentState === "PRODUCT_INFO") {
      reply = `The ${selectedProduct.name} is a high-grade product sourced directly from local producers. It is priced at Rs. ${selectedProduct.price}. Would you like to buy it now?`;
      nextState = "QA_LOOP";
    } else if (currentState === "QA_LOOP") {
      if (msgLower.includes("buy") || msgLower.includes("price") || msgLower.includes("order") || msgLower.includes("yes")) {
        reply = "Excellent choice! Please provide your full delivery address so we can schedule the shipment.";
        nextState = "ADDRESS_COLLECTION";
      } else {
        reply = `Our ${selectedProduct.name} is guaranteed 100% natural and high quality. Are you ready to order?`;
      }
    } else if (currentState === "ADDRESS_COLLECTION") {
      reply = `Thank you! I have recorded your delivery address. Please click the button below to pay Rs. ${selectedProduct.price} using UPI to confirm your order.`;
      nextState = "PAYMENT";
      setActiveOrderId("order_" + Math.random().toString(36).substr(2, 9));
    }

    setTimeout(() => {
      setChatHistory(prev => [...prev, { role: "assistant", content: reply }]);
      setCurrentState(nextState);
    }, 1000);
  };

  const handleSimulatePayment = async () => {
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
        setChatHistory(prev => [
          ...prev,
          { role: "assistant", content: "🎉 Payment Received! Thank you for your purchase. Your order is confirmed and will be shipped within 24 hours. A tracking link will be sent to your number. Have a wonderful day!" }
        ]);
        setCurrentState("ORDER_CONFIRMED");
        setActiveOrderId(null);
      } else {
        mockPaymentSuccess();
      }
    } catch (err) {
      mockPaymentSuccess();
    }
  };

  const mockPaymentSuccess = () => {
    setChatHistory(prev => [
      ...prev,
      { role: "assistant", content: "🎉 Payment Received! [Demo Mode] Thank you for your purchase. Your order is confirmed and will be shipped within 24 hours." }
    ]);
    setCurrentState("ORDER_CONFIRMED");
    setActiveOrderId(null);
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
          AI Sales Agent Simulator
        </h1>
        <p className="text-slate-400 mt-2">
          Monitor the autonomous LangGraph state machine handles conversation and closes sales orders.
        </p>
      </div>

      {/* State timeline steps */}
      <div className="glass-panel rounded-2xl p-6 flex flex-wrap justify-between items-center gap-4">
        {steps.map((step, idx) => {
          const isCurrent = currentState === step.key;
          const isDone = steps.findIndex(s => s.key === currentState) > idx || currentState === "COMPLETE";
          return (
            <div key={step.key} className="flex items-center gap-2">
              <span className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs border ${
                isCurrent 
                  ? "bg-indigo-600 border-indigo-500 text-white animate-pulse" 
                  : isDone 
                  ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" 
                  : "bg-slate-900 border-slate-800 text-slate-500"
              }`}>
                {isDone ? "✓" : idx + 1}
              </span>
              <span className={`text-xs font-semibold ${isCurrent ? "text-indigo-300" : isDone ? "text-slate-300" : "text-slate-600"}`}>
                {step.label}
              </span>
              {idx < steps.length - 1 && (
                <span className="text-slate-800 font-bold ml-2">→</span>
              )}
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        
        {/* CRM Context card */}
        <div className="glass-panel rounded-2xl p-6 h-max space-y-6">
          <div>
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3">Target Lead</h3>
            <select
              onChange={(e) => setSelectedLead(leadList.find(l => l.id === e.target.value))}
              value={selectedLead?.id || ""}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-300 focus:outline-none focus:border-indigo-500 text-sm"
            >
              {leadList.map(lead => (
                <option key={lead.id} value={lead.id}>@{lead.username} ({lead.language})</option>
              ))}
            </select>
          </div>

          <div>
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-3">Product Catalog</h3>
            <select
              onChange={(e) => setSelectedProduct(productList.find(p => p.id === e.target.value))}
              value={selectedProduct?.id || ""}
              className="w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-300 focus:outline-none focus:border-indigo-500 text-sm"
            >
              {productList.map(prod => (
                <option key={prod.id} value={prod.id}>{prod.name} (Rs. {prod.price})</option>
              ))}
            </select>
          </div>

          <div className="border-t border-slate-800 pt-4 text-xs text-slate-400 space-y-2">
            <h4 className="font-bold text-white mb-2 uppercase tracking-wide">Conversation Meta</h4>
            <p>Framework: LangGraph</p>
            <p>Agent Node: {currentState}</p>
            <p>Engine: Llama 3.1 8B</p>
          </div>
        </div>

        {/* Active Chat Interface */}
        <div className="lg:col-span-3 glass-panel rounded-2xl h-[600px] flex flex-col justify-between overflow-hidden relative">
          
          {/* Header */}
          <div className="h-16 border-b border-slate-800 px-6 flex items-center justify-between bg-slate-900/40">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-indigo-600/20 border border-indigo-500 flex items-center justify-center">
                <Bot className="w-5 h-5 text-indigo-400" />
              </div>
              <div>
                <h4 className="font-bold text-sm text-white">SalesAgent AI</h4>
                <p className="text-[10px] text-slate-400">LangGraph Agent Loop Active</p>
              </div>
            </div>
            
            <span className="text-xs text-indigo-400 font-semibold bg-indigo-500/10 px-3 py-1 rounded-full border border-indigo-500/20">
              State: {currentState}
            </span>
          </div>

          {/* Messages body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {chatHistory.map((msg, index) => {
              const isAssistant = msg.role === "assistant";
              return (
                <div key={index} className={`flex gap-3 max-w-[80%] ${isAssistant ? "" : "ml-auto flex-row-reverse"}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs flex-shrink-0 ${
                    isAssistant ? "bg-indigo-600 text-white" : "bg-slate-800 text-slate-300"
                  }`}>
                    {isAssistant ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                  </div>
                  <div className={`p-4 rounded-2xl text-sm leading-relaxed border ${
                    isAssistant 
                      ? "bg-slate-900 border-slate-800/80 text-slate-200" 
                      : "bg-indigo-600/10 border-indigo-500/30 text-slate-100"
                  }`}>
                    {msg.content}
                  </div>
                </div>
              );
            })}

            {/* UPI simulated QR overlay */}
            {currentState === "PAYMENT" && activeOrderId && (
              <div className="flex gap-3 max-w-[80%]">
                <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center flex-shrink-0">
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

            {loading && (
              <div className="flex gap-3 max-w-[80%]">
                <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 text-slate-400 text-sm italic">
                  Thinking...
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Form input */}
          <form onSubmit={handleSendMessage} className="h-20 border-t border-slate-800 px-6 flex items-center gap-3 bg-slate-900/30">
            <input
              type="text"
              placeholder={currentState === "ORDER_CONFIRMED" ? "Order completed successfully." : "Type message for sales agent..."}
              value={userMsg}
              onChange={(e) => setUserMsg(e.target.value)}
              className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 text-sm"
              disabled={currentState === "ORDER_CONFIRMED"}
            />
            <button
              type="submit"
              className="bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white font-bold p-3.5 rounded-xl transition"
              disabled={currentState === "ORDER_CONFIRMED" || loading}
            >
              <Send className="w-4 h-4" />
            </button>
          </form>

        </div>

      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="text-center py-12 text-slate-400 text-sm">Loading Chat Simulator...</div>}>
      <ChatContent />
    </Suspense>
  );
}
