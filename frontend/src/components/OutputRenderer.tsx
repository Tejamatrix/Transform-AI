"use client";

import { useMemo } from "react";

/* Generic structured-content renderer with optional FactTrace grounding:
   sentences that match validated claims get color-coded underlines
   (green = verified, amber = partial, red = unsupported) and are clickable
   to inspect source evidence. */

import type { GroundingClaim } from "@/lib/types";

const STATUS_CLASS: Record<string, string> = {
  VERIFIED: "border-b-2 border-success/70 bg-success/10",
  PARTIALLY_SUPPORTED: "border-b-2 border-warn/70 bg-warn/10",
  UNSUPPORTED: "border-b-2 border-error/80 bg-error/15",
};

function norm(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9\u00C0-\u024F\u0900-\u097F\u0C00-\u0C7F]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function TextBlock({
  text,
  claimMap,
  onClaimClick,
}: {
  text: string;
  claimMap: Map<string, GroundingClaim> | null;
  onClaimClick?: (index: number) => void;
}) {
  if (!claimMap || claimMap.size === 0) {
    return (
      <div className="text-[14px] text-ink-2 leading-relaxed whitespace-pre-wrap">
        {text.split("\n").map((line, i) =>
          line.trim().startsWith("-") || line.trim().startsWith("•") ? (
            <div key={i} className="pl-4">{line}</div>
          ) : (
            <div key={i}>{line}</div>
          )
        )}
      </div>
    );
  }

  // Grounded rendering: split into sentence pieces and match claims.
  const lines = text.split("\n");
  return (
    <div className="text-[14px] text-ink-2 leading-relaxed whitespace-pre-wrap">
      {lines.map((line, li) => {
        const isBullet = line.trim().startsWith("-") || line.trim().startsWith("•");
        const sentences = line.match(/[^.!?…\n]+[.!?…]*/g) || [line];
        return (
          <div key={li} className={isBullet ? "pl-4" : undefined}>
            {sentences.map((sentence, si) => {
              const hit = claimMap.get(norm(sentence));
              if (hit === undefined) {
                return <span key={si}>{sentence}</span>;
              }
              const clickable = Boolean(onClaimClick);
              return (
                <span
                  key={si}
                  className={`rounded-sm px-0.5 ${STATUS_CLASS[hit.status] || ""} ${
                    clickable ? "cursor-pointer hover:brightness-125" : ""
                  }`}
                  title={`FactTrace: ${hit.status.replace("_", " ").toLowerCase()} — click to view evidence`}
                  onClick={clickable ? () => onClaimClick?.(hit.index) : undefined}
                >
                  {sentence}
                </span>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}

function FieldRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="py-3 border-b border-line-subtle last:border-0">
      <div className="text-[12px] text-ink-3 uppercase tracking-wide mb-1">{label}</div>
      {children}
    </div>
  );
}

const SKIP_KEYS = new Set([
  "language_note", "srt_ready", "_quality", "mode", "variant", "slide_count", "claims", "sources",
]);

export function OutputRenderer({
  content,
  claims,
  onClaimClick,
}: {
  content: Record<string, unknown>;
  claims?: GroundingClaim[];
  onClaimClick?: (index: number) => void;
}) {
  const claimMap = useMemo(() => {
    if (!claims || claims.length === 0) return null;
    const m = new Map<string, GroundingClaim>();
    for (const c of claims) {
      const key = norm(c.claim);
      if (key && !m.has(key)) m.set(key, c);
    }
    return m.size > 0 ? m : null;
  }, [claims]);

  const entries = Object.entries(content).filter(([k]) => !SKIP_KEYS.has(k));

  return (
    <div className="flex flex-col">
      {entries.map(([key, value]) => {
        if (value == null || value === "" || (Array.isArray(value) && value.length === 0)) return null;
        const label = key.replace(/_/g, " ");

        if (key === "sections" && Array.isArray(value)) {
          return (
            <div key={key} className="flex flex-col gap-5 py-2">
              {value.map((s: Record<string, unknown>, i: number) => (
                <div key={i}>
                  <h3 className="text-[15px] font-semibold text-ink">{String(s.heading ?? s.title ?? "")}</h3>
                  <div className="mt-1.5">
                    <TextBlock text={String(s.body ?? s.content ?? "")} claimMap={claimMap} onClaimClick={onClaimClick} />
                  </div>
                </div>
              ))}
            </div>
          );
        }

        if (key === "slides" && Array.isArray(value)) {
          return (
            <div key={key} className="flex flex-col gap-4 py-2">
              {value.map((s: Record<string, unknown>, i: number) => (
                <div key={i} className="bg-elevated border border-line-subtle rounded-card p-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-[14px] font-semibold">{String(s.title ?? "")}</h3>
                    <span className="text-[11px] text-ink-3">Slide {String(s.slide_number ?? i + 1)}</span>
                  </div>
                  <div className="mt-1.5">
                    <TextBlock text={String(s.content ?? "")} claimMap={claimMap} onClaimClick={onClaimClick} />
                  </div>
                  <div className="mt-2 text-[12px] text-ink-3">Visual: {String(s.visual_recommendation ?? "")}</div>
                  {s.speaker_notes ? <div className="mt-1 text-[12px] text-ink-3">Notes: {String(s.speaker_notes)}</div> : null}
                </div>
              ))}
            </div>
          );
        }

        if (key === "variants" && Array.isArray(value)) {
          return (
            <div key={key} className="flex flex-col gap-4 py-2">
              {value.map((v: Record<string, unknown>, i: number) => (
                <div key={i} className="bg-elevated border border-line-subtle rounded-card p-4">
                  <div className="text-[12px] text-ink-3 mb-2">Variant {String(v.variant ?? i + 1)}</div>
                  <div className="text-[14px] font-medium text-ink">{String(v.hook ?? "")}</div>
                  <div className="mt-2">
                    <TextBlock text={String(v.body ?? "")} claimMap={claimMap} onClaimClick={onClaimClick} />
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {(v.hashtags as string[] | undefined)?.map((h) => (
                      <span key={h} className="text-[12px] text-accent">{h}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          );
        }

        if (key === "posts" && Array.isArray(value)) {
          return (
            <div key={key} className="flex flex-col gap-2.5 py-2">
              {value.map((p: string, i: number) => (
                <div key={i} className="bg-elevated border border-line-subtle rounded-card p-3.5">
                  <div className="text-[11px] text-ink-3 mb-1">{i + 1}/{value.length} · {p.length}/280</div>
                  <TextBlock text={p} claimMap={claimMap} onClaimClick={onClaimClick} />
                </div>
              ))}
            </div>
          );
        }

        if (key === "scenes" && Array.isArray(value)) {
          return (
            <div key={key} className="flex flex-col gap-3 py-2">
              {value.map((s: Record<string, unknown>, i: number) => (
                <div key={i} className="bg-elevated border border-line-subtle rounded-card p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-[13px] font-semibold">Scene {String(s.scene_number ?? i + 1)}</span>
                    <span className="text-[11px] text-ink-3">{String(s.duration_seconds ?? "")}s · {String(s.transition ?? "")}</span>
                  </div>
                  <div className="mt-2 text-[13px] text-ink-2">{String(s.visual_description ?? "")}</div>
                  <div className="mt-1.5 text-[13px] text-ink">Narration: <TextBlock text={String(s.narration ?? "")} claimMap={claimMap} onClaimClick={onClaimClick} /></div>
                  <div className="mt-1 text-[12px] text-ink-3">On-screen: {String(s.on_screen_text ?? "")}</div>
                </div>
              ))}
            </div>
          );
        }

        if (key === "key_statistics" && Array.isArray(value)) {
          return (
            <FieldRow key={key} label={label}>
              <div className="grid grid-cols-2 gap-2">
                {value.map((s: Record<string, unknown>, i: number) => (
                  <div key={i} className="bg-elevated border border-line-subtle rounded-card px-3.5 py-3">
                    <div className="text-lg font-semibold text-accent">{String(s.value ?? "")}</div>
                    <div className="text-[12px] text-ink-2 mt-0.5">{String(s.label ?? "")}</div>
                  </div>
                ))}
              </div>
            </FieldRow>
          );
        }

        if (Array.isArray(value)) {
          const allStrings = value.every((v) => typeof v === "string");
          return (
            <FieldRow key={key} label={label}>
              {allStrings ? (
                <ul className="flex flex-col gap-1.5">
                  {value.map((v, i) => (
                    <li key={i} className="text-[14px] text-ink-2 leading-relaxed">
                      • <TextBlock text={String(v)} claimMap={claimMap} onClaimClick={onClaimClick} />
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="flex flex-col gap-2">
                  {value.map((v, i) => (
                    <div key={i} className="bg-elevated border border-line-subtle rounded-card px-3.5 py-2.5 text-[13px] text-ink-2">
                      {Object.entries(v as Record<string, unknown>)
                        .filter(([vk, vv]) => vv && !["source_id", "chunk_index"].includes(vk))
                        .map(([vk, vv]) => (
                          <span key={vk} className="mr-3">
                            <span className="text-ink-3">{vk.replace(/_/g, " ")}: </span>
                            <span className="text-ink">{String(vv).slice(0, 120)}</span>
                          </span>
                        ))}
                    </div>
                  ))}
                </div>
              )}
            </FieldRow>
          );
        }

        if (typeof value === "object") {
          return (
            <FieldRow key={key} label={label}>
              <div className="text-[13px] text-ink-2 leading-relaxed">
                {Object.entries(value as Record<string, unknown>).map(([vk, vv]) => (
                  <div key={vk}>
                    <span className="text-ink-3">{vk.replace(/_/g, " ")}: </span>
                    <span className="text-ink">{typeof vv === "string" ? vv : JSON.stringify(vv)}</span>
                  </div>
                ))}
              </div>
            </FieldRow>
          );
        }

        const long = String(value).length > 120;
        return (
          <FieldRow key={key} label={label}>
            {long ? (
              <TextBlock text={String(value)} claimMap={claimMap} onClaimClick={onClaimClick} />
            ) : (
              <div className="text-[14px] text-ink">{String(value)}</div>
            )}
          </FieldRow>
        );
      })}
    </div>
  );
}
