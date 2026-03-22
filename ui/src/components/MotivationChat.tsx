import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  deleteMotivation,
  getMotivation,
  sendMotivationChat,
  type ChatMessage,
} from "@/lib/api";
import { Label } from "@/components/ui/label";

const glassStyle = {
  background: "rgba(255,255,255,0.06)",
  backdropFilter: "blur(6px)",
  WebkitBackdropFilter: "blur(6px)",
  border: "1px solid rgba(255,255,255,0.14)",
};

interface MotivationChatProps {
  resumeId?: string;
  provider?: string;
}

export function MotivationChat({ resumeId, provider }: MotivationChatProps) {
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [input, setInput] = useState("");
  const [localHistory, setLocalHistory] = useState<ChatMessage[]>([]);
  const [localSummary, setLocalSummary] = useState<string>("");
  const [localStatus, setLocalStatus] = useState<"idle" | "in_progress" | "completed">("idle");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Load existing motivation on mount
  const { data: existing, isLoading } = useQuery({
    queryKey: ["motivation"],
    queryFn: getMotivation,
    retry: false,
  });

  // Seed local state from existing motivation
  useEffect(() => {
    if (existing) {
      setLocalHistory(existing.chat_history);
      setLocalSummary(existing.summary);
      setLocalStatus(existing.status);
      if (existing.status === "in_progress" && existing.chat_history.length > 0) {
        setExpanded(true);
      }
    }
  }, [existing]);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [localHistory]);

  const chatMutation = useMutation({
    mutationFn: (message: string) =>
      sendMotivationChat(message, resumeId, provider),
    onSuccess: (data) => {
      setLocalHistory(data.chat_history);
      if (data.ready && data.summary) {
        setLocalSummary(data.summary);
        setLocalStatus("completed");
      }
      qc.setQueryData(["motivation"], {
        resume_id: resumeId ?? null,
        chat_history: data.chat_history,
        summary: data.summary ?? "",
        status: data.status,
        created_at: "",
        updated_at: "",
      });
    },
  });

  const resetMutation = useMutation({
    mutationFn: deleteMotivation,
    onSuccess: () => {
      setLocalHistory([]);
      setLocalSummary("");
      setLocalStatus("idle");
      setInput("");
      setExpanded(false);
      qc.setQueryData(["motivation"], null);
    },
  });

  const handleSend = () => {
    const msg = input.trim();
    if (!msg || chatMutation.isPending) return;

    // Optimistically add user message
    setLocalHistory((prev) => [...prev, { role: "user", content: msg }]);
    setLocalStatus("in_progress");
    setInput("");
    chatMutation.mutate(msg);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (isLoading) return null;

  // Completed state — show summary badge
  if (localStatus === "completed" && localSummary) {
    return (
      <div className="space-y-1.5">
        <Label className="text-white/75">Search Preferences</Label>
        <div
          className="flex items-start gap-3 rounded-lg px-3 py-2.5"
          style={{
            ...glassStyle,
            background: "rgba(52, 211, 153, 0.08)",
            border: "1px solid rgba(52, 211, 153, 0.25)",
          }}
        >
          <div className="flex-1 min-w-0">
            <p className="text-sm text-emerald-300/90 leading-relaxed">{localSummary}</p>
          </div>
          <button
            onClick={() => resetMutation.mutate()}
            disabled={resetMutation.isPending}
            className="shrink-0 px-2 py-1 rounded text-xs font-medium transition-colors"
            style={{
              background: "rgba(255,255,255,0.10)",
              border: "1px solid rgba(255,255,255,0.20)",
              color: "rgba(255,255,255,0.60)",
            }}
          >
            Reset
          </button>
        </div>
      </div>
    );
  }

  // Collapsed state — show toggle to open
  if (!expanded) {
    return (
      <div className="space-y-1.5">
        <button
          onClick={() => setExpanded(true)}
          className="text-sm transition-colors"
          style={{ color: "rgba(147, 210, 255, 0.75)" }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "rgba(147, 210, 255, 1)")}
          onMouseLeave={(e) => (e.currentTarget.style.color = "rgba(147, 210, 255, 0.75)")}
        >
          + Describe what you're looking for <span className="text-white/30">(optional)</span>
        </button>
      </div>
    );
  }

  // Expanded chat state
  const starterMessage: ChatMessage = {
    role: "assistant",
    content: "What kind of companies are you looking for? For example: 'startups in health tech', 'large enterprises in Seattle', or 'companies using cutting-edge AI'.",
  };

  const displayHistory = localHistory.length === 0 ? [starterMessage] : localHistory;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <Label className="text-white/75">Search Preferences</Label>
        <div className="flex gap-2">
          {localHistory.length > 0 && (
            <button
              onClick={() => resetMutation.mutate()}
              disabled={resetMutation.isPending}
              className="text-xs transition-colors"
              style={{ color: "rgba(255,255,255,0.40)" }}
            >
              Reset
            </button>
          )}
          <button
            onClick={() => setExpanded(false)}
            className="text-xs transition-colors"
            style={{ color: "rgba(255,255,255,0.40)" }}
          >
            Minimize
          </button>
        </div>
      </div>

      <div className="rounded-lg overflow-hidden" style={glassStyle}>
        {/* Messages */}
        <div
          ref={scrollRef}
          className="px-3 py-3 space-y-3 overflow-y-auto"
          style={{ maxHeight: "220px" }}
        >
          {displayHistory.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className="rounded-lg px-3 py-2 text-sm max-w-[85%]"
                style={{
                  background:
                    msg.role === "user"
                      ? "rgba(99, 148, 255, 0.18)"
                      : "rgba(255, 255, 255, 0.08)",
                  color:
                    msg.role === "user"
                      ? "rgba(186, 210, 255, 0.95)"
                      : "rgba(255, 255, 255, 0.75)",
                }}
              >
                {msg.content}
              </div>
            </div>
          ))}

          {chatMutation.isPending && (
            <div className="flex justify-start">
              <div
                className="rounded-lg px-3 py-2 text-sm"
                style={{
                  background: "rgba(255, 255, 255, 0.08)",
                  color: "rgba(255, 255, 255, 0.50)",
                }}
              >
                <span className="inline-flex gap-1">
                  <span className="animate-bounce" style={{ animationDelay: "0ms" }}>.</span>
                  <span className="animate-bounce" style={{ animationDelay: "150ms" }}>.</span>
                  <span className="animate-bounce" style={{ animationDelay: "300ms" }}>.</span>
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div
          className="flex items-center gap-2 px-3 py-2"
          style={{ borderTop: "1px solid rgba(255,255,255,0.10)" }}
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe the kind of companies you want..."
            disabled={chatMutation.isPending}
            className="flex-1 bg-transparent text-sm text-white placeholder-white/30 outline-none"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || chatMutation.isPending}
            className="shrink-0 px-3 py-1 rounded text-xs font-medium transition-colors disabled:opacity-30"
            style={{
              background: "rgba(99, 148, 255, 0.25)",
              border: "1px solid rgba(99, 148, 255, 0.35)",
              color: "rgba(186, 210, 255, 0.95)",
            }}
          >
            Send
          </button>
        </div>

        {/* Error */}
        {chatMutation.isError && (
          <div className="px-3 pb-2">
            <p className="text-xs text-red-300/80">
              Failed to get response. Try again.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
