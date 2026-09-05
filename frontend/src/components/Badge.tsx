export function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "accent" | "error" | "success" | "warn";
}) {
  const tones = {
    neutral: "bg-elevated text-ink-2 border-line-subtle",
    accent: "bg-mint-soft text-accent-strong border-mint/60",
    error: "bg-[#FBE9E9] text-error border-[#F2C4C4]",
    success: "bg-[#E9F3EB] text-success border-[#C2DCC8]",
    warn: "bg-highlight text-warn border-[#E8DFAE]",
  };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}
