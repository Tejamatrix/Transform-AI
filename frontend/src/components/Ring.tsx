"use client";

/** Circular progress ring with PS color-coding:
 *  green > 90 · yellow 70-89 · red < 70 */
export function Ring({
  value,
  label,
  sub,
  size = 84,
  colorOverride,
}: {
  value: number;
  label?: string;
  sub?: string;
  size?: number;
  colorOverride?: string;
}) {
  const v = Math.max(0, Math.min(100, Math.round(value)));
  const color = colorOverride || (v >= 90 ? "#16A34A" : v >= 70 ? "#D97706" : "#DC2626");
  const stroke = 8;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const off = c * (1 - v / 100);

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#E5EAF2" strokeWidth={stroke} />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={off}
            style={{ transition: "stroke-dashoffset 700ms ease, stroke 300ms ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="font-bold" style={{ color, fontSize: size * 0.22 }}>{v}%</span>
        </div>
      </div>
      {label && <div className="text-[12px] text-ink-2 font-medium text-center leading-tight">{label}</div>}
      {sub && <div className="text-[10.5px] text-ink-3 text-center">{sub}</div>}
    </div>
  );
}

/** Qualitative badge from a 0-100 score */
export function ScoreBadge({ value }: { value: number }) {
  const tone = value >= 90 ? "High" : value >= 70 ? "Medium" : "Low";
  const cls = value >= 90 ? "text-success bg-[#E9F3EB] border-[#C2DCC8]"
    : value >= 70 ? "text-warn bg-highlight border-[#D9D6F5]"
    : "text-error bg-[#FBE9E9] border-[#F2C4C4]";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full border text-[11px] font-semibold ${cls}`}>
      {tone}
    </span>
  );
}
