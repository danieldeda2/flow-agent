"use client"
import { useEffect, useRef } from "react"

export interface Message {
  role: "user" | "assistant"
  content: string
  timestamp: Date
}

export default function ChatWindow({ messages, loading }: {
  messages: Message[]
  loading: boolean
}) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  return (
    <div style={{
      flex: 1,
      overflowY: "auto",
      padding: "32px 24px",
      display: "flex",
      flexDirection: "column",
      gap: "24px",
    }}>
      {messages.length === 0 && !loading && (
        <EmptyState />
      )}

      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}

      {loading && <TypingIndicator />}

      <div ref={bottomRef} />
    </div>
  )
}

function EmptyState() {
  const suggestions = [
    "What are my unread emails?",
    "Show me my GitHub repositories",
    "What channels do I have in Slack?",
    "Summarize my emails and related GitHub repos",
  ]

  return (
    <div style={{
      flex: 1,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      gap: "32px",
      padding: "48px 0",
      minHeight: "60vh",
    }}>
      <div style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: "12px" }}>
        <div style={{
          width: "48px", height: "48px",
          background: "var(--accent-dim)",
          border: "1px solid var(--accent-glow)",
          borderRadius: "14px",
          display: "flex", alignItems: "center", justifyContent: "center",
          margin: "0 auto",
          fontSize: "20px",
        }}>⚡</div>
        <h2 style={{
          fontSize: "20px",
          fontWeight: "600",
          color: "var(--text-primary)",
          letterSpacing: "-0.03em",
        }}>What can I help with?</h2>
        <p style={{
          fontSize: "14px",
          color: "var(--text-secondary)",
          maxWidth: "320px",
        }}>
          Ask anything about your GitHub, Gmail, or Slack. I can reason across all three at once.
        </p>
      </div>

      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "8px",
        width: "100%",
        maxWidth: "480px",
      }}>
        {suggestions.map((s, i) => (
          <div key={i} style={{
            padding: "12px 14px",
            background: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-md)",
            fontSize: "13px",
            color: "var(--text-secondary)",
            cursor: "pointer",
            transition: "all var(--transition)",
            lineHeight: "1.4",
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLDivElement).style.borderColor = "var(--accent-glow)"
            ;(e.currentTarget as HTMLDivElement).style.color = "var(--text-primary)"
            ;(e.currentTarget as HTMLDivElement).style.background = "var(--bg-elevated)"
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLDivElement).style.borderColor = "var(--border)"
            ;(e.currentTarget as HTMLDivElement).style.color = "var(--text-secondary)"
            ;(e.currentTarget as HTMLDivElement).style.background = "var(--bg-surface)"
          }}>
            {s}
          </div>
        ))}
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user"

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: isUser ? "flex-end" : "flex-start",
      gap: "6px",
      animation: "fadeIn 200ms ease-out",
    }}>
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        flexDirection: isUser ? "row-reverse" : "row",
      }}>
        <div style={{
          width: "22px", height: "22px",
          borderRadius: "6px",
          background: isUser ? "var(--accent)" : "var(--bg-elevated)",
          border: isUser ? "none" : "1px solid var(--border)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "11px",
          fontFamily: "var(--font-mono)",
          color: isUser ? "white" : "var(--text-secondary)",
          flexShrink: 0,
        }}>
          {isUser ? "U" : "F"}
        </div>
        <span style={{
          fontSize: "11px",
          fontFamily: "var(--font-mono)",
          color: "var(--text-muted)",
        }}>
          {isUser ? "You" : "FlowAgent"}
        </span>
      </div>

      <div style={{
        maxWidth: "680px",
        padding: "12px 16px",
        borderRadius: isUser ? "12px 4px 12px 12px" : "4px 12px 12px 12px",
        background: isUser ? "var(--accent)" : "var(--bg-surface)",
        border: isUser ? "none" : "1px solid var(--border)",
        fontSize: "14px",
        lineHeight: "1.7",
        color: isUser ? "white" : "var(--text-primary)",
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
      }}>
        {message.content}
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: "8px",
    }}>
      <div style={{
        width: "22px", height: "22px",
        borderRadius: "6px",
        background: "var(--bg-elevated)",
        border: "1px solid var(--border)",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: "11px",
        fontFamily: "var(--font-mono)",
        color: "var(--text-secondary)",
      }}>F</div>
      <div style={{
        padding: "12px 16px",
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "4px 12px 12px 12px",
        display: "flex",
        gap: "5px",
        alignItems: "center",
      }}>
        {[0, 1, 2].map(i => (
          <div key={i} style={{
            width: "5px", height: "5px",
            borderRadius: "50%",
            background: "var(--text-muted)",
            animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
          }} />
        ))}
      </div>
    </div>
  )
}