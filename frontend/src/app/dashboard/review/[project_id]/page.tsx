"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { ProjectOut, OutputOut, OUTPUT_LABELS } from "@/lib/types";
import { Card } from "@/components/Card";
import { Button } from "@/components/Button";
import { Badge } from "@/components/Badge";

export default function ReviewPage() {
  const params = useParams();
  const projectId = params.project_id as string;
  const [project, setProject] = useState<ProjectOut | null>(null);
  const [outputs, setOutputs] = useState<OutputOut[]>([]);

  useEffect(() => {
    api<ProjectOut>(`/api/projects/${projectId}`).then(setProject).catch(() => {});
    api<OutputOut[]>(`/api/generate/project/${projectId}`).then(setOutputs).catch(() => {});
  }, [projectId]);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">{project?.name || "Outputs"}</h2>
          <p className="text-[13px] text-ink-2 mt-0.5">Review, validate and export generated artefacts</p>
        </div>
        <Link href="/dashboard/new">
          <Button variant="secondary">New Transformation</Button>
        </Link>
      </div>

      {outputs.length === 0 ? (
        <Card className="text-center py-10">
          <p className="text-[14px] text-ink-2">No outputs yet for this project.</p>
          <p className="text-[13px] text-ink-3 mt-1">Run a transformation to generate deliverables from its blueprint.</p>
        </Card>
      ) : (
        <div className="grid md:grid-cols-2 gap-3 stagger">
          {outputs.map((o) => (
            <Link key={o.id} href={`/dashboard/review/${projectId}/${o.id}`}>
              <Card className="hover:border-line">
                <div className="flex items-center justify-between">
                  <span className="text-[15px] font-medium">{OUTPUT_LABELS[o.output_type] || o.output_type}</span>
                  <Badge tone="accent">v{o.current_version}</Badge>
                </div>
                <div className="text-[12px] text-ink-3 mt-1.5">
                  {new Date(o.updated_at).toLocaleString()} · {o.status}
                </div>
                <div className="text-[13px] text-ink-2 mt-2 line-clamp-2">
                  {String(o.content.title || o.content.advisory_title || o.content.deck_title || o.content.storyboard_title || "Generated artefact")}
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
