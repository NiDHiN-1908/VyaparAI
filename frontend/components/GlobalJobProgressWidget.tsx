// frontend/components/GlobalJobProgressWidget.tsx
"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { 
  Sparkles, 
  X, 
  Minimize2, 
  Maximize2, 
  ChevronUp, 
  ChevronDown, 
  Loader2, 
  CheckCircle2, 
  AlertTriangle,
  Play,
  Pause,
  RotateCcw,
  StopCircle,
  Trash2,
  Terminal,
  AlertCircle,
  FileText
} from "lucide-react";
import ConfirmActionModal from "./ui/ConfirmActionModal";
import JobLogsModal from "./ui/JobLogsModal";

interface Job {
  job_id: string;
  campaign_name: string;
  product_name: string;
  product_id: string;
  current_stage: string;
  percentage_complete: number;
  started_time: number;
  estimated_completion_time: number;
  estimated_remaining_time: number;
  elapsed_time: number;
  current_status: string;
  status?: string;
  retry_count: number;
  logs: string[];
  error_message: string | null;
  is_stalled?: boolean;
}

interface Toast {
  id: string;
  message: string;
  type: "info" | "success" | "error";
}

export default function GlobalJobProgressWidget() {
  const router = useRouter();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isMinimized, setIsMinimized] = useState<boolean>(false);
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [isHidden, setIsHidden] = useState<boolean>(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const prevStagesRef = useRef<Record<string, { stage: string; status: string; pct: number }>>({});

  // Action Modals State
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

  const addToast = (message: string, type: "info" | "success" | "error" = "info") => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 5000);
  };

  useEffect(() => {
    const ws_protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const ws_host = API_BASE.replace("http://", "").replace("https://", "");
    const DEFAULT_TENANT = "00000000-0000-0000-0000-000000000000";
    
    let socket: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout;
    
    const connectWS = () => {
      try {
        socket = new WebSocket(`${ws_protocol}//${ws_host}/ws?tenant_id=${DEFAULT_TENANT}`);
        
        socket.onmessage = (event) => {
          try {
            const payload = JSON.parse(event.data);
            if (payload.event === "job.deleted" && payload.data) {
              setJobs(prevJobs => prevJobs.filter(j => j.job_id !== payload.data.job_id && j.product_id !== payload.data.product_id));
              return;
            }
            if (payload.event === "job.progress" && payload.data) {
              const updatedJob = payload.data;
              
              setJobs(prevJobs => {
                if (updatedJob.current_status === "Completed" || updatedJob.current_status === "Failed" || updatedJob.current_status === "Cancelled") {
                  return prevJobs.filter(j => j.job_id !== updatedJob.job_id && j.product_id !== updatedJob.product_id);
                }
                if (prevJobs.some(j => j.job_id === updatedJob.job_id || j.product_id === updatedJob.product_id)) {
                  return prevJobs.map(j => (j.job_id === updatedJob.job_id || j.product_id === updatedJob.product_id) ? updatedJob : j);
                }
                return [...prevJobs, updatedJob];
              });

              const cached = prevStagesRef.current[updatedJob.job_id || updatedJob.product_id];
              if (!cached) {
                addToast(`Generation started for ${updatedJob.product_name}`, "info");
              } else {
                if (cached.stage !== updatedJob.current_stage) {
                  addToast(`Stage updated: ${updatedJob.current_stage} (${updatedJob.percentage_complete}%)`, "info");
                }
                if (updatedJob.current_status === "Completed" && cached.status !== "Completed") {
                  addToast(`Video generation for ${updatedJob.product_name} completed!`, "success");
                  router.refresh();
                } else if (updatedJob.current_status === "Failed" && cached.status !== "Failed") {
                  addToast(`Job failed for ${updatedJob.product_name}: ${updatedJob.error_message || "Error"}`, "error");
                } else if (updatedJob.current_status === "Cancelled" && cached.status !== "Cancelled") {
                  addToast(`Job cancelled for ${updatedJob.product_name}`, "info");
                } else if (updatedJob.current_status === "Stalled" && cached.status !== "Stalled") {
                  addToast(`Job stalled for ${updatedJob.product_name}.`, "error");
                }
              }
              prevStagesRef.current[updatedJob.job_id || updatedJob.product_id] = {
                stage: updatedJob.current_stage,
                status: updatedJob.current_status,
                pct: updatedJob.percentage_complete
              };
            }
          } catch (err) {
            console.error("WS message parse error:", err);
          }
        };
        
        socket.onclose = () => {
          reconnectTimeout = setTimeout(connectWS, 5000);
        };
        
        socket.onerror = (err) => {
          console.warn("WebSocket progress connection error:", err);
          socket?.close();
        };
      } catch (e) {
        console.error("WebSocket connection failure:", e);
      }
    };
    
    connectWS();
    
    return () => {
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
      clearTimeout(reconnectTimeout);
    };
  }, [API_BASE]);

  useEffect(() => {
    let intervalId: NodeJS.Timeout;

    const pollActiveJobs = async () => {
      try {
        const res = await fetch(`${API_BASE}/video-jobs/active`);
        if (!res.ok) return;
        const data = await res.json();
        
        if (data.status === "success" && Array.isArray(data.jobs)) {
          const activeJobs: Job[] = data.jobs;
          setJobs(activeJobs);

          if (activeJobs.length === 0) {
            prevStagesRef.current = {};
            return;
          }

          activeJobs.forEach(job => {
            const key = job.job_id || job.product_id;
            const cached = prevStagesRef.current[key];
            if (!cached) {
              addToast(`Generation active: ${job.product_name}`, "info");
            } else {
              if (cached.stage !== job.current_stage) {
                addToast(`Stage: ${job.current_stage} (${job.percentage_complete}%)`, "info");
              }
              if (job.current_status === "Completed" && cached.status !== "Completed") {
                addToast(`Video generation for ${job.product_name} completed!`, "success");
                router.refresh();
              } else if (job.current_status === "Failed" && cached.status !== "Failed") {
                addToast(`Job failed for ${job.product_name}: ${job.error_message || "Error"}`, "error");
              } else if (job.current_status === "Stalled" && cached.status !== "Stalled") {
                addToast(`Job stalled for ${job.product_name}.`, "error");
              }
            }
            prevStagesRef.current[key] = {
              stage: job.current_stage,
              status: job.current_status,
              pct: job.percentage_complete
            };
          });
        }
      } catch (err) {
        console.error("Failed to poll active video generation jobs:", err);
      }
    };

    pollActiveJobs();
    intervalId = setInterval(pollActiveJobs, 3000);

    return () => {
      clearInterval(intervalId);
    };
  }, []);

  // Job Actions
  const handleCancelJob = async (job: Job) => {
    setActionLoading(true);
    const targetId = job.job_id || job.product_id;
    try {
      const res = await fetch(`${API_BASE}/video-jobs/${targetId}/cancel`, { method: "POST" });
      if (res.ok) {
        addToast(`Job for ${job.product_name} cancelled`, "info");
        setJobs(prev => prev.filter(j => j.job_id !== targetId && j.product_id !== targetId));
      } else {
        addToast(`Failed to cancel job (${res.status})`, "error");
      }
    } catch (err) {
      console.error("Cancel job error:", err);
      addToast("Failed to cancel job", "error");
    } finally {
      setActionLoading(false);
      setConfirmModal({ isOpen: false, type: null, job: null });
    }
  };

  const handleDeleteJob = async (job: Job) => {
    setActionLoading(true);
    const targetId = job.job_id || job.product_id;
    try {
      const res = await fetch(`${API_BASE}/video-jobs/${targetId}`, { method: "DELETE" });
      if (res.ok) {
        addToast(`Job for ${job.product_name} deleted`, "success");
        setJobs(prev => prev.filter(j => j.job_id !== targetId && j.product_id !== targetId));
      } else {
        addToast(`Failed to delete job (${res.status})`, "error");
      }
    } catch (err) {
      console.error("Delete job error:", err);
      addToast("Failed to delete job", "error");
    } finally {
      setActionLoading(false);
      setConfirmModal({ isOpen: false, type: null, job: null });
    }
  };

  const handlePauseJob = async (job: Job) => {
    const targetId = job.job_id || job.product_id;
    try {
      const res = await fetch(`${API_BASE}/video-jobs/${targetId}/pause`, { method: "POST" });
      if (res.ok) {
        addToast(`Paused ${job.product_name}`, "info");
        setJobs(prev => prev.map(j => (j.job_id === targetId || j.product_id === targetId) ? { ...j, current_status: "Paused" } : j));
      }
    } catch (err) {
      console.error("Pause job error:", err);
    }
  };

  const handleResumeJob = async (job: Job) => {
    const targetId = job.job_id || job.product_id;
    try {
      const res = await fetch(`${API_BASE}/video-jobs/${targetId}/resume`, { method: "POST" });
      if (res.ok) {
        addToast(`Resumed ${job.product_name}`, "info");
        setJobs(prev => prev.map(j => (j.job_id === targetId || j.product_id === targetId) ? { ...j, current_status: "Running" } : j));
      }
    } catch (err) {
      console.error("Resume job error:", err);
    }
  };

  const handleRetryJob = async (job: Job) => {
    const targetId = job.job_id || job.product_id;
    try {
      const res = await fetch(`${API_BASE}/video-jobs/${targetId}/retry`, { method: "POST" });
      if (res.ok) {
        addToast(`Retry initiated for ${job.product_name}`, "info");
        setJobs(prev => prev.map(j => (j.job_id === targetId || j.product_id === targetId) ? { ...j, current_status: "Running" } : j));
      }
    } catch (err) {
      console.error("Retry job error:", err);
    }
  };

  if (jobs.length === 0 || isHidden) {
    return (
      <div className="fixed bottom-5 right-5 z-40 flex flex-col gap-2">
        {toasts.map(toast => (
          <div 
            key={toast.id}
            className={`px-4 py-3 rounded-xl shadow-xl flex items-center gap-3 backdrop-blur-md border animate-bounce ${
              toast.type === "success" 
                ? "bg-emerald-950/80 border-emerald-500/30 text-emerald-300"
                : toast.type === "error"
                ? "bg-rose-950/80 border-rose-500/30 text-rose-300"
                : "bg-slate-900/80 border-indigo-500/30 text-indigo-300"
            }`}
          >
            {toast.type === "success" && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
            {toast.type === "error" && <AlertTriangle className="w-4 h-4 text-rose-400" />}
            {toast.type === "info" && <Sparkles className="w-4 h-4 text-indigo-400" />}
            <span className="text-xs font-semibold">{toast.message}</span>
          </div>
        ))}
        {isHidden && jobs.length > 0 && (
          <button 
            onClick={() => setIsHidden(false)}
            className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold p-3 rounded-full shadow-lg transition flex items-center justify-center border border-indigo-500/30 cursor-pointer"
            title="Restore generation widget"
          >
            <Sparkles className="w-5 h-5 animate-pulse" />
          </button>
        )}
      </div>
    );
  }

  const primaryJob = jobs[0];
  const remainingMin = Math.round(primaryJob.estimated_remaining_time / 60) || 1;
  const isStalled = primaryJob.current_status === "Stalled" || primaryJob.is_stalled;
  const isPaused = primaryJob.current_status === "Paused";

  return (
    <>
      <div className="fixed bottom-6 right-6 z-40 flex flex-col gap-3 items-end max-w-sm w-full">
        {/* Toast notifications */}
        <div className="flex flex-col gap-2 w-full items-end">
          {toasts.map(toast => (
            <div 
              key={toast.id}
              className={`px-4 py-2.5 rounded-lg shadow-lg flex items-center gap-2.5 backdrop-blur-md border text-xs font-semibold transition-all duration-300 ${
                toast.type === "success" 
                  ? "bg-emerald-950/90 border-emerald-500/30 text-emerald-300"
                  : toast.type === "error"
                  ? "bg-rose-950/90 border-rose-500/30 text-rose-300"
                  : "bg-slate-900/90 border-indigo-500/20 text-indigo-300"
              }`}
            >
              {toast.type === "success" && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
              {toast.type === "error" && <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />}
              {toast.type === "info" && <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />}
              <span>{toast.message}</span>
            </div>
          ))}
        </div>

        {/* Floating progress panel */}
        <div className="glass-panel border border-slate-800/80 rounded-2xl w-full shadow-2xl overflow-hidden transition-all duration-500 bg-slate-950/90 backdrop-blur-lg">
          {/* Widget Header */}
          {(() => {
            const isAwaitingApproval = primaryJob.status === "waiting_approval" || primaryJob.current_stage?.includes("Approval") || primaryJob.status === "script_approved";
            return (
              <>
                <div className="flex items-center justify-between px-4 py-3 bg-slate-900/40 border-b border-slate-800/35">
                  <div className="flex items-center gap-2">
                    {isAwaitingApproval ? (
                      <FileText className="w-4 h-4 text-amber-400 animate-pulse" />
                    ) : isStalled ? (
                      <AlertCircle className="w-4 h-4 text-amber-400 animate-bounce" />
                    ) : isPaused ? (
                      <Pause className="w-4 h-4 text-amber-400" />
                    ) : (
                      <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
                    )}
                    <span className="text-xs font-bold text-slate-200">
                      {isAwaitingApproval ? "Script Approval Required" : "Video Generation"}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <button 
                      onClick={(e) => { e.stopPropagation(); setIsMinimized(!isMinimized); }}
                      className="p-1 rounded text-slate-500 hover:text-slate-300 hover:bg-slate-800/40 transition cursor-pointer"
                      title={isMinimized ? "Expand widget" : "Minimize widget"}
                    >
                      <Minimize2 className="w-3 h-3" />
                    </button>
                    <button 
                      onClick={(e) => { e.stopPropagation(); setIsHidden(true); }}
                      className="p-1 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition cursor-pointer"
                      title="Hide widget"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Widget Body */}
                {!isMinimized && (
                  <div className="p-4 space-y-3.5">
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="text-sm font-extrabold text-white leading-tight">{primaryJob.product_name}</h4>
                        <p className="text-[10px] text-slate-400 font-semibold mt-0.5">{primaryJob.current_stage}</p>
                      </div>
                      <span className="text-lg font-black text-indigo-400 leading-none">{primaryJob.percentage_complete}%</span>
                    </div>

                    {/* Awaiting Script Approval Banner */}
                    {isAwaitingApproval && (
                      <div className="bg-indigo-950/80 border border-indigo-500/40 p-3 rounded-xl flex items-center justify-between gap-2 shadow-lg">
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-indigo-400 flex-shrink-0 animate-pulse" />
                          <div>
                            <span className="text-xs font-extrabold text-white block">Script Draft Ready!</span>
                            <span className="text-[10px] text-indigo-200/80 block">Review screenplay copy before rendering video</span>
                          </div>
                        </div>
                        <button
                          onClick={(e) => { e.stopPropagation(); router.push(`/preview?product_id=${primaryJob.product_id}`); }}
                          className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] font-bold shadow transition cursor-pointer flex-shrink-0"
                        >
                          Review &amp; Approve
                        </button>
                      </div>
                    )}

                    {/* Stalled Warning Banner */}
                    {isStalled && (
                      <div className="bg-amber-950/60 border border-amber-500/30 p-2.5 rounded-xl space-y-2">
                        <div className="flex items-center gap-2 text-amber-300 text-xs font-bold">
                          <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                          <span>This generation appears to be stalled.</span>
                        </div>
                        <p className="text-[10px] text-amber-200/80">No progress detected for over 10 minutes. You can retry from the last completed stage or cancel the job.</p>
                      </div>
                    )}

              {/* Progress Bar */}
              <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-800/50">
                <div 
                  className={`h-full rounded-full transition-all duration-500 ${
                    isStalled
                      ? "bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]"
                      : isPaused
                      ? "bg-purple-500"
                      : "bg-gradient-to-r from-indigo-500 to-purple-500 shadow-[0_0_8px_rgba(99,102,241,0.5)]"
                  }`}
                  style={{ width: `${primaryJob.percentage_complete}%` }}
                />
              </div>

              {/* Stage info and completion timer */}
              <div className="flex justify-between items-center text-[10px] text-slate-500 font-semibold">
                <span>{remainingMin} min remaining</span>
                <span className={`font-bold ${isStalled ? "text-amber-400" : isPaused ? "text-purple-400" : "text-indigo-400"}`}>
                  Status: {primaryJob.current_status}
                </span>
              </div>

              {/* Action Toolbar */}
              <div className="flex items-center justify-between gap-1.5 pt-1 border-t border-slate-900">
                <div className="flex items-center gap-1">
                  {/* Pause / Resume */}
                  {isPaused ? (
                    <button
                      onClick={(e) => { e.stopPropagation(); handleResumeJob(primaryJob); }}
                      className="px-2 py-1 rounded bg-purple-500/10 border border-purple-500/20 hover:bg-purple-500/20 text-purple-300 text-[10px] font-bold flex items-center gap-1 transition cursor-pointer"
                      title="Resume Job"
                    >
                      <Play className="w-3 h-3" />
                      <span>Resume</span>
                    </button>
                  ) : (
                    <button
                      onClick={(e) => { e.stopPropagation(); handlePauseJob(primaryJob); }}
                      className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-bold flex items-center gap-1 transition border border-slate-700 cursor-pointer"
                      title="Pause Job"
                    >
                      <Pause className="w-3 h-3" />
                      <span>Pause</span>
                    </button>
                  )}

                  {/* Retry */}
                  <button
                    onClick={(e) => { e.stopPropagation(); handleRetryJob(primaryJob); }}
                    className="px-2 py-1 rounded bg-indigo-500/10 border border-indigo-500/20 hover:bg-indigo-500/20 text-indigo-300 text-[10px] font-bold flex items-center gap-1 transition cursor-pointer"
                    title="Retry from stage"
                  >
                    <RotateCcw className="w-3 h-3" />
                    <span>Retry</span>
                  </button>

                  {/* View Logs */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setLogsModal({ isOpen: true, jobId: primaryJob.job_id || primaryJob.product_id, productName: primaryJob.product_name });
                    }}
                    className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-bold flex items-center gap-1 transition border border-slate-700 cursor-pointer"
                    title="View Logs"
                  >
                    <Terminal className="w-3 h-3" />
                    <span>Logs</span>
                  </button>
                </div>

                <div className="flex items-center gap-1">
                  {/* Cancel */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setConfirmModal({ isOpen: true, type: "cancel", job: primaryJob });
                    }}
                    className="p-1 rounded bg-amber-500/10 border border-amber-500/20 hover:bg-amber-500/20 text-amber-400 transition cursor-pointer"
                    title="Cancel Job"
                  >
                    <StopCircle className="w-3.5 h-3.5" />
                  </button>

                  {/* Delete */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setConfirmModal({ isOpen: true, type: "delete", job: primaryJob });
                    }}
                    className="p-1 rounded bg-rose-500/10 border border-rose-500/20 hover:bg-rose-500/20 text-rose-400 transition cursor-pointer"
                    title="Delete Job"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* View Details Link */}
              <div className="flex justify-between items-center pt-1 border-t border-slate-900">
                <button
                  onClick={(e) => { e.stopPropagation(); router.push("/jobs"); }}
                  className="text-[10px] text-slate-400 hover:text-slate-200 font-bold transition cursor-pointer"
                >
                  All Background Jobs
                </button>
                <button 
                  onClick={(e) => { e.stopPropagation(); router.push(`/preview?product_id=${primaryJob.product_id}`); }}
                  className="flex items-center gap-1 text-[10px] font-bold text-indigo-400 hover:text-indigo-300 transition cursor-pointer"
                >
                  <span>Campaign Details</span>
                  <Play className="w-3 h-3" />
                </button>
              </div>
            </div>
          )}

          {/* Minimized Body */}
          {isMinimized && (
            <div className="px-4 py-2.5 flex items-center justify-between text-xs font-bold">
              <span className="text-slate-300 truncate max-w-[150px]">{primaryJob.product_name}</span>
              <div className="flex items-center gap-2">
                <span className="text-indigo-400">{primaryJob.percentage_complete}%</span>
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-ping" />
              </div>
            </div>
          )}
              </>
            );
          })()}
        </div>
      </div>

      {/* Confirmation Modal */}
      {confirmModal.job && (
        <ConfirmActionModal
          isOpen={confirmModal.isOpen}
          title={confirmModal.type === "cancel" ? "Cancel Video Generation?" : "Delete Video Job?"}
          message={
            confirmModal.type === "cancel"
              ? "Are you sure you want to cancel this video generation? Any unfinished work will be discarded and background processes stopped immediately."
              : "Are you sure you want to permanently delete this generation job? Intermediate temporary files and logs will be removed."
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
    </>
  );
}
