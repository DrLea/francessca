// Small reusable shadcn/ui-style primitives (Tailwind only).
import clsx from "clsx";
import React from "react";

export function Button({
  className,
  variant = "primary",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
}) {
  const variants = {
    primary: "bg-brand text-white hover:bg-brand-dark",
    secondary: "bg-slate-700 text-white hover:bg-slate-800",
    ghost: "bg-transparent text-slate-700 hover:bg-slate-100",
  } as const;
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition disabled:opacity-50",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}

export function Input({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={clsx(
        "w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand focus:ring-1 focus:ring-brand",
        className,
      )}
      {...props}
    />
  );
}

export function Card({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={clsx(
        "rounded-lg border border-slate-200 bg-white p-6 shadow-sm",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-block rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
      {children}
    </span>
  );
}

export function ProgressBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
      <div
        className={clsx("h-full rounded-full", pct > 90 ? "bg-red-500" : "bg-brand")}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-400">
      <span className="h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-brand" />
      {label}
    </div>
  );
}

export function Disclaimer() {
  return (
    <p className="mt-4 text-xs text-slate-500">
      Francessca is not a lawyer and does not provide legal advice. Always have
      documents reviewed by a qualified lawyer.
    </p>
  );
}
