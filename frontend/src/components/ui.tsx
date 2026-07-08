// Small reusable shadcn/ui-style primitives (Tailwind only).
import clsx from "clsx";
import React, { useEffect, useRef } from "react";
import { useT } from "@/lib/i18n";

export function Button({
  className,
  variant = "primary",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
}) {
  const variants = {
    primary: "bg-brand text-white shadow-soft hover:bg-brand-600 active:bg-brand-700",
    secondary:
      "bg-slate-800 text-white shadow-soft hover:bg-slate-900 active:bg-slate-950",
    ghost: "bg-transparent text-slate-600 hover:bg-slate-100 active:bg-slate-200",
  } as const;
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium transition-all duration-150 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50",
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
        "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 outline-none transition-shadow duration-150 focus:border-brand focus:ring-2 focus:ring-brand/20",
        className,
      )}
      {...props}
    />
  );
}

/**
 * A textarea that grows with its content (up to `maxHeightPx`), so typing a
 * longer message doesn't get cramped into a single scrolling line. Height is
 * recalculated on every keystroke and whenever `value` changes externally
 * (e.g. after the message is sent and the field is cleared).
 */
export function Textarea({
  className,
  maxHeightPx = 200,
  value,
  onInput,
  bare = false,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
  maxHeightPx?: number;
  /** Skip the built-in border/background/focus-ring — use when nesting
   * inside another element (e.g. the chat composer) that already provides
   * its own border and focus styling. */
  bare?: boolean;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);

  const resize = () => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, maxHeightPx)}px`;
  };

  useEffect(resize, [value, maxHeightPx]);

  return (
    <textarea
      ref={ref}
      value={value}
      onInput={(e) => {
        resize();
        onInput?.(e);
      }}
      rows={1}
      style={{ maxHeight: maxHeightPx }}
      className={clsx(
        "w-full resize-none text-sm text-slate-800 placeholder:text-slate-400 outline-none",
        bare
          ? "bg-transparent px-2 py-1.5"
          : "rounded-lg border border-slate-200 bg-white px-3 py-2 transition-shadow duration-150 focus:border-brand focus:ring-2 focus:ring-brand/20",
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
        "rounded-xl border border-slate-200/80 bg-white p-6 shadow-soft",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-block rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-medium text-brand-700">
      {children}
    </span>
  );
}

export function ProgressBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0;
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-100">
      <div
        className={clsx(
          "h-full rounded-full transition-all duration-300",
          pct > 90 ? "bg-red-500" : "bg-brand",
        )}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-400">
      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-200 border-t-brand" />
      {label}
    </div>
  );
}

export function Disclaimer() {
  const t = useT();
  return <p className="mt-4 text-xs leading-relaxed text-slate-400">{t("common.disclaimer")}</p>;
}
