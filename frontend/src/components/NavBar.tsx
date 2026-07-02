"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import clsx from "clsx";
import { useAuth } from "@/lib/auth";

const LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/chat", label: "Chat" },
  { href: "/files", label: "Documents" },
  { href: "/lawyers", label: "Lawyers" },
];

export function NavBar() {
  const { user, signOut } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
        <Link href="/" className="text-lg font-bold text-brand">
          Francessca
        </Link>
        {user && (
          <div className="flex items-center gap-1">
            {LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={clsx(
                  "rounded-md px-3 py-1.5 text-sm",
                  pathname === l.href
                    ? "bg-brand text-white"
                    : "text-slate-600 hover:bg-slate-100",
                )}
              >
                {l.label}
              </Link>
            ))}
            <button
              onClick={() => {
                signOut();
                router.push("/login");
              }}
              className="ml-2 rounded-md px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-100"
            >
              Sign out
            </button>
          </div>
        )}
        {!user && (
          <Link href="/login" className="text-sm text-brand hover:underline">
            Log in
          </Link>
        )}
      </nav>
    </header>
  );
}
