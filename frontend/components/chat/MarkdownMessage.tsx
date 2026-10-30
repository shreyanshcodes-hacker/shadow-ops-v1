"use client";

import React from "react";

interface MarkdownMessageProps {
  content: string;
  isUser?: boolean;
}

interface InlineToken {
  type: "text" | "bold" | "italic" | "bold-italic" | "underline" | "code" | "strikethrough";
  text: string;
}

interface Block {
  type: "h1" | "h2" | "h3" | "paragraph" | "ul_item" | "ol_item" | "blockquote" | "code_block" | "hr" | "spacer";
  content?: string;
  lang?: string;
  code?: string;
  number?: string;
  indent?: number;
}

// Tokenize inline markdown elements (bold, italic, bold-italic, underline, inline code, strikethrough)
const INLINE_REGEX = /(<u>[\s\S]*?<\/u>|<ins>[\s\S]*?<\/ins>|`[^`]+`|\*\*\*[\s\S]*?\*\*\*|___[\s\S]*?___|\*\*[\s\S]*?\*\*|__[\s\S]*?__|\*[^*\n]+?\*|_[^_\n]+?_|~~[\s\S]*?~~)/g;

function parseInlineTokens(text: string): InlineToken[] {
  const parts = text.split(INLINE_REGEX);
  const tokens: InlineToken[] = [];

  for (const part of parts) {
    if (!part) continue;

    // Inline Code
    if (part.startsWith("`") && part.endsWith("`") && part.length >= 2) {
      tokens.push({ type: "code", text: part.slice(1, -1) });
      continue;
    }

    // HTML Underline tag <u> or <ins>
    if ((part.startsWith("<u>") && part.endsWith("</u>")) || (part.startsWith("<ins>") && part.endsWith("</ins>"))) {
      const inner = part.startsWith("<u>") ? part.slice(3, -4) : part.slice(5, -6);
      tokens.push({ type: "underline", text: inner });
      continue;
    }

    // Bold-Italic (*** or ___)
    if ((part.startsWith("***") && part.endsWith("***") && part.length >= 6) ||
        (part.startsWith("___") && part.endsWith("___") && part.length >= 6)) {
      tokens.push({ type: "bold-italic", text: part.slice(3, -3) });
      continue;
    }

    // Bold (** or __)
    if ((part.startsWith("**") && part.endsWith("**") && part.length >= 4) ||
        (part.startsWith("__") && part.endsWith("__") && part.length >= 4)) {
      tokens.push({ type: "bold", text: part.slice(2, -2) });
      continue;
    }

    // Italic (* or _)
    if ((part.startsWith("*") && part.endsWith("*") && part.length >= 2) ||
        (part.startsWith("_") && part.endsWith("_") && part.length >= 2)) {
      tokens.push({ type: "italic", text: part.slice(1, -1) });
      continue;
    }

    // Strikethrough (~~)
    if (part.startsWith("~~") && part.endsWith("~~") && part.length >= 4) {
      tokens.push({ type: "strikethrough", text: part.slice(2, -2) });
      continue;
    }

    // Plain Text
    tokens.push({ type: "text", text: part });
  }

  return tokens;
}

function renderInline(text: string, isUser = false): React.ReactNode {
  const tokens = parseInlineTokens(text);
  return tokens.map((token, i) => {
    switch (token.type) {
      case "code":
        return (
          <code
            key={i}
            className={`px-1.5 py-0.5 rounded font-mono text-[11px] font-medium mx-0.5 ${
              isUser
                ? "bg-white/20 text-white border border-white/30"
                : "bg-neutral-950 border border-neutral-700/60 text-crimson-light"
            }`}
          >
            {token.text}
          </code>
        );
      case "bold":
        return (
          <strong key={i} className={`font-bold tracking-wide ${isUser ? "text-white" : "text-white"}`}>
            {token.text}
          </strong>
        );
      case "italic":
        return (
          <em key={i} className={`italic font-normal ${isUser ? "text-white/90" : "text-neutral-300"}`}>
            {token.text}
          </em>
        );
      case "bold-italic":
        return (
          <strong key={i} className={`font-bold italic tracking-wide ${isUser ? "text-white" : "text-white"}`}>
            {token.text}
          </strong>
        );
      case "underline":
        return (
          <span
            key={i}
            className={`underline underline-offset-4 decoration-crimson font-medium ${
              isUser ? "text-white" : "text-neutral-100"
            }`}
          >
            {token.text}
          </span>
        );
      case "strikethrough":
        return (
          <span key={i} className="line-through text-neutral-400">
            {token.text}
          </span>
        );
      default:
        return <React.Fragment key={i}>{token.text}</React.Fragment>;
    }
  });
}

function parseBlocks(markdown: string): Block[] {
  const lines = markdown.split(/\r?\n/);
  const blocks: Block[] = [];
  let inCodeBlock = false;
  let codeBlockLang = "";
  let codeBlockLines: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Fenced Code Block delimiter
    if (line.trim().startsWith("```")) {
      if (inCodeBlock) {
        blocks.push({
          type: "code_block",
          lang: codeBlockLang,
          code: codeBlockLines.join("\n"),
        });
        inCodeBlock = false;
        codeBlockLang = "";
        codeBlockLines = [];
      } else {
        inCodeBlock = true;
        codeBlockLang = line.trim().slice(3).trim();
        codeBlockLines = [];
      }
      continue;
    }

    if (inCodeBlock) {
      codeBlockLines.push(line);
      continue;
    }

    // Horizontal Rule
    if (/^(\*{3,}|-{3,}|_{3,})$/.test(line.trim())) {
      blocks.push({ type: "hr" });
      continue;
    }

    // Headings
    if (line.startsWith("### ")) {
      blocks.push({ type: "h3", content: line.slice(4) });
      continue;
    }
    if (line.startsWith("## ")) {
      blocks.push({ type: "h2", content: line.slice(3) });
      continue;
    }
    if (line.startsWith("# ")) {
      blocks.push({ type: "h1", content: line.slice(2) });
      continue;
    }

    // Blockquote
    if (line.startsWith("> ")) {
      blocks.push({ type: "blockquote", content: line.slice(2) });
      continue;
    }

    // Unordered List item (* or - or +)
    const ulMatch = line.match(/^(\s*)([*+-])\s+(.*)$/);
    if (ulMatch) {
      const indent = Math.floor(ulMatch[1].length / 2);
      blocks.push({ type: "ul_item", indent, content: ulMatch[3] });
      continue;
    }

    // Ordered List item (1. or 2.)
    const olMatch = line.match(/^(\s*)(\d+)\.\s+(.*)$/);
    if (olMatch) {
      const indent = Math.floor(olMatch[1].length / 2);
      blocks.push({ type: "ol_item", number: olMatch[2], indent, content: olMatch[3] });
      continue;
    }

    // Empty blank line / spacer
    if (!line.trim()) {
      blocks.push({ type: "spacer" });
      continue;
    }

    // Standard paragraph line
    blocks.push({ type: "paragraph", content: line });
  }

  // Handle unclosed code block if response was truncated
  if (inCodeBlock && codeBlockLines.length > 0) {
    blocks.push({
      type: "code_block",
      lang: codeBlockLang,
      code: codeBlockLines.join("\n"),
    });
  }

  return blocks;
}

export function MarkdownMessage({ content, isUser = false }: MarkdownMessageProps) {
  const blocks = parseBlocks(content);

  return (
    <div className="space-y-1 text-xs md:text-sm leading-relaxed">
      {blocks.map((block, idx) => {
        switch (block.type) {
          case "h1":
            return (
              <h1
                key={idx}
                className="text-base md:text-lg font-bold text-white mt-3.5 mb-1.5 flex items-center gap-1.5"
              >
                {renderInline(block.content || "", isUser)}
              </h1>
            );
          case "h2":
            return (
              <h2
                key={idx}
                className="text-sm md:text-base font-bold text-white mt-3 mb-1.5 border-b border-border-subtle/50 pb-1"
              >
                {renderInline(block.content || "", isUser)}
              </h2>
            );
          case "h3":
            return (
              <h3
                key={idx}
                className="text-xs md:text-sm font-bold text-white mt-2.5 mb-1 flex items-center gap-1.5 font-mono"
              >
                {renderInline(block.content || "", isUser)}
              </h3>
            );
          case "blockquote":
            return (
              <blockquote
                key={idx}
                className="border-l-2 border-crimson pl-3 py-1 my-2 text-neutral-300 italic bg-crimson/5 rounded-r text-xs"
              >
                {renderInline(block.content || "", isUser)}
              </blockquote>
            );
          case "code_block":
            return (
              <div
                key={idx}
                className="my-2.5 rounded-lg border border-border-subtle bg-neutral-950 overflow-hidden font-mono text-xs shadow-md"
              >
                {block.lang && (
                  <div className="px-3 py-1 bg-neutral-900 border-b border-border-subtle text-[10px] text-neutral-400 uppercase tracking-wider flex justify-between items-center font-mono">
                    <span>{block.lang}</span>
                    <span className="text-[9px] text-neutral-500 font-mono">CODE</span>
                  </div>
                )}
                <pre className="p-3 overflow-x-auto text-neutral-200 leading-relaxed font-mono text-[11px]">
                  <code>{block.code}</code>
                </pre>
              </div>
            );
          case "hr":
            return <hr key={idx} className="border-border-subtle/60 my-3" />;
          case "ul_item":
            return (
              <div
                key={idx}
                className={`flex items-start gap-2 my-1 ${
                  block.indent ? `ml-${Math.min(block.indent * 4, 12)}` : "ml-0.5"
                }`}
              >
                <span className="h-1.5 w-1.5 rounded-full bg-crimson mt-1.5 shrink-0" />
                <div className="flex-1 leading-relaxed">
                  {renderInline(block.content || "", isUser)}
                </div>
              </div>
            );
          case "ol_item":
            return (
              <div
                key={idx}
                className={`flex items-start gap-2 my-1.5 ${
                  block.indent ? `ml-${Math.min(block.indent * 4, 12)}` : "ml-0.5"
                }`}
              >
                <span className="h-4 min-w-4 px-1 rounded bg-neutral-900 border border-neutral-700/60 text-crimson-light text-[10px] font-mono font-bold flex items-center justify-center shrink-0 mt-0.5">
                  {block.number}
                </span>
                <div className="flex-1 leading-relaxed">
                  {renderInline(block.content || "", isUser)}
                </div>
              </div>
            );
          case "spacer":
            return <div key={idx} className="h-1.5" />;
          case "paragraph":
          default:
            return (
              <p key={idx} className="leading-relaxed my-0.5">
                {renderInline(block.content || "", isUser)}
              </p>
            );
        }
      })}
    </div>
  );
}
