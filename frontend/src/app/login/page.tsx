"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, setToken } from "@/lib/api";
import { Button } from "@/components/Button";
import { Input, Field } from "@/components/Input";
import { useToast } from "@/components/Input";

type AuthResponse = { access_token: string };

export default function LoginPage() {
  const router = useRouter();
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api<AuthResponse>("/api/auth/login", {
        method: "POST",
        json: { email, password },
      });
      setToken(res.access_token);
      router.push("/dashboard");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Sign in failed", "error");
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <Link href="/" className="text-[17px] font-semibold">
            Transform<span className="text-accent">AI</span>
          </Link>
          <h1 className="mt-6 text-xl font-semibold">Sign in</h1>
          <p className="mt-1 text-[13px] text-ink-2">Access your transformation workspace</p>
        </div>
        <form onSubmit={submit} className="bg-surface border border-line-subtle rounded-card p-6 flex flex-col gap-4">
          <Field label="Email">
            <Input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@organisation.gov"
              autoComplete="email"
            />
          </Field>
          <Field label="Password">
            <Input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </Field>
          <Button type="submit" loading={loading} className="w-full mt-1">
            Sign in
          </Button>
          <p className="text-[13px] text-ink-2 text-center">
            No account?{" "}
            <Link href="/register" className="text-accent hover:brightness-110">
              Create one
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
