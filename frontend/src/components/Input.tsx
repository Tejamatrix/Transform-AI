"use client";

import { InputHTMLAttributes, TextareaHTMLAttributes, SelectHTMLAttributes, forwardRef, ReactNode, useState, createContext, useContext, useCallback } from "react";

const base =
  "w-full bg-input border border-line rounded-btn px-3 text-[14px] text-ink placeholder:text-ink-3 focus:border-accent disabled:opacity-50";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className = "", ...rest }, ref) {
    return <input ref={ref} className={`${base} h-12 ${className}`} {...rest} />;
  }
);

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className = "", ...rest }, ref) {
    return <textarea ref={ref} className={`${base} py-3 min-h-24 ${className}`} {...rest} />;
  }
);

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className = "", children, ...rest }, ref) {
    return (
      <select ref={ref} className={`${base} h-12 appearance-none ${className}`} {...rest}>
        {children}
      </select>
    );
  }
);

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="block text-[13px] text-ink-2 mb-1.5">{label}</span>
      {children}
      {hint && <span className="block text-xs text-ink-3 mt-1">{hint}</span>}
    </label>
  );
}

/* ---------------- Toast ---------------- */

type Toast = { id: number; message: string; kind: "info" | "error" | "success" };
const ToastCtx = createContext<(message: string, kind?: Toast["kind"]) => void>(() => {});

export function useToast() {
  return useContext(ToastCtx);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((message: string, kind: Toast["kind"] = "info") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, message, kind }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4200);
  }, []);
  const dot = { info: "bg-accent", error: "bg-error", success: "bg-success" };
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 w-80">
        {toasts.map((t) => (
          <div key={t.id} className="anim-toast-in flex items-start gap-2.5 bg-elevated border border-line rounded-card px-4 py-3">
            <span className={`mt-1.5 h-2 w-2 rounded-full shrink-0 ${dot[t.kind]}`} />
            <span className="text-[13px] text-ink leading-snug">{t.message}</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
