// frontend/components/ui/ConfirmActionModal.tsx
"use client";

import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, Trash2, X, Loader2, StopCircle } from "lucide-react";

interface ConfirmActionModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "warning" | "indigo";
  isLoading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmActionModal({
  isOpen,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Keep Job",
  variant = "danger",
  isLoading = false,
  onConfirm,
  onCancel
}: ConfirmActionModalProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!isOpen || !mounted) return null;

  const getVariantStyles = () => {
    switch (variant) {
      case "danger":
        return {
          icon: <Trash2 className="w-6 h-6 text-rose-400" />,
          badgeBg: "bg-rose-500/10 border-rose-500/20 text-rose-400",
          btnBg: "bg-rose-600 hover:bg-rose-500 text-white shadow-rose-900/30"
        };
      case "warning":
        return {
          icon: <StopCircle className="w-6 h-6 text-amber-400" />,
          badgeBg: "bg-amber-500/10 border-amber-500/20 text-amber-400",
          btnBg: "bg-amber-600 hover:bg-amber-500 text-white shadow-amber-900/30"
        };
      default:
        return {
          icon: <AlertTriangle className="w-6 h-6 text-indigo-400" />,
          badgeBg: "bg-indigo-500/10 border-indigo-500/20 text-indigo-400",
          btnBg: "bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-900/30"
        };
    }
  };

  const styles = getVariantStyles();

  const modalContent = (
    <div 
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fadeIn pointer-events-auto"
      onClick={(e) => {
        e.stopPropagation();
        if (!isLoading) onCancel();
      }}
    >
      <div 
        className="relative w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden p-6 space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close Button */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onCancel();
          }}
          disabled={isLoading}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 transition p-1.5 rounded-lg hover:bg-slate-800 cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header Icon */}
        <div className="flex items-center gap-3">
          <div className={`p-3 rounded-xl border ${styles.badgeBg}`}>
            {styles.icon}
          </div>
          <div>
            <h3 className="text-base font-extrabold text-white">{title}</h3>
            <span className="text-[11px] font-semibold text-slate-400">Confirmation Required</span>
          </div>
        </div>

        {/* Message */}
        <p className="text-xs font-medium text-slate-300 leading-relaxed bg-slate-950/50 p-3.5 rounded-xl border border-slate-800/60">
          {message}
        </p>

        {/* Action Buttons */}
        <div className="flex justify-end items-center gap-2.5 pt-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onCancel();
            }}
            disabled={isLoading}
            className="px-4 py-2 text-xs font-bold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-xl transition border border-slate-700 cursor-pointer"
          >
            {cancelLabel}
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onConfirm();
            }}
            disabled={isLoading}
            className={`px-4 py-2 text-xs font-bold rounded-xl transition shadow-lg flex items-center gap-2 cursor-pointer ${styles.btnBg}`}
          >
            {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
            <span>{confirmLabel}</span>
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
