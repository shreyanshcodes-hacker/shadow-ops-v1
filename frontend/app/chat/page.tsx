"use client";

import React, { useState, useRef, useEffect } from "react";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { CommandCenterShell } from "@/components/layout/CommandCenterShell";
import { useWorkspace } from "@/context/WorkspaceContext";
import { useAuth } from "@/context/AuthContext";
import { apiClient } from "@/lib/api-client";
import {
  MessageSquare,
  Send,
  Shield,
  Bot,
  User,
  Sparkles,
  Terminal,
  RotateCcw,
  AlertCircle,
  Code2,
  CheckCircle2,
  Layers,
} from "lucide-react";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  suggestedActions?: string[];
}

export default function SecurityChatPage() {
  const { activeWorkspace } = useWorkspace();
  const { profile } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome-1",
      role: "assistant",
      content:
        "### ShadowOps Sentinel Online\n\n" +
        "I am your dedicated **AI Security Analyst & Architect**, grounded in your workspace's authorized assets, static scan findings, and attack paths.\n\n" +
        "**What I can help you with:**\n" +
        "- Explain root causes and exploitation mechanics for detected vulnerabilities\n" +
        "- Provide defense-in-depth remediation code samples (Python, TypeScript, SQL, etc.)\n" +
        "- Analyze lateral movement risks and attack path choke points\n" +
        "- Formulate human-in-the-loop verification strategies\n\n" +
        "> **Safety Boundary:** All guidance is strictly analytical and defensive. I cannot deploy unauthorized changes or execute weaponized exploit payloads.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      suggestedActions: [
        "How do I fix SQL injection in our authentication service?",
        "Summarize our latest high and critical findings",
        "What is our highest risk attack path?",
        "Security best practices for API boundary protection",
      ],
    },
  ]);

  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSending]);

  const handleSend = async (messageText?: string) => {
    const textToSend = (messageText || input).trim();
    if (!textToSend || isSending) return;
    if (!activeWorkspace) {
      setError("Please select an active workspace from the sidebar to chat.");
      return;
    }

    setError(null);
    setInput("");

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsSending(true);

    try {
      // Build history for backend
      const history = messages.slice(-6).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const res = await apiClient.post<{
        reply: string;
        provider: string;
        grounded_context: any;
        suggested_actions: string[];
      }>("/ai/chat", {
        workspace_id: activeWorkspace.id,
        message: textToSend,
        history: history,
      });

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: res.reply,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        suggestedActions: res.suggested_actions,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      console.error("Chat request failed:", err);
      setError(err?.message || "Failed to communicate with AI Security Sentinel.");
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        role: "assistant",
        content:
          "**Service Notice:** Unable to reach the AI Sentinel provider. Please verify your workspace configuration or review your network connection.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClearHistory = () => {
    setMessages([
      {
        id: "welcome-reset",
        role: "assistant",
        content:
          "Conversation history cleared. Workspace telemetry re-synchronized. How can I assist your security team?",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        suggestedActions: [
          "How do I fix SQL injection in our code?",
          "Summarize critical vulnerabilities",
          "What is our highest risk attack path?",
        ],
      },
    ]);
  };

  return (
    <ProtectedRoute>
      <CommandCenterShell>
        <div className="flex flex-col h-[calc(100vh-3.5rem)] max-w-6xl mx-auto p-4 md:p-6">
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-border-subtle shrink-0">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-lg bg-crimson/20 border border-crimson/50 flex items-center justify-center text-crimson">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-lg font-bold text-white tracking-tight">
                    AI Security Chat
                  </h1>
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950/60 border border-emerald-700 text-emerald-400 flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    SENTINEL ACTIVE
                  </span>
                </div>
                <p className="text-xs text-neutral-400">
                  Interactive security consulting grounded in {activeWorkspace?.name || "your workspace"} telemetry.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleClearHistory}
                className="px-2.5 py-1.5 rounded border border-border-subtle bg-neutral-900 hover:bg-neutral-800 text-neutral-400 hover:text-white text-xs font-mono flex items-center gap-1.5 transition-colors"
                title="Reset conversation"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                <span>Reset Chat</span>
              </button>
            </div>
          </div>

          {/* Chat Messages Scroll Container */}
          <div className="flex-1 overflow-y-auto py-4 space-y-4 pr-1">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 text-sm ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {msg.role === "assistant" && (
                  <div className="h-8 w-8 rounded-full bg-crimson/20 border border-crimson/60 flex items-center justify-center text-crimson shrink-0 mt-1">
                    <Bot className="h-4 w-4" />
                  </div>
                )}

                <div
                  className={`max-w-2xl rounded-xl p-4 space-y-2 ${
                    msg.role === "user"
                      ? "bg-crimson text-white ml-12 rounded-tr-none"
                      : "bg-background-secondary border border-border-subtle text-neutral-200 mr-12 rounded-tl-none shadow-lg"
                  }`}
                >
                  <div className="flex items-center justify-between gap-4 border-b border-white/10 pb-1.5 text-[11px] font-mono text-neutral-400">
                    <span className="font-semibold text-white flex items-center gap-1.5">
                      {msg.role === "assistant" ? (
                        <>
                          <Shield className="h-3 w-3 text-crimson" />
                          <span>ShadowOps Sentinel</span>
                        </>
                      ) : (
                        <>
                          <User className="h-3 w-3 text-white" />
                          <span>{profile?.display_name || "Security Operator"}</span>
                        </>
                      )}
                    </span>
                    <span>{msg.timestamp}</span>
                  </div>

                  {/* Message Body */}
                  <div className="whitespace-pre-wrap leading-relaxed text-xs md:text-sm">
                    {msg.content}
                  </div>

                  {/* Suggested Prompts if provided */}
                  {msg.suggestedActions && msg.suggestedActions.length > 0 && (
                    <div className="pt-2 border-t border-border-subtle/50 mt-3">
                      <span className="text-[10px] font-mono text-neutral-400 block mb-1.5">
                        Suggested Follow-ups:
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {msg.suggestedActions.map((action, i) => (
                          <button
                            key={i}
                            onClick={() => handleSend(action)}
                            disabled={isSending}
                            className="px-2 py-1 rounded bg-neutral-900/80 hover:bg-neutral-800 border border-neutral-700/80 text-[11px] text-neutral-300 hover:text-white transition-colors text-left"
                          >
                            {action}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {msg.role === "user" && (
                  <div className="h-8 w-8 rounded-full bg-neutral-800 border border-neutral-700 flex items-center justify-center text-white shrink-0 mt-1 font-mono text-xs font-bold">
                    {profile?.display_name ? profile.display_name.slice(0, 2).toUpperCase() : "OP"}
                  </div>
                )}
              </div>
            ))}

            {isSending && (
              <div className="flex gap-3 text-sm justify-start">
                <div className="h-8 w-8 rounded-full bg-crimson/20 border border-crimson/60 flex items-center justify-center text-crimson shrink-0 mt-1">
                  <Bot className="h-4 w-4" />
                </div>
                <div className="rounded-xl p-4 bg-background-secondary border border-border-subtle text-neutral-400 rounded-tl-none flex items-center gap-2 font-mono text-xs">
                  <span className="h-2 w-2 rounded-full bg-crimson animate-ping" />
                  <span>Sentinel is analyzing workspace facts &amp; synthesizing advisory...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Form */}
          <div className="pt-3 border-t border-border-subtle shrink-0">
            {error && (
              <div className="mb-2 p-2.5 rounded bg-crimson/10 border border-crimson/30 text-crimson text-xs flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="relative rounded-xl border border-border-subtle bg-background-secondary focus-within:border-crimson transition-colors">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask Sentinel anything about vulnerabilities, remediation patterns, or attack paths... (Press Enter to send)"
                rows={2}
                disabled={isSending}
                className="w-full p-3 pr-14 bg-transparent text-sm text-neutral-200 placeholder-neutral-500 focus:outline-none resize-none font-sans"
              />
              <button
                onClick={() => handleSend()}
                disabled={isSending || !input.trim()}
                className="absolute right-3 bottom-3 p-2 rounded-lg bg-crimson hover:bg-crimson/90 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-all"
                title="Send message"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
            <div className="flex items-center justify-between text-[11px] text-neutral-500 font-mono mt-1.5 px-1">
              <span>Shift + Enter for new line • Enter to submit</span>
              <span>Grounded in active workspace telemetry</span>
            </div>
          </div>
        </div>
      </CommandCenterShell>
    </ProtectedRoute>
  );
}
