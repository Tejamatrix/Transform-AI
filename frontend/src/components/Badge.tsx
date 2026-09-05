export function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "accent" | "error" | "success" | "warn";
}) {
  const tones = {
    neutral: "bg-elevated text-ink-2 border-line-subtle",
    accent: "bg-mint-soft text-accent-strong border-mint",
    error: "bg-[#FBEAE8] text-error border-[#F0C9C5]",
    success: "bg-[#E8F3EC] text-success border-[#C2DFCC]",
    warn: "bg-[#F9F1DE] text-warn border-[#EBD8AC]",
  };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}
