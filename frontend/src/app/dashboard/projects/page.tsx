"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { ProjectOut } from "@/lib/types";
import { Card, SectionTitle } from "@/components/Card";
import { Button } from "@/components/Button";
import { Input, Field, useToast } from "@/components/Input";
import { Badge } from "@/components/Badge";

export default function ProjectsPage() {
  const toast = useToast();
  const [projects, setProjects] = useState<ProjectOut[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  async function load() {
    try {
      setProjects(await api<ProjectOut[]>("/api/projects"));
    } catch {}
  }

  useEffect(() => {
    load();
  }, []);

  async function create() {
    if (!name.trim()) return;
    setCreating(true);
    try {
      await api("/api/projects", { method: "POST", json: { name, description } });
      setName("");
      setDescription("");
      toast("Project created.", "success");
      await load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to create project", "error");
    } finally {
      setCreating(false);
    }
  }

  async function remove(id: string, projectName: string) {
    if (!confirm(`Delete "${projectName}" and all of its sources and outputs?`)) return;
    try {
      await api(`/api/projects/${id}`, { method: "DELETE" });
      toast("Project deleted.", "success");
      await load();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Failed to delete", "error");
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <div>
        <SectionTitle>New workspace</SectionTitle>
        <Card className="flex gap-3 items-end">
          <div className="flex-1">
            <Field label="Project name">
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Cybersecurity Campaign" />
            </Field>
          </div>
          <div className="flex-1">
            <Field label="Description (optional)">
              <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Q1 incident communication" />
            </Field>
          </div>
          <Button onClick={create} loading={creating}>Create</Button>
        </Card>
      </div>

      <div>
        <SectionTitle>All projects</SectionTitle>
        <div className="flex flex-col gap-2 stagger">
          {projects.map((p) => (
            <Card key={p.id} className="flex items-center justify-between">
              <Link href={`/dashboard/projects/${p.id}`} className="min-w-0">
                <div className="text-[14px] font-medium hover:text-accent">{p.name}</div>
                <div className="text-[12px] text-ink-3 mt-0.5">
                  {new Date(p.created_at).toLocaleDateString()} · {p.description || "No description"}
                </div>
              </Link>
              <div className="flex items-center gap-2 shrink-0">
                <Badge>{p.source_count} sources</Badge>
                <Badge tone="accent">{p.output_count} outputs</Badge>
                <Button variant="ghost" onClick={() => remove(p.id, p.name)}>
                  Delete
                </Button>
              </div>
            </Card>
          ))}
          {projects.length === 0 && (
            <Card className="text-center py-8 text-[13px] text-ink-3">No projects yet.</Card>
          )}
        </div>
      </div>
    </div>
  );
}
