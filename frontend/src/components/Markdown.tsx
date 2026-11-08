"use client";

import React from "react";

/**
 * Minimal markdown renderer for assistant replies.
 *
 * The model writes **bold**, numbered steps and bullet lists; rendering the
 * raw text meant users read literal asterisks. This covers what actually
 * shows up in replies — headings, ordered/unordered lists, paragraphs,
 * bold, italic, inline code and links — and nothing else.
 *
 * It builds React elements rather than setting innerHTML, so no markup in a
 * model reply (or in a document quoted back by it) can ever be executed.
 */

// Bold first so **text** is consumed before the single-asterisk italic
// alternative can see it. No lookbehind: older Safari fails to parse it.
const INLINE_RE =
  /(\*\*[^*\n]+\*\*|__[^_\n]+__|\*[^*\n]+\*|`[^`\n]+`|\[[^\]\n]+\]\([^)\s]+\))/g;

function safeHref(href: string): string | null {
  return /^(https?:|mailto:)/i.test(href) ? href : null;
}

/** Bold / italic / code / links inside one line of text. */
function inline(text: string, keyPrefix: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  let last = 0;
  let match: RegExpExecArray | null;
  INLINE_RE.lastIndex = 0;

  while ((match = INLINE_RE.exec(text)) !== null) {
    if (match.index > last) nodes.push(text.slice(last, match.index));
    const token = match[0];
    const key = `${keyPrefix}-${match.index}`;

    if (token.startsWith("**") || token.startsWith("__")) {
      nodes.push(
        <strong key={key} className="font-semibold">
          {token.slice(2, -2)}
        </strong>,
      );
    } else if (token.startsWith("`")) {
      nodes.push(
        <code
          key={key}
          className="rounded bg-slate-200/70 px-1 py-0.5 font-mono text-[0.85em]"
        >
          {token.slice(1, -1)}
        </code>,
      );
    } else if (token.startsWith("[")) {
      const split = token.indexOf("](");
      const label = token.slice(1, split);
      const href = safeHref(token.slice(split + 2, -1));
      nodes.push(
        href ? (
          <a
            key={key}
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-2"
          >
            {label}
          </a>
        ) : (
          label
        ),
      );
    } else {
      nodes.push(<em key={key}>{token.slice(1, -1)}</em>);
    }
    last = match.index + token.length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

const BULLET_RE = /^\s*[-*•]\s+(.*)$/;
const ORDERED_RE = /^\s*(\d+)[.)]\s+(.*)$/;
const HEADING_RE = /^\s*(#{1,6})\s+(.*)$/;

export function Markdown({ text }: { text: string }) {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const blocks: React.ReactNode[] = [];

  let paragraph: string[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;

  const flushParagraph = () => {
    if (paragraph.length === 0) return;
    const key = `p-${blocks.length}`;
    blocks.push(
      <p key={key}>
        {paragraph.map((line, i) => (
          <React.Fragment key={i}>
            {i > 0 && <br />}
            {inline(line, `${key}-${i}`)}
          </React.Fragment>
        ))}
      </p>,
    );
    paragraph = [];
  };

  const flushList = () => {
    if (!list) return;
    const key = `l-${blocks.length}`;
    const items = list.items.map((item, i) => (
      <li key={i} className="ms-1">
        {inline(item, `${key}-${i}`)}
      </li>
    ));
    blocks.push(
      list.ordered ? (
        <ol key={key} className="ms-4 list-outside list-decimal space-y-1">
          {items}
        </ol>
      ) : (
        <ul key={key} className="ms-4 list-outside list-disc space-y-1">
          {items}
        </ul>
      ),
    );
    list = null;
  };

  for (const line of lines) {
    if (!line.trim()) {
      flushParagraph();
      flushList();
      continue;
    }

    const heading = HEADING_RE.exec(line);
    if (heading) {
      flushParagraph();
      flushList();
      blocks.push(
        <p key={`h-${blocks.length}`} className="font-semibold">
          {inline(heading[2], `h-${blocks.length}`)}
        </p>,
      );
      continue;
    }

    const ordered = ORDERED_RE.exec(line);
    const bullet = BULLET_RE.exec(line);
    if (ordered || bullet) {
      flushParagraph();
      const isOrdered = !!ordered;
      const content = (ordered ? ordered[2] : bullet![1]).trim();
      if (list && list.ordered !== isOrdered) flushList();
      if (!list) list = { ordered: isOrdered, items: [] };
      list.items.push(content);
      continue;
    }

    flushList();
    paragraph.push(line);
  }
  flushParagraph();
  flushList();

  return <div className="flex flex-col gap-2 leading-relaxed">{blocks}</div>;
}
