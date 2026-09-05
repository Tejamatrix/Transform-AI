"use client";

import { useEffect, useState } from "react";
import { API_URL } from "@/lib/api";import { Card, SectionTitle, Stat } from "@/components/Card";
import { Badge } from "@/components/Badge";

type Health = { status: string; app: string; llm_provider?: string; llm_model?: string; llm_fallback?: string };

export default function SettingsPage() {
  const [health, setHealth] = useState<Health | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/health`)
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  const live = health?.llm_provider === "openai+fallback";

  return (
    <div className="flex flex-col gap-8 max-w-2xl">
      <div>
        <SectionTitle>Platform status</SectionTitle>
        <div className="grid grid-cols-2 gap-4">
          <Stat label="API service" value={health ? "Operational" : "Unreachable"} tone={health ? "success" : "error"} />
          <Stat label="AI provider" value={live ? "Live LLM" : "Offline engine"} tone="accent" />
        </div>
        <p className="text-[12px] text-ink-3 mt-3">
          {live ? (
            <>
              Live generation via <code className="text-ink-2">{health?.llm_model}</code> through an
              OpenAI-compatible gateway (Groq). If the live provider is unavailable (quota, rate limit,
              timeout), requests automatically fall back to the deterministic offline engine — the
              platform never blocks.
            </>
          ) : (
            <>
              The offline AI engine runs fully deterministic analysis and generation without external
              API keys. Configure <code className="text-ink-2">LLM_PROVIDER=openai</code> with an API key
              in <code className="text-ink-2">backend/.env</code> to upgrade generation quality — no code
              changes required.
            </>
          )}
        </p>
      </div>

      <div>
        <SectionTitle>Workspace</SectionTitle>
        <Card className="flex flex-col gap-2 text-[13px] text-ink-2">
          <div className="flex items-center justify-between">
            <span>Backend</span>
            <Badge>{API_URL}</Badge>
          </div>
          <div className="flex items-center justify-between">
            <span>Health check</span>
            <Badge tone={health ? "success" : "error"}>{health ? "ok" : "offline"}</Badge>
          </div>
          <div className="flex items-center justify-between">
            <span>Session</span>
            <Badge>JWT bearer token</Badge>
          </div>
        </Card>
      </div>
    </div>
  );
}
