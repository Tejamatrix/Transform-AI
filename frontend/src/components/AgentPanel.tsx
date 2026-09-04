"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { api, API_URL } from "@/lib/api";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { Input } from "@/components/Input";

type SourceRefLite = { source_title: string; page: number; paragraph: number; quote: string };
type Msg = { role: "user" | "assistant"; text: string; evidence?: SourceRefLite[] };

const SUGGESTIONS = [
  "What are the key facts?",
  "What is the timeline of events?",
  "What are the main risks?",
  "What actions are recommended?",
];

export default function AgentPanel({ projectId, onClose }: { projectId: string; onClose: () => void }) {
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "assistant",
      text: "I answer strictly from the source context retrieved for this project. Ask me anything about the analyzed material.",
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [live, setLive] = useState<boolean | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/health`)
      .then((r) => r.json())
      .then((h) => setLive(h.llm_provider === "openai+fallback" && h.llm_fallback !== "offline-only"))
      .catch(() => setLive(null));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  async function ask(question: string) {
    if (!question.trim() || busy) return;
    setMessages((m) => [...m, { role: "user", text: question }]);
    setInput("");
    setBusy(true);
    try {
      const res = await api<{ answer: string; evidence: SourceRefLite[] }>("/api/agent", {
        method: "POST",
        json: { project_id: projectId, question },
      });
      setMessages((m) => [...m, { role: "assistant", text: res.answer, evidence: res.evidence }]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: err instanceof Error ? err.message : "The assistant is unavailable. Please retry." },
      ]);
    } finally {
      setBusy(false);
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    ask(input);
  }

  return (
    <Card className="flex flex-col h-[calc(100vh-9rem)] max-h-[760px] sticky top-24 p-0 overflow-hidden">
      {/* header */}
      <div className="flex items-center justify-between px-4 h-14 border-b border-line-subtle shrink-0">
        <div>
          <div className="text-[14px] font-semibold flex items-center gap-2">
            AI Assistant
            <span
              className={`text-[9.5px] px-1.5 py-0.5 rounded-full border font-medium ${
                live
                  ? "text-success border-success/30 bg-success/10"
                  : "text-warn border-warn/30 bg-warn/10"
              }`}
              title={live ? "Live LLM generation with grounding" : "Offline extractive mode — answers quote the source directly"}
            >
              {live ? "LIVE LLM" : "OFFLINE"}
            </span>
          </div>
          <div className="text-[11px] text-ink-3">Grounded in retrieved source context</div>
        </div>
        <button
          onClick={onClose}
          className="h-8 w-8 rounded-btn text-ink-3 hover:text-ink hover:bg-elevated text-[15px]"
          aria-label="Close assistant"
        >
          ✕
        </button>
      </div>

      {/* messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-3">
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="self-end max-w-[85%] bg-accent text-white rounded-card px-3.5 py-2.5 text-[13px] leading-relaxed">
              {m.text}
            </div>
          ) : (
            <div key={i} className="self-start max-w-[92%] flex flex-col gap-2">
              <div className="bg-elevated border border-line-subtle rounded-card px-3.5 py-2.5 text-[13px] text-ink leading-relaxed">
                {m.text}
              </div>
              {m.evidence && m.evidence.length > 0 && (
                <div className="flex flex-col gap-1.5">
                  {m.evidence.map((ev, j) => (
                    <div key={j} className="bg-surface border border-line-subtle rounded-card px-3 py-2">
                      <div className="text-[10.5px] text-accent mb-0.5">
                        {ev.source_title || "Source"} · page {ev.page} · para {ev.paragraph}
                      </div>
                      <div className="text-[11.5px] text-ink-3 leading-snug line-clamp-2">&ldquo;{ev.quote}&rdquo;</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        )}
        {busy && (
          <div className="self-start bg-elevated border border-line-subtle rounded-card px-3.5 py-2.5 flex items-center gap-2">
            <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-accent" />
            <span className="text-[12px] text-ink-3">Searching source context…</span>
          </div>
        )}
      </div>

      {/* suggestions */}
      {messages.length <= 1 && (
        <div className="px-4 pb-2 flex flex-wrap gap-1.5 shrink-0">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => ask(s)}
              className="px-2.5 py-1.5 rounded-btn border border-line-subtle text-[11.5px] text-ink-2 hover:border-line hover:text-ink"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* input */}
      <form onSubmit={submit} className="p-3 border-t border-line-subtle flex gap-2 shrink-0">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about the source material…"
          className="!h-11 text-[13px]"
        />
        <Button type="submit" loading={busy} className="!h-11 !px-4">
          Ask
        </Button>
      </form>
    </Card>
  );
}
