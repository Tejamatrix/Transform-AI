import Link from "next/link";

const FLOW = [
  "Ingest", "Understand", "Blueprint", "Plan", "Generate", "Validate", "Review", "Export",
];

const OUTPUTS = [
  ["Executive Summary", "Board-ready overview with findings, risks and recommendations."],
  ["Security Advisory", "Structured advisory with severity, indicators and mitigations."],
  ["LinkedIn Post", "Professional variants with hooks, insights and hashtags."],
  ["X Thread", "Platform-aware threads within character limits."],
  ["Presentation", "5-10 slide structure with speaker notes."],
  ["Infographic", "Complete visual specification with hierarchy and layout."],
  ["Video Package", "Scene-by-scene storyboard, script and subtitles."],
];

export default function Landing() {
  return (
    <div className="landing-gradient min-h-screen bg-bg text-ink">
      {/* Hero — one continuous animated wash flows behind everything */}
      <section className="border-b border-line-subtle/60">
        <div className="stagger max-w-5xl mx-auto px-6 pt-24 pb-28">
          <div className="text-[13px] text-ink-2 mb-4 tracking-wide">TransformAI</div>
          <h1 className="text-3xl md:text-4xl font-semibold leading-tight max-w-3xl">
            Turn any source material into communication your audience can act on.
          </h1>
          <p className="mt-5 text-[15px] text-ink-2 max-w-2xl leading-relaxed">
            Upload reports, documents or URLs. TransformAI builds a single validated
            understanding of your content — a Transformation Blueprint — and generates every
            deliverable from it, with every claim traceable back to the source.
          </p>
          <div className="mt-8 flex gap-3">
            <Link
              href="/register"
              className="inline-flex items-center h-12 px-6 rounded-btn bg-accent text-white font-medium hover:brightness-110 active:scale-[0.97]"
            >
              Create account
            </Link>
            <Link
              href="/login"
              className="inline-flex items-center h-12 px-6 rounded-btn border border-[#2A2A2E] text-white font-medium hover:bg-elevated active:scale-[0.97]"
            >
              Sign in
            </Link>
          </div>
        </div>
      </section>

      {/* Pipeline */}
      <section className="max-w-5xl mx-auto px-6 py-16">
        <h2 className="text-xl font-semibold">One blueprint. Every output.</h2>
        <p className="mt-2 text-ink-2 text-[15px] max-w-2xl">
          The system understands your source once. All deliverables are generated from the same
          structured blueprint — consistent facts, consistent entities, no drift.
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-2">
          {FLOW.map((step, i) => (
            <div key={step} className="flex items-center gap-2">
              <span className="px-3 py-1.5 rounded-btn bg-surface border border-line-subtle text-[13px] text-ink-2">
                {step}
              </span>
              {i < FLOW.length - 1 && <span className="text-ink-3 text-xs">→</span>}
            </div>
          ))}
        </div>
      </section>

      {/* Outputs */}
      <section className="max-w-5xl mx-auto px-6 pb-16">
        <h2 className="text-xl font-semibold">Seven deliverables. One operation.</h2>
        <div className="mt-6 grid md:grid-cols-2 lg:grid-cols-3 gap-4 stagger">
          {OUTPUTS.map(([title, desc]) => (
            <div key={title} className="lift hover:border-line bg-surface border border-line-subtle rounded-card p-4">
              <div className="text-[15px] font-medium">{title}</div>
              <div className="mt-1.5 text-[13px] text-ink-2 leading-relaxed">{desc}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Trust */}
      <section className="max-w-5xl mx-auto px-6 pb-24">
        <h2 className="text-xl font-semibold">Grounded in your sources.</h2>
        <div className="mt-6 grid md:grid-cols-3 gap-4 stagger">
          {[
            ["FactTrace", "Every important claim links back to the exact page and paragraph it came from."],
            ["Fact validation", "Generated claims are checked against retrieved evidence: verified, partially supported or unsupported."],
            ["Human review", "Edit, regenerate, shorten, expand or change tone — with full version history."],
          ].map(([title, desc]) => (
            <div key={title} className="lift hover:border-line bg-surface border border-line-subtle rounded-card p-4">
              <div className="text-[15px] font-medium">{title}</div>
              <div className="mt-1.5 text-[13px] text-ink-2 leading-relaxed">{desc}</div>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-line-subtle">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center text-[13px] text-ink-3">
          TransformAI — AI-powered multimodal content transformation
        </div>
      </footer>
    </div>
  );
}
