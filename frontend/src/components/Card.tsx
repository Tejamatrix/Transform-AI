import { ReactNode } from "react";

export function Card({
  children,
  className = "",
  onClick,
}: {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
}) {
  const base =
    "glass glass-brighten rounded-card p-4 anim-fade-in-up";
  if (onClick) {
    return (
      <div
        role="button"
        tabIndex={0}
        onClick={onClick}
        onKeyDown={(e) => e.key === "Enter" && onClick()}
        className={`${base} cursor-pointer hover:border-accent/40 lift ${className}`}
      >
        {children}
      </div>
    );
  }
  return <div className={`${base} ${className}`}>{children}</div>;
}

export function SectionTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-3">
      <h2 className="text-[17px] font-semibold text-ink">{children}</h2>
      {action}
    </div>
  );
}

export function Stat({ label, value, tone = "default" }: { label: string; value: string | number; tone?: "default" | "accent" | "error" | "success" | "warn" }) {
  const colors = {
    default: "text-ink",
    accent: "text-accent-strong",
    error: "text-error",
    success: "text-success",
    warn: "text-warn",
  };
  return (
    <div className="glass rounded-card px-4 py-3">
      <div className="text-xs text-ink-3">{label}</div>
      <div className={`text-xl font-semibold mt-0.5 ${colors[tone]}`}>{value}</div>
    </div>
  );
}
