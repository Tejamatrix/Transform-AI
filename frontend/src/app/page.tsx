"use client";

import Link from "next/link";
import { useState } from "react";

const FLOW = ["Ingest", "Understand", "Blueprint", "Plan", "Generate", "Validate", "Review", "Export"];

const FLOW_INFO: Record<string, { title: string; body: string; points: string[] }> = {
  Ingest: {
    title: "Bring in any source",
    body: "Nine source types, one pipeline. Upload documents, spreadsheets, code files, images or videos — or paste text and URLs. Everything is extracted, chunked and indexed for grounding.",
    points: ["PDF, DOCX, TXT, CSV, URLs and pasted text", "Images via OCR, videos via Whisper transcript + frame text", "30+ programming languages — the AI explains what code does"],
  },
  Understand: {
    title: "The AI reads it properly",
    body: "The content understanding engine detects domain, intent and structure — whether it's an incident report, a policy document, a dataset or an application's source code.",
    points: ["Domain + intent detection", "Entities (10 types), key facts, statistics", "Spoken video content and code behaviour, explained"],
  },
  Blueprint: {
    title: "One blueprint. Every output.",
    body: "The understanding is distilled into a Transformation Blueprint — a structured, editable intermediate representation. Every deliverable is generated from this single source of truth, so formats can never contradict each other.",
    points: ["Domain, entities, key facts, timeline, risks, confidence", "Editable by the operator before generation", "Versioned — consistency is architectural, not hoped-for"],
  },
  Plan: {
    title: "You stay in control",
    body: "Based on the detected domain and intent, the analyzer recommends suitable outputs. Then you configure exactly what you need — no black boxes.",
    points: ["Recommended outputs pre-selected for you", "Audience, tone, language, detail, objective, style", "Any combination of the 7 formats, one operation"],
  },
  Generate: {
    title: "Every deliverable, one operation",
    body: "All selected generators run from the same blueprint plus retrieved evidence — an executive summary, an advisory, a thread and a video script will always tell the same story.",
    points: ["7 formats written by the live LLM", "Grounded in retrieved source evidence", "Structured JSON schemas, auto-repaired and validated"],
  },
  Validate: {
    title: "Every claim gets checked",
    body: "Generated claims are compared against retrieved evidence and classified: verified, partially supported or unsupported. Nothing hallucinated slips through silently.",
    points: ["Color-coded grounding overlay in the output", "Click a claim â†’ exact source page and quote", "Conflicts between sources flagged for human review"],
  },
  Review: {
    title: "Human judgment, built in",
    body: "Nothing is locked. Edit any section, shorten, expand, change tone or audience, rewrite — or regenerate entirely. Every change is versioned.",
    points: ["Inline edits with instant preview", "Version history (v1, v2, v3â€¦) with actions", "Regenerate from the same blueprint anytime"],
  },
  Export: {
    title: "Production-ready files",
    body: "Download deliverables in the format your audience needs — a real PowerPoint deck, a Word advisory, subtitles for your video editor, structured JSON for integrations.",
    points: ["PPTX, DOCX, PDF, HTML, JSON, CSV, TXT, SRT, MD", "Video packages include storyboard, script and subtitles", "Clean layouts — presentation-ready, not raw dumps"],
  },
};

const OUTPUTS = [
  ["Executive Summary", "Board-ready overview with findings, risks and recommendations."],
  ["Security Advisory", "Structured advisory with severity, indicators and mitigations."],
  ["LinkedIn Post", "Professional variants with hooks, insights and hashtags."],
  ["X Thread", "Platform-aware threads within character limits."],
  ["Presentation", "5-10 slide structure with speaker notes — exported as real PPTX."],
  ["Infographic", "Complete visual specification with hierarchy and layout."],
  ["Video Package", "Scene-by-scene storyboard, script and subtitles."],
];

const TRUST = [
  ["FactTrace", "Every important claim links back to the exact page and paragraph it came from."],
  ["Fact validation", "Claims are checked against retrieved evidence: verified, partial or unsupported."],
  ["Human review", "Edit, regenerate, shorten, expand or change tone — with full version history."],
];

export default function Landing() {
  const [activeStep, setActiveStep] = useState("Blueprint");
  const info = FLOW_INFO[activeStep];

  return (
    <div className="min-h-screen bg-bg text-ink overflow-x-clip">
      {/* minimal modern navigation */}
      <nav className="sticky top-0 z-40 bg-bg/80 backdrop-blur border-b border-line-subtle">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="text-[17px] font-bold tracking-tight">
            Pr<span className="text-accent">ism</span>
          </Link>
          <div className="hidden md:flex items-center gap-7 text-[14px] text-ink-2">
            <a href="#pipeline" className="hover:text-ink">How it works</a>
            <a href="#outputs" className="hover:text-ink">Outputs</a>
            <a href="#trust" className="hover:text-ink">Trust</a>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/login" className="h-10 px-4 inline-flex items-center rounded-btn text-[14px] font-medium text-ink-2 hover:text-ink">
              Sign in
            </Link>
            <Link
              href="/register"
              className="h-10 px-5 inline-flex items-center rounded-btn bg-accent text-white text-[14px] font-medium hover:bg-accent-strong shadow-soft active:scale-[0.97]"
            >
              Get started
            </Link>
          </div>
        </div>
      </nav>

      {/* HERO — organic blobs, asymmetric split */}
      <section className="relative overflow-hidden">
        {/* background blobs */}
        <div className="absolute -top-24 -left-32 w-[34rem] h-[34rem] bg-mint/25 blob" aria-hidden />
        <div className="absolute top-40 -right-40 w-[38rem] h-[38rem] bg-cream blob" style={{ animationDelay: "-8s" }} aria-hidden />
        <div className="absolute bottom-0 left-1/3 w-72 h-72 bg-highlight/70 blob" style={{ animationDelay: "-4s" }} aria-hidden />

        {/* floating geometric elements */}
        <div className="float-slow absolute top-28 right-[12%] w-10 h-10 rounded-xl bg-accent/15 rotate-12 hidden lg:block" aria-hidden />
        <div className="float-slower absolute top-64 right-[28%] w-6 h-6 rounded-full bg-mint/40 hidden lg:block" aria-hidden />
        <div className="float-slow absolute bottom-24 left-[8%] w-8 h-8 border-2 border-accent/25 rounded-lg -rotate-12 hidden lg:block" style={{ animationDelay: "-3s" }} aria-hidden />

        <div className="relative max-w-6xl mx-auto px-6 pt-20 pb-28 grid lg:grid-cols-[1.1fr_0.9fr] gap-14 items-center">
          <div className="stagger">
            <div className="inline-flex items-center gap-2 bg-mint-soft border border-mint/50 rounded-full px-4 py-1.5 text-[13px] text-accent-strong font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-accent" />
              One source. Every deliverable. Zero contradictions.
            </div>
            <h1 className="mt-6 text-4xl md:text-[3.4rem] font-bold leading-[1.08] tracking-tight text-ink">
              Turn any document into communication your{" "}
              <span className="relative inline-block">
                <span className="relative z-10 text-accent-strong">audience acts on</span>
                <span className="absolute inset-x-0 bottom-1 h-3.5 bg-highlight -z-0 rounded-full" />
              </span>
              .
            </h1>
            <p className="mt-6 text-[16px] text-ink-2 leading-relaxed max-w-xl">
              Upload reports, code, images, videos or URLs. Prism understands the content
              once, builds a validated blueprint, and generates every deliverable from it —
              with every claim traceable to its source.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link
                href="/register"
                className="h-12 px-7 inline-flex items-center rounded-btn bg-accent text-white font-medium hover:bg-accent-strong shadow-lift active:scale-[0.97]"
              >
                Start transforming free
              </Link>
              <Link
                href="/login"
                className="h-12 px-7 inline-flex items-center rounded-btn bg-surface border border-line text-ink font-medium hover:border-accent/40 shadow-soft active:scale-[0.97]"
              >
                Sign in
              </Link>
            </div>
            <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-2 text-[13px] text-ink-3">
              <span className="flex items-center gap-1.5"><span className="text-accent">âœ“</span> 9 source types</span>
              <span className="flex items-center gap-1.5"><span className="text-accent">âœ“</span> 7 output formats</span>
              <span className="flex items-center gap-1.5"><span className="text-accent">âœ“</span> Works offline</span>
            </div>
          </div>

          {/* product mockup card — clean, floating */}
          <div className="relative hidden lg:block">
            <div className="float-slower absolute -top-6 -right-4 w-24 h-24 bg-mint blob opacity-70" aria-hidden />
            <div className="relative bg-surface rounded-card border border-line-subtle shadow-lift p-6 rotate-1">
              <div className="flex items-center gap-1.5 mb-4">
                <span className="w-2.5 h-2.5 rounded-full bg-[#F0C9C5]" />
                <span className="w-2.5 h-2.5 rounded-full bg-highlight" />
                <span className="w-2.5 h-2.5 rounded-full bg-mint" />
              </div>
              <div className="text-[12px] text-ink-3 mb-1">TRANSFORMATION BLUEPRINT</div>
              <div className="text-[15px] font-semibold">Cybersecurity Incident — March 2026</div>
              <div className="mt-4 grid grid-cols-2 gap-2 text-[12px]">
                <div className="bg-mint-soft rounded-xl px-3 py-2"><span className="text-ink-3">Domain</span><div className="font-semibold text-accent-strong">Cybersecurity</div></div>
                <div className="bg-highlight rounded-xl px-3 py-2"><span className="text-ink-3">Intent</span><div className="font-semibold">Alert</div></div>
                <div className="bg-highlight rounded-xl px-3 py-2"><span className="text-ink-3">Entities</span><div className="font-semibold">18</div></div>
                <div className="bg-mint-soft rounded-xl px-3 py-2"><span className="text-ink-3">Key facts</span><div className="font-semibold">24</div></div>
              </div>
              <div className="mt-4 flex flex-col gap-2">
                {["The incident affected 14 departments.", "38,000 customer records exposed.", "Mitigation completed by 20 March."].map((t, i) => (
                  <div key={i} className="flex items-center gap-2 text-[12.5px] text-ink-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${i === 2 ? "bg-accent" : "bg-success"}`} />
                    {t}
                    <span className="ml-auto text-[10.5px] text-ink-3 border border-line-subtle rounded-full px-2 py-0.5">p.{7 + i}</span>
                  </div>
                ))}
              </div>
            </div>
            {/* mini stat card overlapping */}
            <div className="absolute -bottom-6 -left-8 bg-surface border border-line-subtle rounded-card shadow-lift px-4 py-3 -rotate-2">
              <div className="text-[11px] text-ink-3">FACT VALIDATION</div>
              <div className="text-[15px] font-bold text-success">31 verified âœ“</div>
              <div className="text-[12px] text-warn">2 partial Â· 1 unsupported</div>
            </div>
            {/* floating mint chip */}
            <div className="float-slow absolute -top-8 -left-10 bg-mint text-white text-[12px] font-semibold rounded-2xl px-4 py-2.5 shadow-lift rotate-3">
              âœ“ Blueprint ready
            </div>
          </div>
        </div>
      </section>

      {/* PIPELINE — asymmetric band */}
      <section id="pipeline" className="relative py-20 bg-surface border-y border-line-subtle overflow-hidden">
        <div className="absolute -bottom-32 -right-24 w-96 h-96 bg-mint-soft blob opacity-80" aria-hidden />
        <div className="relative max-w-6xl mx-auto px-6">
          <div className="grid lg:grid-cols-[0.9fr_1.1fr] gap-12 items-start">
            {/* LEFT — live info panel for the active step */}
            <div key={activeStep} className="anim-fade-in-up lg:sticky lg:top-28">
              <div className="text-[13px] font-semibold text-accent-strong tracking-wide uppercase">
                How it works
              </div>
              <div className="mt-3 flex items-center gap-3">
                <span className="w-10 h-10 rounded-2xl bg-mint text-white flex items-center justify-center font-bold text-[15px] shadow-soft">
                  {String(FLOW.indexOf(activeStep) + 1).padStart(2, "0")}
                </span>
                <h2 className="text-2xl font-bold tracking-tight leading-snug">{info.title}</h2>
              </div>
              <p className="mt-4 text-ink-2 text-[15px] leading-relaxed">{info.body}</p>
              <ul className="mt-5 flex flex-col gap-2.5">
                {info.points.map((pt) => (
                  <li key={pt} className="flex items-start gap-2.5 text-[13.5px] text-ink-2">
                    <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
                    {pt}
                  </li>
                ))}
              </ul>
              <div className="mt-7 h-1 w-full bg-line-subtle rounded-full overflow-hidden">
                <div
                  className="h-full bg-accent rounded-full"
                  style={{
                    width: `${((FLOW.indexOf(activeStep) + 1) / FLOW.length) * 100}%`,
                    transition: "width 300ms ease",
                  }}
                />
              </div>
              <div className="mt-2 text-[12px] text-ink-3">
                Step {FLOW.indexOf(activeStep) + 1} of {FLOW.length} — click any step to explore
              </div>
            </div>

            {/* RIGHT — clickable steps */}
            <div className="flex flex-col gap-2 stagger">
              {FLOW.map((step, i) => {
                const active = step === activeStep;
                return (
                  <button
                    key={step}
                    onClick={() => setActiveStep(step)}
                    className={`flex items-center gap-4 text-left px-5 py-4 rounded-2xl border active:scale-[0.98] ${
                      active
                        ? "bg-accent text-white border-accent shadow-lift"
                        : "bg-bg border-line text-ink-2 hover:border-accent/50 hover:text-ink"
                    }`}
                  >
                    <span
                      className={`w-8 h-8 rounded-xl flex items-center justify-center text-[13px] font-bold shrink-0 ${
                        active ? "bg-white/20 text-white" : "bg-elevated text-accent-strong"
                      }`}
                    >
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="text-[15px] font-medium">{step}</span>
                    <span className={`ml-auto text-lg transition-transform ${active ? "translate-x-0 opacity-100" : "-translate-x-1 opacity-0"}`}>
                      â†’
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* OUTPUTS — bento-style asymmetric grid */}
      <section id="outputs" className="relative py-24 overflow-hidden">
        <div className="absolute top-20 -left-32 w-96 h-96 bg-cream blob opacity-70" aria-hidden />
        <div className="relative max-w-6xl mx-auto px-6">
          <div className="max-w-2xl">
            <div className="text-[13px] font-semibold text-accent-strong tracking-wide uppercase">Outputs</div>
            <h2 className="mt-3 text-3xl font-bold tracking-tight">Seven deliverables. One click.</h2>
            <p className="mt-4 text-ink-2 text-[15px] leading-relaxed">
              Select any combination. All generated from the same validated understanding —
              exported as real files: PPTX, DOCX, PDF, SRT and more.
            </p>
          </div>
          <div className="mt-12 grid md:grid-cols-3 gap-4 stagger">
            {OUTPUTS.map(([title, desc], i) => (
              <div
                key={title}
                className={`lift bg-surface border border-line-subtle rounded-card p-6 shadow-soft ${
                  i === 0 ? "md:col-span-2 bg-gradient-to-br from-surface to-mint-soft" : ""
                }`}
              >
                <div className="w-9 h-9 rounded-xl bg-mint text-white flex items-center justify-center font-bold text-[15px] mb-4">
                  {String(i + 1).padStart(2, "0")}
                </div>
                <div className="text-[16px] font-semibold">{title}</div>
                <div className="mt-1.5 text-[13.5px] text-ink-2 leading-relaxed">{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* TRUST — cream band */}
      <section id="trust" className="relative py-24 bg-cream/60 border-y border-line-subtle overflow-hidden">
        <div className="absolute -top-24 right-[10%] w-80 h-80 bg-mint/50 blob" aria-hidden />
        <div className="relative max-w-6xl mx-auto px-6">
          <div className="max-w-2xl">
            <div className="text-[13px] font-semibold text-accent-strong tracking-wide uppercase">Trust</div>
            <h2 className="mt-3 text-3xl font-bold tracking-tight">Grounded in your sources.</h2>
            <p className="mt-4 text-ink-2 text-[15px] leading-relaxed">
              AI that shows its work. Every generated claim is checked against the evidence
              and traceable to where it came from.
            </p>
          </div>
          <div className="mt-12 grid md:grid-cols-3 gap-4 stagger">
            {TRUST.map(([title, desc]) => (
              <div key={title} className="lift bg-surface border border-line-subtle rounded-card p-6 shadow-soft">
                <div className="text-[16px] font-semibold">{title}</div>
                <div className="mt-1.5 text-[13.5px] text-ink-2 leading-relaxed">{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="relative py-24 overflow-hidden">
        <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 w-[42rem] h-[42rem] bg-mint-soft blob mx-auto opacity-60" aria-hidden />
        <div className="relative max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-3xl md:text-4xl font-bold tracking-tight">
            Ready to transform how your team communicates?
          </h2>
          <p className="mt-4 text-ink-2 text-[15px]">
            From a single incident report to a full communication kit — in one operation.
          </p>
          <Link
            href="/register"
            className="mt-8 h-12 px-8 inline-flex items-center rounded-btn bg-accent text-white font-medium hover:bg-accent-strong shadow-lift active:scale-[0.97]"
          >
            Start transforming free
          </Link>
        </div>
      </section>

      <footer className="border-t border-line-subtle bg-surface">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between text-[13px] text-ink-3">
          <span>Prism — AI-powered multimodal content transformation</span>
          <span>Mint Â· Teal Â· Charcoal</span>
        </div>
      </footer>
    </div>
  );
}
