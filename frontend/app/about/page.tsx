// frontend/app/about/page.tsx
"use client";

import { Info, Shield, CheckCircle2, Cpu, Target, Eye, Sparkles, Globe, TrendingUp, HeartHandshake } from "lucide-react";

export default function AboutPage() {
  return (
    <div className="max-w-5xl mx-auto space-y-10 pb-16">
      {/* Header Banner */}
      <div className="relative overflow-hidden p-8 rounded-3xl bg-slate-900/80 border border-slate-800/80 shadow-2xl backdrop-blur-xl">
        <div className="absolute -right-10 -top-10 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -left-10 -bottom-10 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="relative z-10 space-y-3">
          <div className="inline-flex items-center gap-2 text-indigo-400 text-xs font-extrabold uppercase tracking-widest px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20">
            <Info className="w-3.5 h-3.5" />
            Project Documentation &amp; Overview
          </div>
          <h1 className="text-3xl md:text-4xl font-black tracking-tight text-white">
            About <span className="bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">VyaparAI</span>
          </h1>
          <p className="text-slate-300 text-sm max-w-3xl leading-relaxed font-medium">
            An End-to-End Autonomous Social Marketing Funnel and Collaborative Multi-Agent Sales Pipeline for Indian Micro-Businesses and Botanical Nurseries.
          </p>
        </div>
      </div>

      {/* Mission & Vision Section */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-widest">
          <Sparkles className="w-4 h-4 text-indigo-400" />
          Strategic Purpose &amp; Direction
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Mission Card */}
          <div className="p-7 backdrop-blur-md bg-gradient-to-br from-slate-900/90 via-slate-900/60 to-indigo-950/40 border border-indigo-500/30 rounded-3xl shadow-xl relative overflow-hidden group hover:border-indigo-500/50 transition duration-300">
            <div className="absolute right-0 top-0 w-32 h-32 bg-indigo-500/10 rounded-full blur-2xl group-hover:bg-indigo-500/20 transition" />
            
            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 rounded-2xl bg-indigo-600/20 border border-indigo-500/40 text-indigo-400">
                <Target className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-black text-white">Our Mission</h3>
                <p className="text-[11px] text-indigo-300 font-semibold">Empowering Sellers on Autopilot</p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed font-medium space-y-3">
              VyaparAI is built to solve the #1 growth barrier for local Indian retailers and botanical nurseries: <strong className="text-white">scaling digital marketing and lead conversion without manual labor or agency overhead</strong>.
              <br /><br />
              By replacing traditional marketing delays with autonomous multi-agent systems (<strong className="text-indigo-300">CrewAI &amp; LangGraph</strong>), VyaparAI enables small business owners to generate high-converting promotional videos, classify social comments, engage leads on WhatsApp 24/7, and close orders instantly.
            </p>

            <div className="mt-5 pt-4 border-t border-indigo-500/20 space-y-2 text-[11px] text-slate-300">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                <span>Zero-friction social lead capture via trackable links</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                <span>Multilingual regional audio synthesis (Hindi, Malayalam, Tamil, Telugu)</span>
              </div>
            </div>
          </div>

          {/* Vision Card */}
          <div className="p-7 backdrop-blur-md bg-gradient-to-br from-slate-900/90 via-slate-900/60 to-emerald-950/40 border border-emerald-500/30 rounded-3xl shadow-xl relative overflow-hidden group hover:border-emerald-500/50 transition duration-300">
            <div className="absolute right-0 top-0 w-32 h-32 bg-emerald-500/10 rounded-full blur-2xl group-hover:bg-emerald-500/20 transition" />

            <div className="flex items-center gap-3 mb-4">
              <div className="p-3 rounded-2xl bg-emerald-600/20 border border-emerald-500/40 text-emerald-400">
                <Eye className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-black text-white">Our Vision</h3>
                <p className="text-[11px] text-emerald-300 font-semibold">Revolutionizing Micro-Commerce</p>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed font-medium space-y-3">
              We envision a future where every local nursery and micro-retailer in India operates an enterprise-grade marketing and sales force on complete autopilot.
              <br /><br />
              VyaparAI aims to bridge the gap between traditional local craftsmanship/plant care and modern digital shoppers—enabling small businesses to expand their reach across India, eliminate abandoned inquiries, and deliver delight through instant, intelligent AI interactions.
            </p>

            <div className="mt-5 pt-4 border-t border-emerald-500/20 space-y-2 text-[11px] text-slate-300">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                <span>Enterprise-grade autonomous sales assistant for every small business</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
                <span>Seamless automated shipping calculation &amp; instant UPI invoicing</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Autopilot Capabilities Grid */}
      <div className="p-7 backdrop-blur-md bg-slate-900/60 border border-slate-800/80 rounded-3xl shadow-xl space-y-5">
        <h3 className="text-sm font-bold uppercase tracking-wider text-indigo-400 flex items-center gap-2">
          <Cpu className="w-4.5 h-4.5" />
          Autopilot Core Capabilities
        </h3>
        
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-white">
              <Globe className="w-4 h-4 text-indigo-400" />
              <span>SEO &amp; Media Engine</span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Automatic trend auditing, commercial script copywriting, native Unicode subtitle rendering, and voice synthesis.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-white">
              <TrendingUp className="w-4 h-4 text-purple-400" />
              <span>YouTube Social Monitor</span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Real-time comment classification, automated AI reply publishing, and direct WhatsApp lead generation.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-white">
              <HeartHandshake className="w-4 h-4 text-emerald-400" />
              <span>Conversational Checkout</span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Stateful LangGraph chat agent with strict delivery address verification, tier discounts, and instant UPI link payment.
            </p>
          </div>
        </div>
      </div>

      {/* Tech Stack & Architecture Details */}
      <div className="p-7 backdrop-blur-md bg-slate-900/60 border border-slate-800/80 rounded-3xl shadow-xl space-y-5">
        <h3 className="text-sm font-bold uppercase tracking-wider text-indigo-400">
          Tech Stack &amp; Architecture
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
          <div className="p-3.5 bg-slate-950/60 border border-slate-850 rounded-2xl">
            <div className="text-[10px] text-slate-500 font-extrabold uppercase tracking-wider">LLM Engine</div>
            <div className="text-xs text-slate-200 font-bold mt-1">Ollama / Llama3.1</div>
          </div>
          <div className="p-3.5 bg-slate-950/60 border border-slate-850 rounded-2xl">
            <div className="text-[10px] text-slate-500 font-extrabold uppercase tracking-wider">Orchestrator</div>
            <div className="text-xs text-slate-200 font-bold mt-1">CrewAI &amp; LangGraph</div>
          </div>
          <div className="p-3.5 bg-slate-950/60 border border-slate-850 rounded-2xl">
            <div className="text-[10px] text-slate-500 font-extrabold uppercase tracking-wider">Backend Database</div>
            <div className="text-xs text-slate-200 font-bold mt-1">Supabase / Postgres</div>
          </div>
          <div className="p-3.5 bg-slate-950/60 border border-slate-850 rounded-2xl">
            <div className="text-[10px] text-slate-500 font-extrabold uppercase tracking-wider">API Framework</div>
            <div className="text-xs text-slate-200 font-bold mt-1">FastAPI / Next.js</div>
          </div>
        </div>
      </div>
    </div>
  );
}
