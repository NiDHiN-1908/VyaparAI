// frontend/components/ui/JobLogsModal.tsx
"use client";

import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Terminal, X, RefreshCw, Copy, Check } from "lucide-react";

interface JobLogsModalProps {
  isOpen: boolean;
  jobId: string | null;
  productName?: string;
  onClose: () => void;
}

export default function JobLogsModal({
  isOpen,
  jobId,
  productName,
  onClose
}: JobLogsModalProps) {
  const [logs, setLogs] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [mounted, setMounted] = useState(false);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  useEffect(() => {
    setMounted(true);
  }, []);

  const fetchLogs = async () => {
    if (!jobId) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/video-jobs/${jobId}/logs`);
      if (res.ok) {
        const data = await res.json();
        setLogs(data.logs || []);
      }
    } catch (err) {
      console.error("Failed to fetch job logs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && jobId) {
      fetchLogs();
    }
  }, [isOpen, jobId]);

  if (!isOpen || !jobId || !mounted) return null;

  const handleCopyLogs = () => {
    const text = logs.join("\n");
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const modalContent = (
    <div 
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fadeIn pointer-events-auto"
      onClick={(e) => {
        e.stopPropagation();
        onClose();
      }}
    >
      <div 
        className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden p-6 space-y-4 flex flex-col max-h-[80vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Terminal className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-extrabold text-white">Execution Logs</h3>
              <p className="text-[11px] text-slate-400 font-semibold">{productName ? `Product: ${productName}` : `Job ID: ${jobId}`}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={(e) => { e.stopPropagation(); fetchLogs(); }}
              disabled={loading}
              className="p-2 text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 rounded-lg transition cursor-pointer"
              title="Refresh logs"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); handleCopyLogs(); }}
              className="p-2 text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 rounded-lg transition cursor-pointer"
              title="Copy all logs"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onClose(); }}
              className="p-2 text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 rounded-lg transition cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Log Viewer Content */}
        <div className="flex-1 bg-slate-950 rounded-xl border border-slate-800/80 p-4 font-mono text-xs overflow-y-auto space-y-1.5 custom-scrollbar min-h-[300px]">
          {logs.length === 0 ? (
            <p className="text-slate-500 italic">No log entries recorded for this job yet.</p>
          ) : (
            logs.map((log, index) => (
              <div key={index} className="flex gap-2 text-slate-300 leading-relaxed hover:bg-slate-900/60 p-1 rounded">
                <span className="text-slate-600 select-none">{index + 1}.</span>
                <span className="whitespace-pre-wrap">{log}</span>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end pt-2">
          <button
            onClick={(e) => { e.stopPropagation(); onClose(); }}
            className="px-4 py-2 text-xs font-bold text-slate-300 bg-slate-800 hover:bg-slate-700 rounded-xl transition cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
