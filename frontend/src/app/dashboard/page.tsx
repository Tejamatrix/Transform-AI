"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { ProjectOut } from "@/lib/types";
import { Card, SectionTitle, Stat } from "@/components/Card";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";

export default function DashboardHome() {
  const [projects, setProjects] = useState<ProjectOut[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<ProjectOut[]>("/api/projects")
      .then(setProjects)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const totalOutputs = projects.reduce((a, p) => a + p.output_count, 0);
  const totalSources = projects.reduce((a, p) => a + p.source_count, 0);

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Recent transformations</h2>
          <p className="text-[13px] text-ink-2 mt-0.5">Sources, outputs and status at a glance</p>
        </div>
        <Link href="/dashboard/new">
          <Button>New Transformation</Button>
        </Link>
      </div>

      <div className="grid grid-cols-3 gap-4 stagger">
        <Stat label="Projects" value={projects.length} />
        <Stat label="Sources processed" value={totalSources} tone="accent" />
        <Stat label="Outputs generated" value={totalOutputs} tone="accent" />
      </div>

      <div>
        <SectionTitle
          action={
            <Link href="/dashboard/projects" className="text-[13px] text-accent hover:brightness-110">
              View all
            </Link>
          }
        >
          Projects
        </SectionTitle>
        {loading ? (
          <div className="text-[13px] text-ink-3">Loading…</div>
        ) : projects.length === 0 ? (
          <Card className="text-center py-10">
            <p className="text-[14px] text-ink-2">No transformations yet.</p>
            <p className="text-[13px] text-ink-3 mt-1">
              Start by uploading a source — an incident report, advisory, article or pasted text.
            </p>
            <Link href="/dashboard/new" className="inline-block mt-4">
              <Button variant="secondary">Create your first transformation</Button>
            </Link>
          </Card>
        ) : (
          <div className="flex flex-col gap-2 stagger">
            {projects.slice(0, 6).map((p) => (
              <Link key={p.id} href={`/dashboard/projects/${p.id}`}>
                <Card className="flex items-center justify-between hover:border-line">
                  <div>
                    <div className="text-[14px] font-medium">{p.name}</div>
                    <div className="text-[12px] text-ink-3 mt-0.5">
                      {new Date(p.created_at).toLocaleDateString()} · {p.description || "No description"}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge>{p.source_count} sources</Badge>
                    <Badge tone="accent">{p.output_count} outputs</Badge>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
