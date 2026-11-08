"use client";

import { useState } from "react";
import clsx from "clsx";
import type { ClarifyAnswer, ClarifyQuestion } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Button, Input } from "@/components/ui";

/**
 * Asks the assistant's clarifying questions one at a time.
 *
 * The whole set is collected client-side and handed back in a single
 * `onSubmit` call, so a five-question round trip still costs exactly one
 * model call. "Other" is always offered as a free-text field, whatever the
 * model proposed, and both skip buttons finish through the same path so the
 * assistant always learns what was skipped.
 */
export function ClarifyPrompt({
  questions,
  disabled = false,
  onSubmit,
}: {
  questions: ClarifyQuestion[];
  disabled?: boolean;
  onSubmit: (answers: ClarifyAnswer[]) => void;
}) {
  const { t } = useI18n();
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<(string | null)[]>(() =>
    questions.map(() => null),
  );
  const [otherOpen, setOtherOpen] = useState(false);
  const [otherText, setOtherText] = useState("");

  const current = questions[index];
  const isLast = index === questions.length - 1;
  // A question with no choices is asked as plain free text.
  const freeTextOnly = current.choices.length === 0;

  function finish(collected: (string | null)[]) {
    onSubmit(
      questions.map((q, i) => ({
        question: q.question,
        answer: collected[i] ?? null,
      })),
    );
  }

  function advance(value: string | null) {
    const next = [...answers];
    next[index] = value;
    setAnswers(next);
    setOtherOpen(false);
    setOtherText("");
    if (isLast) finish(next);
    else setIndex(index + 1);
  }

  function goBack() {
    if (index === 0) return;
    setOtherOpen(false);
    setOtherText("");
    setIndex(index - 1);
  }

  function skipAll() {
    // Everything not answered yet stays null; the assistant is told they
    // were skipped rather than left guessing why they never came back.
    finish(answers.map((a, i) => (i < index ? a : null)));
  }

  return (
    <div className="rounded-2xl border border-brand/30 bg-brand-50/40 p-4 shadow-soft">
      <div className="mb-3 flex items-center justify-between gap-3">
        <span className="text-xs font-medium text-brand-700">
          {t("clarify.progress", {
            current: index + 1,
            total: questions.length,
          })}
        </span>
        <div className="flex items-center gap-1">
          {questions.map((_, i) => (
            <span
              key={i}
              className={clsx(
                "h-1.5 w-1.5 rounded-full transition-colors",
                i < index
                  ? "bg-brand"
                  : i === index
                    ? "bg-brand/60"
                    : "bg-slate-300",
              )}
            />
          ))}
        </div>
      </div>

      <p className="mb-3 text-sm font-medium text-slate-800">
        {current.question}
      </p>

      <div className="flex flex-col gap-2">
        {current.choices.map((choice) => (
          <button
            key={choice}
            type="button"
            disabled={disabled}
            onClick={() => advance(choice)}
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-left text-sm text-slate-700 transition-colors hover:border-brand hover:bg-brand-50 disabled:pointer-events-none disabled:opacity-50"
          >
            {choice}
          </button>
        ))}

        {/* "Other" is always available — the model is told never to add one. */}
        {!otherOpen && !freeTextOnly && (
          <button
            type="button"
            disabled={disabled}
            onClick={() => setOtherOpen(true)}
            className="rounded-lg border border-dashed border-slate-300 px-3 py-2 text-left text-sm text-slate-500 transition-colors hover:border-brand hover:text-brand disabled:pointer-events-none disabled:opacity-50"
          >
            {t("clarify.other")}
          </button>
        )}

        {(otherOpen || freeTextOnly) && (
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              const value = otherText.trim();
              if (value) advance(value);
            }}
          >
            <Input
              autoFocus
              value={otherText}
              disabled={disabled}
              onChange={(e) => setOtherText(e.target.value)}
              placeholder={t("clarify.otherPlaceholder")}
            />
            <Button
              type="submit"
              disabled={disabled || !otherText.trim()}
              className="shrink-0"
            >
              {isLast ? t("clarify.finish") : t("clarify.next")}
            </Button>
          </form>
        )}
      </div>

      <div className="mt-3 flex items-center justify-between gap-2 text-xs">
        <div>
          {index > 0 && (
            <Button type="button" variant="ghost" onClick={goBack} disabled={disabled}>
              {t("clarify.back")}
            </Button>
          )}
        </div>
        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            onClick={() => advance(null)}
            disabled={disabled}
          >
            {t("clarify.skip")}
          </Button>
          <Button type="button" variant="ghost" onClick={skipAll} disabled={disabled}>
            {t("clarify.skipAll")}
          </Button>
        </div>
      </div>
    </div>
  );
}
