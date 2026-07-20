// frontend/app/faq/page.tsx
"use client";

import { useState } from "react";
import { HelpCircle, ChevronDown, ChevronUp, Sparkles } from "lucide-react";

export default function FAQPage() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const faqs = [
    {
      q: "How does the YouTube-to-WhatsApp sales funnel work?",
      a: "The Coordinator Agent schedules background checks on your YouTube video comments. When a new comment is detected, it is parsed by the Comment Agent. If classified as having buying intent (HIGH_INTENT), the system automatically replies on YouTube with a trackable WhatsApp deep-link. Clicking this link opens WhatsApp and registers the customer to initiate the checkout flow."
    },
    {
      q: "What is a qualified referral link, and how is it tracked?",
      a: "When the Comment Agent posts a link, it generates a custom URL suffix like (Ref: YT_<comment_id>). When the customer messages your WhatsApp line, the Evolution API webhook triggers. Our webhook handler parses this comment ID, searches the database, links the customer's phone number to their YouTube profile, and informs the sales agent of the exact product they are interested in."
    },
    {
      q: "How does the self-healing SSH tunnel maintain 99% uptime?",
      a: "The Tunnel Manager runs a background daemon thread that pings health endpoints on your local port and public tunnel URL every 30 seconds. If a connection drop, TLS handshake error, or network timeout is detected, the self-healing routine kills orphaned connections, restarts the SSH process to generate a new URL, writes the new URL to the configuration settings, and updates the Evolution API webhook targets in the database."
    },
    {
      q: "Does the AI support languages other than English?",
      a: "Yes! The system uses a dedicated Translation Agent and Response Agent to support regional languages like Malayalam, Hindi, Tamil, and Telugu. Marketing scripts, voice synthesis (TTS), and WhatsApp checkout messages can be generated and served in these languages dynamically."
    },
    {
      q: "How does the system collect customer shipping addresses and payments?",
      a: "The WhatsApp checkout assistant uses a LangGraph state machine. It guides the customer through welcoming, answers frequently asked questions using local ChromaDB document contexts, captures their shipping address, validates the postal code, and dynamically generates a UPI invoice link for direct retail payments."
    }
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-16">
      <div>
        <div className="flex items-center gap-2 text-indigo-400 text-xs font-bold uppercase tracking-widest mb-1.5">
          <HelpCircle className="w-4.5 h-4.5" />
          Documentation / Reference
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-slate-100 to-slate-400 bg-clip-text text-transparent">
          Frequently Asked Questions
        </h1>
        <p className="text-slate-400 text-sm mt-2 leading-relaxed">
          Quick reference answers explaining the autonomous orchestration and business processes.
        </p>
      </div>

      <div className="space-y-4">
        {faqs.map((faq, idx) => {
          const isOpen = openIndex === idx;
          return (
            <div 
              key={idx} 
              className="backdrop-blur-md bg-slate-900/60 border border-slate-800/40 rounded-xl overflow-hidden transition-all duration-300"
            >
              <button
                onClick={() => setOpenIndex(isOpen ? null : idx)}
                className="w-full p-5 text-left flex items-center justify-between gap-4 font-bold text-slate-100 hover:bg-slate-850/40 transition-colors text-sm"
              >
                <span className="flex items-center gap-3">
                  <span className="text-indigo-400">0{idx + 1}.</span>
                  {faq.q}
                </span>
                {isOpen ? (
                  <ChevronUp className="w-4 h-4 text-slate-500" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-slate-500" />
                )}
              </button>
              
              {isOpen && (
                <div className="p-5 pt-0 text-xs text-slate-400 leading-relaxed border-t border-slate-850/40 bg-slate-950/20">
                  {faq.a}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Suggestion banner */}
      <div className="p-4 rounded-xl bg-indigo-500/10 border border-indigo-500/10 flex items-center gap-3">
        <Sparkles className="w-5 h-5 text-indigo-400 flex-shrink-0" />
        <span className="text-[11px] text-slate-300 font-medium">
          Have additional questions about your custom deployment? Review the local <code className="text-indigo-300">installation_guide.md</code> file in your project workspace.
        </span>
      </div>
    </div>
  );
}
