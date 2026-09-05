"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearToken } from "@/lib/api";

const NAV = [
  { href: "/dashboard", label: "Dashboard", exact: true },
  { href: "/dashboard/new", label: "New Transformation" },
  { href: "/dashboard/projects", label: "Projects" },
  { href: "/dashboard/history", label: "History" },
  { href: "/dashboard/settings", label: "Settings" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  const logout = () => {
    clearToken();
    router.push("/login");
  };

  return (
    <div className="min-h-screen flex">
      <aside className="w-60 shrink-0 border-r border-line-subtle bg-bg flex flex-col h-screen sticky top-0">
        <div className="px-5 h-16 flex items-center border-b border-line-subtle">
          <Link href="/dashboard" className="text-[15px] font-semibold text-ink">
            Transform<span className="text-accent">AI</span>
          </Link>
        </div>
        <nav className="flex-1 px-3 py-4 flex flex-col gap-1">
          {NAV.map((item) => {
            const active = item.exact
              ? pathname === item.href
              : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`px-3 h-10 flex items-center rounded-btn text-[14px] ${
                  active ? "bg-elevated text-ink font-medium" : "text-ink-2 hover:text-ink hover:bg-elevated"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="px-3 py-4 border-t border-line-subtle">
          <div className="px-3 text-[11px] text-ink-3 mb-2">TransformAI v1.0</div>
          <button
            onClick={logout}
            className="w-full px-3 h-10 flex items-center rounded-btn text-[14px] text-ink-2 hover:text-ink hover:bg-elevated"
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 min-w-0">
        <header className="h-16 border-b border-line-subtle flex items-center px-8 sticky top-0 bg-bg z-10">
          <h1 className="text-[15px] font-medium text-ink-2">
            {NAV.find((n) => (n.exact ? pathname === n.href : pathname.startsWith(n.href)))?.label ||
              "Workspace"}
          </h1>
        </header>
        <div className="p-8 max-w-6xl mx-auto">{children}</div>
      </main>
    </div>
  );
}
