"use client";

import React, { useMemo } from "react";
import { Marked, type Token, type Tokens } from "marked";

interface MarkdownMessageProps {
  content: string;
  isUser?: boolean;
}

// Configure marked with an underline extension for <u>, <ins>, and ++text++
const customMarked = new Marked();

customMarked.use({
  extensions: [
    {
      name: "underline",
      level: "inline",
      start(src: string) {
        const match = src.match(/(<u>|<ins>|\+\+)/);
        return match ? match.index : -1;
      },
      tokenizer(src: string) {
        const rule = /^(?:<u>([\s\S]*?)<\/u>|<ins>([\s\S]*?)<\/ins>|\+\+([\s\S]*?)\+\+)/;
        const match = rule.exec(src);
        if (match) {
          const text = match[1] || match[2] || match[3] || "";
          return {
            type: "underline",
            raw: match[0],
            text: text,
            tokens: (this as any).lexer.inlineTokens(text),
          };
        }
      },
    },
  ],
});

export function MarkdownMessage({ content, isUser = false }: MarkdownMessageProps) {
  const tokens = useMemo(() => {
    try {
      return customMarked.lexer(content || "");
    } catch (e) {
      console.error("Markdown parse error:", e);
      return [];
    }
  }, [content]);

  return (
    <div className={`space-y-2 text-xs md:text-sm leading-relaxed ${isUser ? "text-white" : "text-neutral-200"}`}>
      {renderTokens(tokens, isUser)}
    </div>
  );
}

function renderTokens(tokens: Token[] | undefined, isUser: boolean): React.ReactNode {
  if (!tokens || tokens.length === 0) return null;

  return tokens.map((token, index) => renderToken(token, index, isUser));
}

function renderToken(token: any, index: number, isUser: boolean): React.ReactNode {
  switch (token.type) {
    case "heading": {
      const headingToken = token as Tokens.Heading;
      const depth = headingToken.depth;
      const children = renderTokens(headingToken.tokens, isUser);

      if (depth === 1) {
        return (
          <h1 key={index} className="text-base md:text-lg font-bold text-white mt-3.5 mb-1.5 flex items-center gap-1.5">
            {children}
          </h1>
        );
      }
      if (depth === 2) {
        return (
          <h2 key={index} className="text-sm md:text-base font-bold text-white mt-3 mb-1.5 border-b border-border-subtle/50 pb-1">
            {children}
          </h2>
        );
      }
      return (
        <h3 key={index} className="text-xs md:text-sm font-bold text-white mt-2.5 mb-1 flex items-center gap-1.5 font-mono">
          {children}
        </h3>
      );
    }

    case "paragraph": {
      const paraToken = token as Tokens.Paragraph;
      return (
        <p key={index} className="my-1 leading-relaxed">
          {renderTokens(paraToken.tokens, isUser)}
        </p>
      );
    }

    case "strong": {
      const strongToken = token as Tokens.Strong;
      return (
        <strong key={index} className={`font-bold tracking-wide ${isUser ? "text-white" : "text-white"}`}>
          {renderTokens(strongToken.tokens, isUser)}
        </strong>
      );
    }

    case "em": {
      const emToken = token as Tokens.Em;
      return (
        <em key={index} className={`italic font-normal ${isUser ? "text-white/95" : "text-neutral-300"}`}>
          {renderTokens(emToken.tokens, isUser)}
        </em>
      );
    }

    case "underline": {
      return (
        <span
          key={index}
          className={`underline underline-offset-4 decoration-crimson font-medium ${
            isUser ? "text-white" : "text-neutral-100"
          }`}
        >
          {renderTokens(token.tokens, isUser)}
        </span>
      );
    }

    case "del": {
      const delToken = token as Tokens.Del;
      return (
        <span key={index} className="line-through text-neutral-400">
          {renderTokens(delToken.tokens, isUser)}
        </span>
      );
    }

    case "codespan": {
      const codeToken = token as Tokens.Codespan;
      return (
        <code
          key={index}
          className={`px-1.5 py-0.5 rounded font-mono text-[11px] font-medium mx-0.5 ${
            isUser
              ? "bg-white/20 text-white border border-white/30"
              : "bg-neutral-950 border border-neutral-700/60 text-crimson-light"
          }`}
        >
          {codeToken.text}
        </code>
      );
    }

    case "code": {
      const codeToken = token as Tokens.Code;
      return (
        <div
          key={index}
          className="my-2.5 rounded-lg border border-border-subtle bg-neutral-950 overflow-hidden font-mono text-xs shadow-md"
        >
          {codeToken.lang && (
            <div className="px-3 py-1 bg-neutral-900 border-b border-border-subtle text-[10px] text-neutral-400 uppercase tracking-wider flex justify-between items-center font-mono">
              <span>{codeToken.lang}</span>
              <span className="text-[9px] text-neutral-500 font-mono">CODE</span>
            </div>
          )}
          <pre className="p-3 overflow-x-auto text-neutral-200 leading-relaxed font-mono text-[11px]">
            <code>{codeToken.text}</code>
          </pre>
        </div>
      );
    }

    case "list": {
      const listToken = token as Tokens.List;
      if (listToken.ordered) {
        return (
          <ol key={index} start={listToken.start || 1} className="my-1.5 space-y-1.5 pl-1">
            {listToken.items.map((item, itemIdx) => (
              <li key={itemIdx} className="flex items-start gap-2">
                <span className="h-4 min-w-4 px-1 rounded bg-neutral-900 border border-neutral-700/60 text-crimson-light text-[10px] font-mono font-bold flex items-center justify-center shrink-0 mt-0.5">
                  {(listToken.start || 1) + itemIdx}
                </span>
                <div className="flex-1 leading-relaxed">
                  {renderTokens(item.tokens, isUser)}
                </div>
              </li>
            ))}
          </ol>
        );
      }

      return (
        <ul key={index} className="my-1.5 space-y-1 pl-1">
          {listToken.items.map((item, itemIdx) => (
            <li key={itemIdx} className="flex items-start gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-crimson mt-1.5 shrink-0" />
              <div className="flex-1 leading-relaxed">
                {renderTokens(item.tokens, isUser)}
              </div>
            </li>
          ))}
        </ul>
      );
    }

    case "list_item": {
      const itemToken = token as Tokens.ListItem;
      return (
        <div key={index} className="leading-relaxed">
          {renderTokens(itemToken.tokens, isUser)}
        </div>
      );
    }

    case "blockquote": {
      const bqToken = token as Tokens.Blockquote;
      return (
        <blockquote
          key={index}
          className="border-l-2 border-crimson pl-3 py-1 my-2 text-neutral-300 italic bg-crimson/5 rounded-r text-xs"
        >
          {renderTokens(bqToken.tokens, isUser)}
        </blockquote>
      );
    }

    case "hr": {
      return <hr key={index} className="border-border-subtle/60 my-3" />;
    }

    case "space": {
      return null;
    }

    case "text": {
      const textToken = token as Tokens.Text;
      if (textToken.tokens && textToken.tokens.length > 0) {
        return <React.Fragment key={index}>{renderTokens(textToken.tokens, isUser)}</React.Fragment>;
      }
      return <React.Fragment key={index}>{textToken.text}</React.Fragment>;
    }

    case "link": {
      const linkToken = token as Tokens.Link;
      return (
        <a
          key={index}
          href={linkToken.href}
          target="_blank"
          rel="noopener noreferrer"
          className="text-crimson-light hover:text-white underline underline-offset-2 transition-colors font-medium"
        >
          {renderTokens(linkToken.tokens, isUser)}
        </a>
      );
    }

    case "html": {
      // Stripped or safe text fallback for stray html
      return null;
    }

    default:
      return (token as any).text ? <React.Fragment key={index}>{(token as any).text}</React.Fragment> : null;
  }
}
