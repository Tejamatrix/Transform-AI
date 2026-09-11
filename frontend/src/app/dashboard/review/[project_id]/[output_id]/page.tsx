"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, downloadFile } from "@/lib/api";
import {
  OutputOut, OutputVersion, ValidationResp, QualityScores, OUTPUT_LABELS,
} from "@/lib/types";
import { Card, Stat } from "@/components/Card";
import { Button } from "@/components/Button";
import { Badge } from "@/components/Badge";
import { Select, useToast } from "@/components/Input";
import { OutputRenderer } from "@/components/OutputRenderer";
import AgentPanel from "@/components/AgentPanel";

const CLAIM_TONE = {
  VERIFIED: "success",
  PARTIALLY_SUPPORTED: "warn",
  UNSUPPORTED: "error",
} as const;

export default function OutputDetailPage() {
  const { project_id, output_id } = useParams() as { project_id: string; output_id: string };
  const toast = useToast();

  const [output, setOutput] = useState<OutputOut | null>(null);
  const [validation, setValidation] = useState<ValidationResp>({ validated: false });
  const [quality, setQuality] = useState<QualityScores | null>(null);
  const [versions, setVersions] = useState<OutputVersion[]>([]);
  const [tab, setTab] = useState<"content" | "facttrace" | "versions">("content");
  const [busy, setBusy] = useState<string | null>(null);
  const [editTone, setEditTone] = useState("formal");
  const [openClaim, setOpenClaim] = useState<number | null>(null);
  const [agentOpen, setAgentOpen] = useState(false);
  const loadAll = useCallback(async () => {
    try {
      const o = await api<OutputOut>(`/api/generate/output/${output_id}`);
      setOutput(o);
      const [v, q, vs] = await Promise.all([
        api<ValidationResp>(`/api/validate/${output_id}`),
        api<QualityScores>(`/api/export/${output_id}/quality`, { method: "POST" }),
        api<OutputVersion[]>(`/api/generate/output/${output_id}/versions`),
      ]);
      setValidation(v);
      setQuality(q);
      setVersions(vs);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to load output", "error");
    }
  }, [output_id, toast]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  async function runValidation() {
    setBusy("validate");
    try {
      await api(`/api/validate/${output_id}`, { method: "POST" });
      toast("Validation complete.", "success");
      await loadAll();
      setTab("facttrace");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Validation failed", "error");
    } finally {
      setBusy(null);
    }
  }

  async function editAction(action: string, extra: Record<string, unknown> = {}) {
    setBusy(action);
    try {
      await api(`/api/generate/output/${output_id}/edit`, {
        method: "POST",
        json: { action, ...extra },
      });
      toast("Output updated — new version saved.", "success");
      await loadAll();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Edit failed", "error");
    } finally {
      setBusy(null);
    }
  }

  async function regenerate() {
    setBusy("regenerate");
    try {
      await api(`/api/generate/output/${output_id}/regenerate`, { method: "POST" });
      toast("Regenerated from the same blueprint.", "success");
      await loadAll();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Regeneration failed", "error");
    } finally {
      setBusy(null);
    }
  }

  async function doExport(format: string) {
    setBusy(`export-${format}`);
    try {
      await downloadFile(`/api/export/${output_id}`, { format }, `output.${format}`);
      toast(`Exported as ${format.toUpperCase()}.`, "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Export failed", "error");
    } finally {
      setBusy(null);
    }
  }

  if (!output) {
    return <div className="text-[13px] text-ink-3">Loading…</div>;
  }

  const s = validation.summary || {};
  const groundingClaims = validation.grounding?.claims || [];
  const exportFormats = [
    "md", "docx", "pdf", "html", "json", "csv", "txt",
    ...(output.output_type === "presentation" ? ["pptx"] : []),
    ...(output.output_type === "video_package" ? ["srt"] : []),
  ];

  const onClaimClick = (index: number) => {
    setOpenClaim(index);
    setTab("facttrace");
  };

  return (
    <div className="flex gap-6 items-start">
      <div className="flex-1 min-w-0 flex flex-col gap-6">
        {/* header + everything below renders inside main column */}

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link href={`/dashboard/review/${project_id}`} className="text-[12px] text-ink-3 hover:text-ink-2">
            ← All outputs
          </Link>
          <h2 className="text-xl font-semibold mt-1">{OUTPUT_LABELS[output.output_type] || output.output_type}</h2>
          <div className="flex items-center gap-2 mt-2">
            <Badge tone="accent">v{output.current_version}</Badge>
            <Badge>{String(output.config.audience || "").replace(/_/g, " ")}</Badge>
            <Badge>{String(output.config.tone || "")}</Badge>
            <Badge>{String(output.config.language || "")}</Badge>
          </div>
        </div>
        <div className="flex gap-1.5 shrink-0 flex-wrap justify-end max-w-2xl">
          <Button variant="ghost" className="!h-9 !px-3 !text-[13px] xl:hidden" onClick={() => setAgentOpen(!agentOpen)}>
            {agentOpen ? "Hide assistant" : "Ask AI"}
          </Button>
          <span className="text-[11px] text-ink-3 self-center mr-1 hidden sm:inline">Export:</span>
          {exportFormats.map((f) => (
            <Button key={f} variant="secondary" className="!h-9 !px-3 !text-[13px]" loading={busy === `export-${f}`} onClick={() => doExport(f)}>
              {f.toUpperCase()}
            </Button>
          ))}
        </div>
      </div>

      {/* Quality */}
      {quality && (
        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-3">
          <Stat label="Overall" value={`${quality.overall}%`} tone="accent" />
          <Stat label="Accuracy" value={`${quality.accuracy}%`} />
          <Stat label="Fidelity" value={`${quality.source_fidelity}%`} />
          <Stat label="Relevance" value={`${quality.relevance}%`} />
          <Stat label="Readability" value={`${quality.readability}%`} />
          <Stat label="Audience fit" value={`${quality.audience_fit}%`} />
          <Stat label="Completeness" value={`${quality.completeness}%`} />
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-line-subtle">
        {(["content", "facttrace", "versions"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 h-10 text-[14px] border-b-2 -mb-px ${
              tab === t ? "border-accent text-ink font-medium" : "border-transparent text-ink-2 hover:text-ink"
            }`}
          >
            {t === "facttrace" ? "FactTrace" : t[0].toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* CONTENT */}
      {tab === "content" && (
        <>
          <Card className="flex flex-wrap gap-2 items-center">
            <span className="text-[12px] text-ink-3 mr-1">Edit:</span>
            <Button variant="ghost" loading={busy === "shorten"} onClick={() => editAction("shorten")}>Shorten</Button>
            <Button variant="ghost" loading={busy === "expand"} onClick={() => editAction("expand")}>Expand</Button>
            <span className="w-px h-6 bg-line mx-1" />
            <Select value={editTone} onChange={(e) => setEditTone(e.target.value)} className="!h-9 !w-36 text-[13px]">
              {["professional", "formal", "neutral", "urgent", "educational", "persuasive", "technical", "conversational"].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </Select>
            <Button variant="ghost" loading={busy === "change_tone"} onClick={() => editAction("change_tone", { tone: editTone })}>
              Change tone
            </Button>
            <span className="w-px h-6 bg-line mx-1" />
            <Button variant="ghost" loading={busy === "change_audience"} onClick={() => editAction("change_audience")}>
              Adapt audience
            </Button>
            <Button variant="ghost" loading={busy === "rewrite_section"} onClick={() => editAction("rewrite_section")}>
              Rewrite
            </Button>
            <Button variant="secondary" loading={busy === "regenerate"} onClick={regenerate}>
              Regenerate
            </Button>
          </Card>
          <Card>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 mb-3 pb-3 border-b border-line-subtle">
              <span className="text-[11px] text-ink-3">FactTrace:</span>
              <span className="flex items-center gap-1.5 text-[11px] text-ink-2">
                <span className="w-4 h-0 border-b-2 border-success" /> verified
              </span>
              <span className="flex items-center gap-1.5 text-[11px] text-ink-2">
                <span className="w-4 h-0 border-b-2 border-warn" /> partial
              </span>
              <span className="flex items-center gap-1.5 text-[11px] text-ink-2">
                <span className="w-4 h-0 border-b-2 border-error" /> unsupported
              </span>
              {!validation.validated && (
                <button onClick={runValidation} className="text-[11px] text-accent hover:brightness-110">
                  run validation to see grounding
                </button>
              )}
            </div>
            <OutputRenderer
              content={output.content}
              claims={validation.validated ? groundingClaims : undefined}
              onClaimClick={onClaimClick}
            />
          </Card>
        </>
      )}

      {/* FACTTRACE */}
      {tab === "facttrace" && (
        <>
          {validation.validated ? (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Stat label="Verified" value={s.verified ?? 0} tone="success" />
                <Stat label="Partially supported" value={s.partially_supported ?? 0} tone="warn" />
                <Stat label="Unsupported" value={s.unsupported ?? 0} tone={s.unsupported ? "error" : "default"} />
                <Stat label="Total claims" value={s.total ?? 0} />
              </div>
              <div className="flex flex-col gap-2">
                {(validation.claims || []).map((c, i) => (
                  <Card key={i}>
                    <button className="w-full text-left" onClick={() => setOpenClaim(openClaim === i ? null : i)}>
                      <div className="flex items-start justify-between gap-3">
                        <span className="text-[14px] text-ink leading-relaxed">{c.claim}</span>
                        <Badge tone={CLAIM_TONE[c.status]}>{c.status.replace("_", " ")}</Badge>
                      </div>
                    </button>
                    {openClaim === i && (
                      <div className={`expand-wrap open`}>
                        <div>
                          <div className="mt-3 pt-3 border-t border-line-subtle flex flex-col gap-2">
                            <div className="text-[12px] text-ink-3">
                              Confidence {Math.round(c.confidence * 100)}% · {c.evidence.length} evidence item(s)
                            </div>
                            {c.evidence.map((e, j) => (
                              <div key={j} className="bg-elevated border border-line-subtle rounded-card p-3">
                                <div className="text-[12px] text-accent mb-1">
                                  {e.source_title || "Source"} · page {e.page} · paragraph {e.paragraph}
                                </div>
                                <div className="text-[13px] text-ink-2 leading-relaxed">&ldquo;{e.quote}&rdquo;</div>
                              </div>
                            ))}
                            {c.evidence.length === 0 && (
                              <div className="text-[12px] text-error">
                                No supporting source material found for this claim. Review before use.
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                  </Card>
                ))}
              </div>
            </>
          ) : (
            <Card className="text-center py-10">
              <p className="text-[14px] text-ink-2">This output has not been validated yet.</p>
              <Button className="mt-4" loading={busy === "validate"} onClick={runValidation}>
                Run fact validation
              </Button>
            </Card>
          )}
        </>
      )}

      {/* VERSIONS */}
      {tab === "versions" && (
        <div className="flex flex-col gap-2">
          {versions.map((v) => (
            <Card key={v.id} className="flex items-center justify-between">
              <div>
                <div className="text-[14px] font-medium">
                  v{v.version_number} · <span className="text-ink-2 font-normal">{v.action.replace(/_/g, " ")}</span>
                </div>
                <div className="text-[12px] text-ink-3 mt-0.5">{new Date(v.created_at).toLocaleString()}</div>
              </div>
              <Badge tone={v.version_number === output.current_version ? "accent" : "neutral"}>
                {v.version_number === output.current_version ? "current" : "archived"}
              </Badge>
            </Card>
          ))}
        </div>
      )}

      {/* AI assistant inline on smaller screens (side panel handles xl+) */}
      {agentOpen && (
        <div className="xl:hidden">
          <AgentPanel projectId={output.project_id} onClose={() => setAgentOpen(false)} />
        </div>
      )}
        </div>
      </div>

      {/* AI AGENT SIDE PANEL */}
      <div className="w-96 shrink-0 hidden xl:block">
        {agentOpen ? (
          <AgentPanel projectId={output.project_id} onClose={() => setAgentOpen(false)} />
        ) : (
          <Card className="sticky top-24">
            <div className="text-[14px] font-semibold">AI Assistant</div>
            <p className="text-[12px] text-ink-3 mt-1 leading-relaxed">
              Ask questions about this project&apos;s sources. Answers come only from the retrieved
              context — with citations to page and paragraph.
            </p>
            <Button className="w-full mt-4" onClick={() => setAgentOpen(true)}>
              Open assistant
            </Button>
          </Card>
        )}
      </div>
    </div>
  );
}
