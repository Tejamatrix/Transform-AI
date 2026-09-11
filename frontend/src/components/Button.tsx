"use client";

import { ButtonHTMLAttributes, forwardRef } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
}

const styles: Record<Variant, string> = {
  primary: "bg-accent text-white hover:bg-accent-strong shadow-soft hover:shadow-lift hover:-translate-y-0.5 disabled:opacity-40 disabled:hover:translate-y-0",
  secondary:
    "glass text-ink hover:border-accent/40 hover:shadow-soft hover:-translate-y-0.5 disabled:opacity-40 disabled:hover:translate-y-0",
  danger: "bg-error text-white hover:brightness-110 shadow-soft disabled:opacity-40",
  ghost: "bg-transparent text-ink-2 hover:bg-white/60 hover:text-ink",
};

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { variant = "primary", loading, className = "", children, disabled, onClick, ...rest },
  ref
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      onClick={onClick}
      className={`inline-flex items-center justify-center gap-2 h-12 px-5 rounded-btn text-[15px] font-medium active:scale-[0.97] disabled:active:scale-100 ${styles[variant]} ${className}`}
      {...rest}
    >
      {loading && (
        <span className="inline-block h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
      )}
      {children}
    </button>
  );
});
