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
    error: "bg-[#FDECEC] text-error border-[#F5C6C6]",
    success: "bg-[#EAF6EE] text-success border-[#BFE3CC]",
    warn: "bg-[#FBF3E4] text-warn border-[#EFD9AC]",
  };
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}
