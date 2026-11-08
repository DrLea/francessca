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
  id,
}: {
  className?: string;
  children: React.ReactNode;
  /** Optional anchor, so a card can be deep-linked and scrolled to. */
  id?: string;
}) {
  return (
    <div
      id={id}
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

export function Select({
  className,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={clsx(
        "w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none transition-shadow duration-150 focus:border-brand focus:ring-2 focus:ring-brand/20",
        className,
      )}
      {...props}
    />
  );
}

/** A labelled form field: the label sits above whatever control is passed. */
export function Field({
  label,
  hint,
  children,
  className,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <label className={clsx("flex flex-col gap-1", className)}>
      <span className="text-xs font-medium text-slate-600">{label}</span>
      {children}
      {hint && <span className="text-[11px] text-slate-400">{hint}</span>}
    </label>
  );
}

/** Centered dialog over a dimmed page. Closes on Escape and backdrop click. */
export function Modal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-30 flex items-end justify-center bg-slate-900/40 p-0 sm:items-center sm:p-4"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="max-h-[90vh] w-full max-w-lg animate-fade-in overflow-y-auto rounded-t-2xl bg-white p-6 shadow-soft sm:rounded-2xl"
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 className="text-lg font-semibold tracking-tight text-slate-900">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="-me-2 -mt-1 rounded-lg px-2 py-1 text-xl leading-none text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
          >
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

/** 1-5 stars. Read-only by default; pass `onChange` to make it an input. */
export function Stars({
  value,
  onChange,
  size = "text-base",
}: {
  value: number;
  onChange?: (value: number) => void;
  size?: string;
}) {
  const rounded = Math.round(value);
  if (!onChange) {
    return (
      <span className={clsx("tracking-tight text-amber-400", size)} aria-label={`${value} / 5`}>
        {"★".repeat(rounded)}
        <span className="text-slate-200">{"★".repeat(5 - rounded)}</span>
      </span>
    );
  }
  return (
    <span className={clsx("inline-flex", size)} role="radiogroup">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          role="radio"
          aria-checked={n === rounded}
          aria-label={`${n} / 5`}
          // Clicking the current value again clears it.
          onClick={() => onChange(n === value ? 0 : n)}
          className={clsx(
            "px-0.5 transition-colors",
            n <= rounded ? "text-amber-400" : "text-slate-200 hover:text-amber-200",
          )}
        >
          ★
        </button>
      ))}
    </span>
  );
}

export function Tabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: { id: T; label: string; count?: number }[];
  active: T;
  onChange: (id: T) => void;
}) {
  return (
    <div className="flex gap-1 overflow-x-auto border-b border-slate-200" role="tablist">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          role="tab"
          aria-selected={tab.id === active}
          onClick={() => onChange(tab.id)}
          className={clsx(
            "-mb-px flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors",
            tab.id === active
              ? "border-brand text-brand-700"
              : "border-transparent text-slate-500 hover:text-slate-800",
          )}
        >
          {tab.label}
          {!!tab.count && (
            <span className="rounded-full bg-brand px-1.5 text-[11px] font-semibold text-white">
              {tab.count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

/** A number with a caption — the building block of every dashboard here. */
export function Stat({
  value,
  label,
  hint,
}: {
  value: React.ReactNode;
  label: string;
  hint?: string;
}) {
  return (
    <Card className="p-4">
      <div className="text-2xl font-bold tracking-tight text-slate-900">{value}</div>
      <div className="text-sm text-slate-500">{label}</div>
      {hint && <div className="mt-1 text-[11px] text-slate-400">{hint}</div>}
    </Card>
  );
}

const STATUS_TONE: Record<string, string> = {
  pending: "bg-amber-50 text-amber-700",
  new: "bg-amber-50 text-amber-700",
  accepted: "bg-brand-50 text-brand-700",
  approved: "bg-green-50 text-green-700",
  closed_won: "bg-green-50 text-green-700",
  reviewed: "bg-slate-100 text-slate-600",
  declined: "bg-slate-100 text-slate-600",
  cancelled: "bg-slate-100 text-slate-500",
  closed_lost: "bg-slate-100 text-slate-600",
  rejected: "bg-red-50 text-red-700",
};

export function StatusPill({ status, label }: { status: string; label?: string }) {
  return (
    <span
      className={clsx(
        "inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium",
        STATUS_TONE[status] ?? "bg-slate-100 text-slate-600",
      )}
    >
      {label ?? status.replace("_", " ")}
    </span>
  );
}

/** Lead quality, 0-100, as a small coloured meter. */
export function QualityMeter({ score, label }: { score: number; label?: string }) {
  const tone = score >= 70 ? "bg-green-500" : score >= 40 ? "bg-amber-400" : "bg-slate-300";
  return (
    <span className="inline-flex items-center gap-2 text-xs text-slate-500" title={label}>
      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100">
        <span className={clsx("block h-full rounded-full", tone)} style={{ width: `${score}%` }} />
      </span>
      <span className="font-medium tabular-nums text-slate-700">{score}</span>
    </span>
  );
}
