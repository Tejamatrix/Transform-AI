"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
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
  const [menuOpen, setMenuOpen] = useState(false);

  const logout = () => {
    clearToken();
    router.push("/login");
  };

  const navLinks = (onNavigate?: () => void) =>
    NAV.map((item) => {
      const active = item.exact ? pathname === item.href : pathname.startsWith(item.href);
      return (
        <Link
          key={item.href}
          href={item.href}
          onClick={onNavigate}
          className={`px-3 h-10 flex items-center rounded-btn text-[14px] ${
            active ? "bg-mint-soft text-accent-strong font-medium" : "text-ink-2 hover:text-ink hover:bg-elevated"
          }`}
        >
          {item.label}
        </Link>
      );
    });

  const brand = (
    <Link href="/dashboard" onClick={() => setMenuOpen(false)} className="text-[15px] font-semibold text-ink">
      Pr<span className="text-accent">ism</span>
    </Link>
  );

  return (
    <div className="min-h-screen flex bg-bg">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-56 shrink-0 glass-deep border-l-0 border-r-0 border-t-0 border-b flex-col h-screen sticky top-0">
        <div className="px-5 h-16 flex items-center border-b border-line-subtle">{brand}</div>
        <nav className="flex-1 px-3 py-4 flex flex-col gap-1">{navLinks()}</nav>
        <div className="px-3 py-4 border-t border-line-subtle">
          <div className="px-3 text-[11px] text-ink-3 mb-2">Prism v1.0</div>
          <button
            onClick={logout}
            className="w-full px-3 h-10 flex items-center rounded-btn text-[14px] text-ink-2 hover:text-ink hover:bg-elevated"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Mobile drawer */}
      {menuOpen && (
        <div className="fixed inset-0 z-50 md:hidden" role="dialog">
          <div className="absolute inset-0 bg-ink/40 backdrop-blur-sm" onClick={() => setMenuOpen(false)} />
          <aside className="absolute left-0 top-0 bottom-0 w-64 glass-deep border-y-0 border-r-0 flex flex-col anim-fade-in-up">
            <div className="px-5 h-16 flex items-center justify-between border-b border-line-subtle">
              {brand}
              <button
                onClick={() => setMenuOpen(false)}
                className="h-9 w-9 rounded-btn text-ink-3 hover:text-ink hover:bg-elevated text-[16px]"
                aria-label="Close menu"
              >
                ✕
              </button>
            </div>
            <nav className="flex-1 px-3 py-4 flex flex-col gap-1">{navLinks(() => setMenuOpen(false))}</nav>
            <div className="px-3 py-4 border-t border-line-subtle">
              <div className="px-3 text-[11px] text-ink-3 mb-2">Prism v1.0</div>
              <button
                onClick={logout}
                className="w-full px-3 h-10 flex items-center rounded-btn text-[14px] text-ink-2 hover:text-ink hover:bg-elevated"
              >
                Sign out
              </button>
            </div>
          </aside>
        </div>
      )}

      <main className="flex-1 min-w-0">
        {/* Mobile top bar */}
        <div className="md:hidden h-14 flex items-center justify-between px-4 glass border-x-0 border-t-0 border-b sticky top-0 z-40">
          {brand}
          <button
            onClick={() => setMenuOpen(true)}
            className="h-10 w-10 rounded-btn border border-line flex flex-col items-center justify-center gap-1"
            aria-label="Open menu"
          >
            <span className="block w-4 h-0.5 bg-ink rounded" />
            <span className="block w-4 h-0.5 bg-ink rounded" />
            <span className="block w-4 h-0.5 bg-ink rounded" />
          </button>
        </div>

        {/* Desktop header */}
        <header className="hidden md:flex h-16 items-center px-8 sticky top-0 glass border-x-0 border-t-0 z-10">
          <h1 className="text-[15px] font-medium text-ink-2">
            {NAV.find((n) => (n.exact ? pathname === n.href : pathname.startsWith(n.href)))?.label ||
              "Workspace"}
          </h1>
        </header>

        <div className="p-4 sm:p-6 lg:p-8 max-w-6xl mx-auto">{children}</div>
      </main>
    </div>
  );
}
