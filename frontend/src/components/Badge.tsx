export function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "accent" | "error" | "success" | "warn";
}) {
  const tones = {
    neutral: "bg-elevated text-ink-2 border-line-subtle",
    accent: "bg-accent/10 text-accent border-accent/30",
    error: "bg-error/10 text-error border-error/30",
    success: "bg-success/10 text-success border-success/30",
    warn: "bg-warn/10 text-warn border-warn/30",
  };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}
