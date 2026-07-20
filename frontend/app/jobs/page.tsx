// frontend/app/jobs/page.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ListFilter,
  Play,
  Pause,
  RotateCcw,
  StopCircle,
  Trash2,
  Terminal,
  Clock,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Loader2,
  ArrowLeft,
  Sparkles,
  RefreshCw,
  Search
} from "lucide-react";
import ConfirmActionModal from "@/components/ui/ConfirmActionModal";
import JobLogsModal from "@/components/ui/JobLogsModal";

interface Job {
  job_id: string;
  campaign_name: string;
  product_name: string;
  product_id: string;
  current_stage: string;
  percentage_complete: number;
  started_time: number;
  last_updated_time?: number;
  estimated_remaining_time: number;
  elapsed_time: number;
  current_status: string;
  retry_count: number;
  logs: string[];
  error_message: string | null;
  is_stalled?: boolean;
}

export default function BackgroundJobsPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Modals state
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    type: "cancel" | "delete" | null;
    job: Job | null;
  }>({ isOpen: false, type: null, job: null });

  const [logsModal, setLogsModal] = useState<{
    isOpen: boolean;
    jobId: string | null;
    productName?: string;
  }>({ isOpen: false, jobId: null });

  const [actionLoading, setActionLoading] = useState(false);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const filterParam = activeFilter === "all" ? "" : `?status_filter=${activeFilter}`;
      const res = await fetch(`${API_BASE}/video-jobs/list${filterParam}`);
      if (res.ok) {
        const data = await res.json();
        setJobs(data.jobs || []);
      }
    } catch (err) {
      console.error("Failed to fetch jobs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 4000);
    return () => clearInterval(interval);
  }, [activeFilter]);

  // Actions
  const handleCancelJob = async (job: Job) => {
    setActionLoading(true);
    try {
      const res = await fetch(`${API_BASE}/video-jobs/${job.job_id}/cancel`, { method: "POST" });
      if (res.ok) {
        fetchJobs();
      }
    } catch (err) {
      console.error("Failed to cancel job:", err);
    } finally {
      setActionLoading(false);
      setConfirmModal({ isOpen: false, type: null, job: null });
    }
  };

  const handleDeleteJob = async (job: Job) => {
    setActionLoading(true);
    try {
      const res = await fetch(`${API_BASE}/video-jobs/${job.job_id}`, { method: "DELETE" });
      if (res.ok) {
        fetchJobs();
      }
    } catch (err) {
      console.error("Failed to delete job:", err);
    } finally {
      setActionLoading(false);
      setConfirmModal({ isOpen: false, type: null, job: null });
    }
  };

  const handlePauseJob = async (job: Job) => {
    try {
      await fetch(`${API_BASE}/video-jobs/${job.job_id}/pause`, { method: "POST" });
      fetchJobs();
    } catch (err) {
      console.error("Failed to pause job:", err);
    }
  };

  const handleResumeJob = async (job: Job) => {
    try {
      await fetch(`${API_BASE}/video-jobs/${job.job_id}/resume`, { method: "POST" });
      fetchJobs();
    } catch (err) {
      console.error("Failed to resume job:", err);
    }
  };

  const handleRetryJob = async (job: Job) => {
    try {
      await fetch(`${API_BASE}/video-jobs/${job.job_id}/retry`, { method: "POST" });
      fetchJobs();
    } catch (err) {
      console.error("Failed to retry job:", err);
    }
  };

  // Status Badge Helper
  const getStatusBadge = (status: string) => {
    const s = status.toLowerCase();
    switch (s) {
      case "completed":
        return (
          <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center gap-1.5 w-fit">
            <CheckCircle2 className="w-3 h-3" />
            <span>Completed</span>
          </span>
        );
      case "running":
      case "processing":
      case "rendering":
        return (
          <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center gap-1.5 w-fit">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>Running</span>
          </span>
        );
      case "queued":
      case "preparing":
        return (
          <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-slate-800 border border-slate-700 text-slate-300 flex items-center gap-1.5 w-fit">
            <Clock className="w-3 h-3" />
            <span>Queued</span>
          </span>
        );
      case "stalled":
        return (
          <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center gap-1.5 w-fit animate-pulse">
            <AlertCircle className="w-3 h-3" />
            <span>Stalled</span>
          </span>
        );
      case "paused":
        return (
          <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center gap-1.5 w-fit">
            <Pause className="w-3 h-3" />
            <span>Paused</span>
          </span>
        );
      case "cancelled":
        return (
          <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-950/60 border border-amber-500/30 text-amber-300 flex items-center gap-1.5 w-fit">
            <StopCircle className="w-3 h-3" />
            <span>Cancelled</span>
          </span>
        );
      case "failed":
        return (
          <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center gap-1.5 w-fit">
            <AlertTriangle className="w-3 h-3" />
            <span>Failed</span>
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 rounded-full text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700 w-fit">
            {status}
          </span>
        );
    }
  };

  const filteredJobs = jobs.filter(job => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      job.product_name.toLowerCase().includes(q) ||
      job.campaign_name.toLowerCase().includes(q) ||
      job.job_id.toLowerCase().includes(q) ||
      job.current_stage.toLowerCase().includes(q)
    );
  });

  const filterTabs = [
    { id: "all", label: "All Jobs" },
    { id: "running", label: "Running" },
    { id: "queued", label: "Queued" },
    { id: "stalled", label: "Stalled" },
    { id: "completed", label: "Completed" },
    { id: "failed", label: "Failed" },
    { id: "cancelled", label: "Cancelled" },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 space-y-6">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <ListFilter className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-extrabold tracking-tight text-white">Background Jobs</h1>
          </div>
          <p className="text-xs text-slate-400 font-semibold pl-10">
            Monitor, pause, resume, retry, or delete long-running video generation tasks.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchJobs}
            disabled={loading}
            className="px-3.5 py-2 text-xs font-bold bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-xl transition flex items-center gap-2 text-slate-300"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter Tabs & Search Bar */}
      <div className="flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto custom-scrollbar w-full md:w-auto pb-1">
          {filterTabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveFilter(tab.id)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition whitespace-nowrap ${
                activeFilter === tab.id
                  ? "bg-indigo-600 text-white shadow-lg shadow-indigo-900/30"
                  : "bg-slate-900/60 hover:bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800/80"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search input */}
        <div className="relative w-full md:w-64">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search by product, stage..."
            className="w-full bg-slate-900/80 border border-slate-800/80 rounded-xl pl-9 pr-3 py-2 text-xs font-semibold text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/50"
          />
        </div>
      </div>

      {/* Jobs Table */}
      <div className="glass-panel border border-slate-800/80 rounded-2xl overflow-hidden shadow-2xl bg-slate-900/40">
        <div className="overflow-x-auto custom-scrollbar">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800/80 bg-slate-950/60 text-slate-400 font-bold uppercase tracking-wider text-[10px]">
                <th className="px-4 py-3.5">Product & Campaign</th>
                <th className="px-4 py-3.5">Status</th>
                <th className="px-4 py-3.5">Current Stage</th>
                <th className="px-4 py-3.5">Progress</th>
                <th className="px-4 py-3.5">Timing</th>
                <th className="px-4 py-3.5 text-center">Retries</th>
                <th className="px-4 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40 font-medium text-slate-300">
              {loading && filteredJobs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-slate-500 font-semibold">
                    <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-400" />
                    <span>Loading background jobs...</span>
                  </td>
                </tr>
              ) : filteredJobs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-slate-500 font-semibold">
                    No matching background jobs found.
                  </td>
                </tr>
              ) : (
                filteredJobs.map(job => {
                  const isStalled = job.current_status === "Stalled" || job.is_stalled;
                  const isPaused = job.current_status === "Paused";
                  const isCompleted = job.current_status === "Completed";
                  const isRunning = ["Running", "Processing", "Rendering"].includes(job.current_status);

                  return (
                    <tr key={job.job_id} className="hover:bg-slate-800/30 transition-colors">
                      {/* Product & Campaign */}
                      <td className="px-4 py-4">
                        <div className="flex flex-col">
                          <span className="font-extrabold text-white text-sm">{job.product_name}</span>
                          <span className="text-[10px] text-slate-400 font-semibold">{job.campaign_name}</span>
                          <span className="text-[9px] text-slate-600 font-mono mt-0.5">ID: {job.job_id}</span>
                        </div>
                      </td>

                      {/* Status */}
                      <td className="px-4 py-4">
                        {getStatusBadge(job.current_status)}
                      </td>

                      {/* Current Stage */}
                      <td className="px-4 py-4">
                        <div className="flex flex-col">
                          <span className="font-bold text-slate-200">{job.current_stage}</span>
                          {job.error_message && (
                            <span className="text-[10px] text-rose-400 font-semibold truncate max-w-xs">{job.error_message}</span>
                          )}
                        </div>
                      </td>

                      {/* Progress Bar */}
                      <td className="px-4 py-4 min-w-[140px]">
                        <div className="space-y-1">
                          <div className="flex justify-between text-[10px] font-bold text-slate-400">
                            <span>{job.percentage_complete}%</span>
                          </div>
                          <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
                            <div
                              className={`h-full rounded-full transition-all duration-500 ${
                                isStalled
                                  ? "bg-amber-500"
                                  : isCompleted
                                  ? "bg-emerald-500"
                                  : "bg-indigo-500"
                              }`}
                              style={{ width: `${job.percentage_complete}%` }}
                            />
                          </div>
                        </div>
                      </td>

                      {/* Timing */}
                      <td className="px-4 py-4 text-[11px] text-slate-400 font-medium">
                        <div>Elapsed: {job.elapsed_time || 0}s</div>
                        <div className="text-[10px] text-slate-500">Est. left: {job.estimated_remaining_time || 0}s</div>
                      </td>

                      {/* Retries */}
                      <td className="px-4 py-4 text-center font-bold text-slate-300">
                        {job.retry_count || 0}
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {/* Pause / Resume */}
                          {isPaused ? (
                            <button
                              onClick={() => handleResumeJob(job)}
                              className="p-1.5 rounded-lg bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 border border-purple-500/20 transition"
                              title="Resume Job"
                            >
                              <Play className="w-3.5 h-3.5" />
                            </button>
                          ) : isRunning ? (
                            <button
                              onClick={() => handlePauseJob(job)}
                              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
                              title="Pause Job"
                            >
                              <Pause className="w-3.5 h-3.5" />
                            </button>
                          ) : null}

                          {/* Retry */}
                          {!isCompleted && (
                            <button
                              onClick={() => handleRetryJob(job)}
                              className="p-1.5 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 border border-indigo-500/20 transition"
                              title="Retry Job"
                            >
                              <RotateCcw className="w-3.5 h-3.5" />
                            </button>
                          )}

                          {/* Logs */}
                          <button
                            onClick={() => setLogsModal({ isOpen: true, jobId: job.job_id, productName: job.product_name })}
                            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
                            title="View Logs"
                          >
                            <Terminal className="w-3.5 h-3.5" />
                          </button>

                          {/* Campaign Link */}
                          <button
                            onClick={() => router.push(`/preview?product_id=${job.product_id}`)}
                            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-indigo-400 border border-slate-700 transition"
                            title="Go to Campaign Details"
                          >
                            <Play className="w-3.5 h-3.5" />
                          </button>

                          {/* Cancel */}
                          {!isCompleted && job.current_status !== "Cancelled" && (
                            <button
                              onClick={() => setConfirmModal({ isOpen: true, type: "cancel", job })}
                              className="p-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/20 transition"
                              title="Cancel Job"
                            >
                              <StopCircle className="w-3.5 h-3.5" />
                            </button>
                          )}

                          {/* Delete */}
                          <button
                            onClick={() => setConfirmModal({ isOpen: true, type: "delete", job })}
                            className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/20 transition"
                            title="Permanently Delete Job"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Confirmation Modal */}
      {confirmModal.job && (
        <ConfirmActionModal
          isOpen={confirmModal.isOpen}
          title={confirmModal.type === "cancel" ? "Cancel Video Generation?" : "Delete Video Job?"}
          message={
            confirmModal.type === "cancel"
              ? `Are you sure you want to cancel video generation for '${confirmModal.job.product_name}'? Any unfinished work will be discarded and running processes stopped.`
              : `Are you sure you want to permanently delete job '${confirmModal.job.job_id}'? Temporary intermediate files will be purged.`
          }
          confirmLabel={confirmModal.type === "cancel" ? "Cancel Job" : "Permanently Delete"}
          variant={confirmModal.type === "cancel" ? "warning" : "danger"}
          isLoading={actionLoading}
          onConfirm={() => {
            if (confirmModal.type === "cancel") handleCancelJob(confirmModal.job!);
            else if (confirmModal.type === "delete") handleDeleteJob(confirmModal.job!);
          }}
          onCancel={() => setConfirmModal({ isOpen: false, type: null, job: null })}
        />
      )}

      {/* Logs Modal */}
      <JobLogsModal
        isOpen={logsModal.isOpen}
        jobId={logsModal.jobId}
        productName={logsModal.productName}
        onClose={() => setLogsModal({ isOpen: false, jobId: null })}
      />
    </div>
  );
}
