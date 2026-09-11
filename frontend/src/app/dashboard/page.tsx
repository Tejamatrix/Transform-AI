"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { ProjectOut } from "@/lib/types";
import { Card, SectionTitle } from "@/components/Card";
import { Badge } from "@/components/Badge";
import { Button } from "@/components/Button";

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

const QUICK_ACTIONS = [
  { label: "Upload Source", desc: "PDF, DOCX, CSV, code, images, video", href: "/dashboard/new#upload" },
  { label: "Paste Text", desc: "Reports, articles, free-form prompts", href: "/dashboard/new#text" },
  { label: "Import URL", desc: "Public articles and web pages", href: "/dashboard/new#url" },
];

export default function DashboardHome() {
  const router = useRouter();
  const [projects, setProjects] = useState<ProjectOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [userName, setUserName] = useState("");

  useEffect(() => {
    api<ProjectOut[]>("/api/projects")
      .then(setProjects)
      .catch(() => {})
      .finally(() => setLoading(false));
    try {
      const u = JSON.parse(atob((localStorage.getItem("tai_token") || "").split(".")[1] || "{}"));
      setUserName(u.name || "");
    } catch {}
  }, []);

  const totalOutputs = projects.reduce((a, p) => a + p.output_count, 0);

  return (
    <div className="flex flex-col gap-8">
      {/* Greeting + CTA — hero band */}
      <div className="neu p-6 sm:p-8 relative overflow-hidden">
        <div className="absolute -top-16 -right-16 w-64 h-64 rounded-full opacity-30 pointer-events-none"
             style={{ background: "linear-gradient(135deg,#5B9DF9,#2DD4BF,#A78BFA)", filter: "blur(40px)" }} aria-hidden />
        <div className="relative flex flex-col md:flex-row md:items-center gap-6 justify-between">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">
              {greeting()}{userName ? `, ${userName.split(" ")[0]}` : ""} — let&apos;s create clarity today
            </h2>
            <p className="mt-2 text-[14px] text-ink-2 max-w-xl">
              Turn reports, code, images, videos and data into audience-ready communication —
              every claim traceable to its source.
            </p>
          </div>
          <Link href="/dashboard/new" className="shrink-0">
            <button className="grad-cta text-white font-semibold h-12 px-7 rounded-btn shadow-lift active:scale-[0.97] w-full md:w-auto">
              Transform your content
            </button>
          </Link>
        </div>
      </div>

      {/* Quick actions */}
      <div>
        <SectionTitle>Quick actions</SectionTitle>
        <div className="grid sm:grid-cols-3 gap-4 stagger">
          {QUICK_ACTIONS.map((q) => (
            <Link key={q.label} href={q.href}>
              <Card className="hover:border-accent/40">
                <div className="w-10 h-10 rounded-xl grad-cta text-white flex items-center justify-center font-bold mb-3">
                  ↑
                </div>
                <div className="text-[15px] font-semibold">{q.label}</div>
                <div className="text-[12.5px] text-ink-3 mt-1 leading-relaxed">{q.desc}</div>
              </Card>
            </Link>
          ))}
        </div>
      </div>

      {/* Recent projects with indicators */}
      <div>
        <SectionTitle
          action={
            <Link href="/dashboard/projects" className="text-[13px] text-accent hover:brightness-110">
              View all
            </Link>
          }
        >
          Recent projects
        </SectionTitle>
        {loading ? (
          <div className="text-[13px] text-ink-3">Loading…</div>
        ) : projects.length === 0 ? (
          <Card className="text-center py-10">
            <p className="text-[14px] text-ink-2">No transformations yet.</p>
            <p className="text-[13px] text-ink-3 mt-1">
              Upload a source — an incident report, dataset, code file or URL.
            </p>
            <Link href="/dashboard/new" className="inline-block mt-4">
              <Button variant="secondary">Create your first transformation</Button>
            </Link>
          </Card>
        ) : (
          <div className="flex flex-col gap-2 stagger">
            {projects.slice(0, 6).map((p) => (
              <Link key={p.id} href={`/dashboard/projects/${p.id}`}>
                <Card className="flex items-center justify-between hover:border-accent/40">
                  <div className="min-w-0">
                    <div className="text-[14px] font-medium truncate">{p.name}</div>
                    <div className="text-[12px] text-ink-3 mt-0.5">
                      {new Date(p.created_at).toLocaleDateString()} · {p.description || "No description"}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {p.source_count > 0 && <Badge tone="neutral">{p.source_count} src</Badge>}
                    {p.output_count > 0 && <Badge tone="accent">{p.output_count} out</Badge>}
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
