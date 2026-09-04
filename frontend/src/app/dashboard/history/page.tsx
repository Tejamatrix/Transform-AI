"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { AuditEntry } from "@/lib/types";
import { Card, SectionTitle } from "@/components/Card";

export default function HistoryPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<AuditEntry[]>("/api/audit")
      .then(setEntries)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <SectionTitle>Activity history</SectionTitle>
      {loading ? (
        <div className="text-[13px] text-ink-3">Loading…</div>
      ) : entries.length === 0 ? (
        <Card className="text-center py-8 text-[13px] text-ink-3">No activity recorded yet.</Card>
      ) : (
        <div className="flex flex-col">
          {entries.map((e) => (
            <div key={e.id} className="flex items-start gap-4 py-3 border-b border-line-subtle last:border-0">
              <span className="text-[12px] text-ink-3 w-36 shrink-0 pt-0.5">
                {new Date(e.created_at).toLocaleString()}
              </span>
              <span className="text-[13px] text-ink-2 w-44 shrink-0 font-medium">{e.action.replace(/[._]/g, " ")}</span>
              <span className="text-[13px] text-ink min-w-0">{e.detail}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
