"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import {
  ProjectOut, SourceOut, Blueprint, JobOut, OUTPUT_LABELS, AUDIENCES, TONES, LANGUAGES, DETAIL_LEVELS, OBJECTIVES, STYLES,
} from "@/lib/types";
import { Card, SectionTitle, Stat } from "@/components/Card";
import { Button } from "@/components/Button";
import { Input, Textarea, Select, Field, useToast } from "@/components/Input";
import { Badge } from "@/components/Badge";

const STEPS = ["Source", "Context", "Output Selection", "Generate"];

export default function NewTransformation() {
  const router = useRouter();
  const toast = useToast();

  const [step, setStep] = useState(0);
  const [project, setProject] = useState<ProjectOut | null>(null);
  const [projectName, setProjectName] = useState("");
  const [sources, setSources] = useState<SourceOut[]>([]);
  const [blueprint, setBlueprint] = useState<Blueprint | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [config, setConfig] = useState({
    audience: "general_public",
    tone: "professional",
    language: "English",
    detail: "moderate",
    objective: "inform",
    style: "standard",
    custom_audience: "",
  });
  const [job, setJob] = useState<JobOut | null>(null);
  const [generating, setGenerating] = useState(false);

  // source inputs
  const [pasteText, setPasteText] = useState("");
  const [pasteTitle, setPasteTitle] = useState("");
  const [url, setUrl] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!project) return;
    const t = setInterval(() => {
      api<SourceOut[]>(`/api/sources?project_id=${project.id}`).then(setSources).catch(() => {});
    }, 1500);
    return () => clearInterval(t);
  }, [project]);

  async function createProjectAndSources() {
    if (!projectName.trim()) {
      toast("Give this transformation a name first.", "error");
      return;
    }
    try {
      const p = await api<ProjectOut>("/api/projects", {
        method: "POST",
        json: { name: projectName, description: "Created via New Transformation" },
      });
      setProject(p);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to create project", "error");
    }
  }

  async function addText(e: FormEvent) {
    e.preventDefault();
    if (!project || !pasteText.trim()) return;
    try {
      const s = await api<SourceOut>("/api/sources/text", {
        method: "POST",
        json: { project_id: project.id, title: pasteTitle || "Pasted text", text: pasteText },
      });
      if (s.status === "failed") {
        toast(s.error || "Could not process text", "error");
      } else {
        toast("Text source added.", "success");
        setPasteText("");
        setPasteTitle("");
      }
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to add source", "error");
    }
  }

  async function addUrl(e: FormEvent) {
    e.preventDefault();
    if (!project || !url.trim()) return;
    try {
      const s = await api<SourceOut>("/api/sources/url", {
        method: "POST",
        json: { project_id: project.id, url, title: url },
      });
      if (s.status === "failed") {
        toast(s.error || "Could not fetch URL", "error");
      } else {
        toast("URL source added.", "success");
        setUrl("");
      }
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to add URL", "error");
    }
  }

  async function addFile(file: File) {
    if (!project) return;
    const form = new FormData();
    form.append("project_id", project.id);
    form.append("file", file);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/sources/upload`,
        { method: "POST", body: form, headers: { Authorization: `Bearer ${localStorage.getItem("tai_token")}` } }
      );
      const data = await res.json();
      if (!res.ok) {
        toast(data.detail || "Upload failed", "error");
      } else if (data.status === "failed") {
        toast(data.error || "Could not process file", "error");
      } else {
        toast(`${file.name} processed.`, "success");
      }
    } catch {
      toast("Upload failed", "error");
    }
  }

  async function downloadTranscript(sourceId: string, title: string) {
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/sources/${sourceId}/transcript`,
        { headers: { Authorization: `Bearer ${localStorage.getItem("tai_token")}` } }
      );
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        toast(j.detail || "No transcript available for this video.", "error");
        return;
      }
      const j = await res.json();
      const blob = new Blob([j.transcript], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `transcript_${title.replace(/\.[^.]+$/, "")}.txt`;
      a.click();
      URL.revokeObjectURL(url);
      toast("Transcript downloaded.", "success");
    } catch {
      toast("Could not download transcript.", "error");
    }
  }

  async function analyze() {
    if (!project) return;
    const ready = sources.filter((s) => s.status === "ready");
    if (ready.length === 0) {
      toast("Add at least one source first.", "error");
      return;
    }
    setAnalyzing(true);
    try {
      const bp = await api<Blueprint>(`/api/analysis/${project.id}`, { method: "POST" });
      setBlueprint(bp);
      setSelected(bp.content.recommended_outputs || []);
      setStep(1);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Analysis failed", "error");
    } finally {
      setAnalyzing(false);
    }
  }

  function toggleOutput(t: string) {
    setSelected((cur) => (cur.includes(t) ? cur.filter((x) => x !== t) : [...cur, t]));
  }

  async function generate() {
    if (!project || !blueprint) return;
    if (selected.length === 0) {
      toast("Select at least one output format.", "error");
      return;
    }
    setGenerating(true);
    try {
      const j = await api<JobOut>("/api/generate", {
        method: "POST",
        json: { project_id: project.id, blueprint_id: blueprint.id, outputs: selected, configuration: config },
      });
      setJob(j);
      const poll = setInterval(async () => {
        try {
          const cur = await api<JobOut>(`/api/generate/job/${j.id}`);
          setJob(cur);
          if (cur.status === "completed") {
            clearInterval(poll);
            router.push(`/dashboard/review/${project.id}`);
          } else if (cur.status === "failed") {
            clearInterval(poll);
            toast(cur.detail || "Generation failed. You can retry.", "error");
            setGenerating(false);
          }
        } catch {
          clearInterval(poll);
          setGenerating(false);
        }
      }, 1000);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to start generation", "error");
      setGenerating(false);
    }
  }

  const c = blueprint?.content;
  const readyCount = sources.filter((s) => s.status === "ready").length;

  return (
    <div className="flex flex-col gap-8">
      {/* Stepper */}
      <div className="flex items-center gap-2">
        {STEPS.map((label, i) => (
          <div key={label} className="flex items-center gap-2">
            <span
              className={`px-3 py-1.5 rounded-btn text-[13px] border ${
                i === step
                  ? "bg-accent/10 text-accent border-accent/30 font-medium"
                  : i < step
                  ? "bg-elevated text-ink-2 border-line-subtle"
                  : "text-ink-3 border-transparent"
              }`}
            >
              {i + 1}. {label}
            </span>
            {i < STEPS.length - 1 && <span className="text-ink-3 text-xs">→</span>}
          </div>
        ))}
      </div>

      {/* STEP 0 — SOURCE */}
      {step === 0 && (
        <>
          {!project ? (
            <Card className="max-w-xl">
              <SectionTitle>Name this transformation</SectionTitle>
              <Field label="Project name">
                <Input
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="Cybersecurity Incident — March 2026"
                  onKeyDown={(e) => e.key === "Enter" && createProjectAndSources()}
                />
              </Field>
              <Button className="mt-4" onClick={createProjectAndSources}>
                Continue
              </Button>
            </Card>
          ) : (
            <>
              <div className="grid md:grid-cols-2 gap-4">
                <Card>
                  <SectionTitle>Paste text</SectionTitle>
                  <form onSubmit={addText} className="flex flex-col gap-3">
                    <Input value={pasteTitle} onChange={(e) => setPasteTitle(e.target.value)} placeholder="Title (e.g. Incident Report)" />
                    <Textarea
                      value={pasteText}
                      onChange={(e) => setPasteText(e.target.value)}
                      placeholder="Paste the full text of the report, advisory or article…"
                      className="min-h-36"
                    />
                    <Button type="submit" variant="secondary" disabled={!pasteText.trim()}>
                      Add text source
                    </Button>
                  </form>
                </Card>
                <Card>
                  <SectionTitle>Upload document or add URL</SectionTitle>
                  <input
                    ref={fileRef}
                    type="file"
                    accept=".pdf,.docx,.txt,.csv,.png,.jpg,.jpeg,.webp,.mp4,.mov,.webm,.avi,.mkv,.py,.js,.ts,.tsx,.jsx,.java,.c,.h,.cpp,.hpp,.cs,.go,.rs,.rb,.php,.swift,.kt,.sql,.sh,.bat,.ps1,.html,.css,.xml,.json,.yaml,.yml,.r,.scala,.lua,.dart,.ipynb"
                    className="hidden"
                    onChange={(e) => e.target.files?.[0] && addFile(e.target.files[0])}
                  />
                  <Button variant="secondary" className="w-full" onClick={() => fileRef.current?.click()}>
                    Upload document, code, image or video
                  </Button>
                  <form onSubmit={addUrl} className="flex gap-2 mt-3">
                    <Input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" />
                    <Button type="submit" variant="secondary" disabled={!url.trim()}>
                      Add
                    </Button>
                  </form>
                  <p className="text-[12px] text-ink-3 mt-3">
                    PDF, DOCX, TXT · CSV (data analysis) · code files (.py .js .java +25 more — AI
                    explains what the code does) · images (OCR) · videos (Whisper transcript + frame
                    text). Up to 25 MB. Extracted text is chunked and indexed for grounding.
                  </p>
                </Card>
              </div>

              <div>
                <SectionTitle action={<Badge tone={readyCount > 0 ? "success" : "neutral"}>{readyCount} ready</Badge>}>
                  Sources
                </SectionTitle>
                <div className="flex flex-col gap-2">
                  {sources.map((s) => (
                    <Card key={s.id} className="flex items-center justify-between">
                      <div className="min-w-0">
                        <div className="text-[14px] font-medium truncate">{s.title}</div>
                        <div className="text-[12px] text-ink-3">
                          {s.source_type.toUpperCase()} · {s.char_count.toLocaleString()} chars · {s.chunk_count} chunks
                        </div>
                        {s.status === "failed" && <div className="text-[12px] text-error mt-1">{s.error}</div>}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {s.source_type === "video" && s.status === "ready" && (
                          <button
                            onClick={() => downloadTranscript(s.id, s.title)}
                            className="px-2.5 py-1.5 rounded-btn border border-line-subtle text-[12px] text-ink-2 hover:border-line hover:text-ink"
                          >
                            Transcript
                          </button>
                        )}
                        <Badge tone={s.status === "ready" ? "success" : s.status === "failed" ? "error" : "warn"}>
                          {s.status}
                        </Badge>
                      </div>
                    </Card>
                  ))}
                  {sources.length === 0 && (
                    <Card className="text-center py-6 text-[13px] text-ink-3">
                      Add a source to begin. You can mix documents, URLs and pasted text.
                    </Card>
                  )}
                </div>
                <div className="flex gap-3 mt-5">
                  <Button onClick={analyze} loading={analyzing} disabled={readyCount === 0}>
                    Analyze sources
                  </Button>
                </div>
              </div>
            </>
          )}
        </>
      )}

      {/* STEP 1 — CONTEXT (blueprint review) */}
      {step === 1 && c && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Stat label="Domain" value={c.domain} tone="accent" />
            <Stat label="Intent" value={c.intent} tone="accent" />
            <Stat label="Entities" value={c.entities.length} />
            <Stat label="Key facts" value={c.key_facts.length} />
            <Stat label="Timeline events" value={c.timeline.length} />
            <Stat label="Risks" value={c.risks.length} tone={c.risks.length > 0 ? "warn" : "default"} />
            <Stat label="Conflicts" value={c.conflicts.length} tone={c.conflicts.length > 0 ? "error" : "default"} />
            <Stat label="Confidence" value={`${Math.round(c.confidence * 100)}%`} />
          </div>

          <Card>
            <SectionTitle>Summary</SectionTitle>
            <p className="text-[14px] text-ink-2 leading-relaxed">{c.summary}</p>
          </Card>

          <div className="grid md:grid-cols-2 gap-4">
            <Card>
              <SectionTitle>Key facts</SectionTitle>
              <ul className="flex flex-col gap-2">
                {c.key_facts.slice(0, 8).map((f, i) => (
                  <li key={i} className="text-[13px] text-ink-2 leading-relaxed">
                    <span className="text-ink">{f.text.slice(0, 160)}{f.text.length > 160 ? "…" : ""}</span>
                    {f.source_refs?.length > 0 && (
                      <span className="ml-1.5 text-[11px] text-accent">
                        [{f.source_refs[0].source_title.slice(0, 24)} p.{f.source_refs[0].page}]
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </Card>
            <Card>
              <SectionTitle>Timeline</SectionTitle>
              {c.timeline.length === 0 ? (
                <p className="text-[13px] text-ink-3">No chronological events detected.</p>
              ) : (
                <ul className="flex flex-col gap-2.5">
                  {c.timeline.map((t, i) => (
                    <li key={i} className="flex gap-3 text-[13px]">
                      <span className="text-accent font-medium shrink-0">{t.date}</span>
                      <span className="text-ink-2">{t.event.slice(0, 120)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            <Card>
              <SectionTitle>Risks</SectionTitle>
              {c.risks.length === 0 ? (
                <p className="text-[13px] text-ink-3">None detected.</p>
              ) : (
                <ul className="flex flex-col gap-2">
                  {c.risks.slice(0, 5).map((r, i) => (
                    <li key={i} className="text-[13px] text-ink-2">• {r.slice(0, 150)}</li>
                  ))}
                </ul>
              )}
            </Card>
            <Card>
              <SectionTitle>Recommendations</SectionTitle>
              {c.recommendations.length === 0 ? (
                <p className="text-[13px] text-ink-3">None detected.</p>
              ) : (
                <ul className="flex flex-col gap-2">
                  {c.recommendations.slice(0, 5).map((r, i) => (
                    <li key={i} className="text-[13px] text-ink-2">• {r.slice(0, 150)}</li>
                  ))}
                </ul>
              )}
            </Card>
          </div>

          {c.conflicts.length > 0 && (
            <Card className="border-warn/30">
              <SectionTitle>Conflicts detected — human review required</SectionTitle>
              {c.conflicts.map((cf, i) => (
                <div key={i} className="text-[13px] text-warn mb-2">
                  {cf.detail}
                </div>
              ))}
            </Card>
          )}

          <div className="flex gap-3">
            <Button variant="secondary" onClick={() => setStep(0)}>Back to sources</Button>
            <Button onClick={() => setStep(2)}>Continue to output selection</Button>
          </div>
        </>
      )}

      {/* STEP 2 — OUTPUT SELECTION */}
      {step === 2 && (
        <>
          <div>
            <SectionTitle>Recommended by the analyzer</SectionTitle>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {Object.keys(OUTPUT_LABELS).map((t) => {
                const rec = c?.recommended_outputs.includes(t);
                return (
                  <button
                    key={t}
                    onClick={() => toggleOutput(t)}
                    className={`h-12 px-4 rounded-btn border text-[14px] text-left active:scale-[0.97] ${
                      selected.includes(t)
                        ? "bg-accent/10 border-accent/40 text-ink font-medium"
                        : "bg-surface border-line-subtle text-ink-2 hover:border-line"
                    }`}
                  >
                    {OUTPUT_LABELS[t]}
                    {rec && <span className="block text-[11px] text-accent">Recommended</span>}
                  </button>
                );
              })}
            </div>
          </div>

          <Card className="max-w-xl">
            <SectionTitle>Configuration</SectionTitle>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Field label="Audience">
                <Select value={config.audience} onChange={(e) => setConfig({ ...config, audience: e.target.value })}>
                  {AUDIENCES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </Select>
              </Field>
              <Field label="Tone">
                <Select value={config.tone} onChange={(e) => setConfig({ ...config, tone: e.target.value })}>
                  {TONES.map((t) => <option key={t} value={t}>{t}</option>)}
                </Select>
              </Field>
              <Field label="Language">
                <Select value={config.language} onChange={(e) => setConfig({ ...config, language: e.target.value })}>
                  {LANGUAGES.map((l) => <option key={l} value={l}>{l}</option>)}
                </Select>
              </Field>
              <Field label="Detail level">
                <Select value={config.detail} onChange={(e) => setConfig({ ...config, detail: e.target.value })}>
                  {DETAIL_LEVELS.map((d) => <option key={d} value={d}>{d.replace("_", " ")}</option>)}
                </Select>
              </Field>
              <Field label="Objective">
                <Select value={config.objective} onChange={(e) => setConfig({ ...config, objective: e.target.value })}>
                  {OBJECTIVES.map((o) => <option key={o} value={o}>{o}</option>)}
                </Select>
              </Field>
              <Field label="Content style">
                <Select value={config.style} onChange={(e) => setConfig({ ...config, style: e.target.value })}>
                  {STYLES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </Select>
              </Field>
              {config.audience === "custom" && (
                <Field label="Custom audience">
                  <Input
                    value={config.custom_audience}
                    onChange={(e) => setConfig({ ...config, custom_audience: e.target.value })}
                    placeholder="Describe your audience"
                  />
                </Field>
              )}
            </div>
          </Card>

          <div className="flex gap-3">
            <Button variant="secondary" onClick={() => setStep(1)}>Back</Button>
            <Button onClick={generate} loading={generating} disabled={selected.length === 0}>
              Generate {selected.length} selected
            </Button>
          </div>
        </>
      )}

      {/* STEP 3 — GENERATE */}
      {(step === 3 || generating) && job && (
        <Card className="max-w-xl text-center py-12">
          <div className="text-[15px] font-medium flex items-center justify-center gap-2">
            <span className="pulse-dot h-2 w-2 rounded-full bg-accent inline-block" />
            Generating outputs from the blueprint…
          </div>
          <div className="mt-6 h-2 w-full bg-input rounded-full overflow-hidden">
            <div
              className="h-full bg-accent rounded-full"
              style={{ width: `${job.progress}%`, transition: "width 400ms ease" }}
            />
          </div>
          <div className="mt-3 text-[13px] text-ink-2">
            {job.status === "completed" ? "Done." : job.detail || "Working…"} ({job.progress}%)
          </div>
        </Card>
      )}
    </div>
  );
}
