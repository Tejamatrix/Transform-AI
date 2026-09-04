"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { ProjectOut, SourceOut, Blueprint } from "@/lib/types";
import { Card, SectionTitle } from "@/components/Card";
import { Badge } from "@/components/Badge";

export default function ProjectDetailPage() {
  const params = useParams();
  const projectId = params.id as string;
  const [project, setProject] = useState<ProjectOut | null>(null);
  const [sources, setSources] = useState<SourceOut[]>([]);
  const [blueprint, setBlueprint] = useState<Blueprint | null>(null);

  useEffect(() => {
    api<ProjectOut>(`/api/projects/${projectId}`).then(setProject).catch(() => {});
    api<SourceOut[]>(`/api/sources?project_id=${projectId}`).then(setSources).catch(() => {});
    api<Blueprint[]>(`/api/analysis/${projectId}`)
      .then((bps) => setBlueprint(bps[0] || null))
      .catch(() => {});
  }, [projectId]);

  const c = blueprint?.content;

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h2 className="text-xl font-semibold">{project?.name || "Project"}</h2>
        <p className="text-[13px] text-ink-2 mt-0.5">{project?.description}</p>
      </div>

      <div>
        <SectionTitle>Sources</SectionTitle>
        <div className="flex flex-col gap-2">
          {sources.map((s) => (
            <Card key={s.id} className="flex items-center justify-between">
              <div>
                <div className="text-[14px] font-medium">{s.title}</div>
                <div className="text-[12px] text-ink-3">
                  {s.source_type.toUpperCase()} · {s.char_count.toLocaleString()} chars · {s.chunk_count} chunks
                </div>
              </div>
              <Badge tone={s.status === "ready" ? "success" : s.status === "failed" ? "error" : "warn"}>{s.status}</Badge>
            </Card>
          ))}
          {sources.length === 0 && <Card className="text-center py-6 text-[13px] text-ink-3">No sources in this project.</Card>}
        </div>
      </div>

      {c && (
        <div>
          <SectionTitle>Latest blueprint (v{blueprint?.version})</SectionTitle>
          <Card>
            <div className="flex flex-wrap gap-2 mb-3">
              <Badge tone="accent">{c.domain}</Badge>
              <Badge>{c.intent}</Badge>
              <Badge>{c.entities.length} entities</Badge>
              <Badge>{c.key_facts.length} key facts</Badge>
              <Badge>{c.timeline.length} timeline events</Badge>
            </div>
            <p className="text-[13px] text-ink-2 leading-relaxed">{c.summary}</p>
          </Card>
        </div>
      )}
    </div>
  );
}
