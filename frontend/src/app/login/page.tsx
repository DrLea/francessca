"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { GoogleButton } from "@/components/GoogleButton";
import { Button, Card, Disclaimer, Input } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const { user, signIn } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) router.replace("/dashboard");
  }, [user, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { access_token } =
        mode === "login"
          ? await api.login({ email, password })
          : await api.register({ email, password, full_name: fullName || undefined });
      await signIn(access_token);
      router.push("/dashboard");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const onGoogle = useCallback(
    async (idToken: string) => {
      setError(null);
      try {
        const { access_token } = await api.google(idToken);
        await signIn(access_token);
        router.push("/dashboard");
      } catch (err) {
        setError((err as Error).message);
      }
    },
    [signIn, router],
  );

  return (
    <main className="mx-auto max-w-md px-6 py-16">
      <Card>
        <h1 className="mb-4 text-2xl font-semibold">
          {mode === "login" ? "Log in" : "Create account"}
        </h1>
        <form onSubmit={submit} className="flex flex-col gap-3">
          {mode === "register" && (
            <Input
              placeholder="Full name (optional)"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          )}
          <Input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" disabled={loading}>
            {loading ? "Please wait…" : mode === "login" ? "Log in" : "Sign up"}
          </Button>
        </form>

        <div className="my-4 flex items-center gap-3 text-xs text-slate-400">
          <span className="h-px flex-1 bg-slate-200" /> or <span className="h-px flex-1 bg-slate-200" />
        </div>
        <GoogleButton onCredential={onGoogle} />

        <button
          className="mt-4 text-sm text-brand underline"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "Need an account? Sign up" : "Have an account? Log in"}
        </button>
        <Disclaimer />
      </Card>
    </main>
  );
}
