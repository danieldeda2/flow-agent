"use client"
import { useEffect, useRef } from "react"
import ReactMarkdown from "react-markdown"

export interface Message {
  role: "user" | "assistant"
  content: string
  timestamp: Date
}

export default function ChatWindow({ messages, loading, onSuggestionClick }: {
  messages: Message[]
  loading: boolean
  onSuggestionClick: (text: string) => void
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
      {messages.length === 0 && !loading && <EmptyState onSuggestionClick={onSuggestionClick} />}
      {messages.map((msg, i) => (
        <MessageBubble key={i} message={msg} />
      ))}
      {loading && <TypingIndicator />}
      <div ref={bottomRef} />
    </div>
  )
}

function EmptyState({ onSuggestionClick }: { onSuggestionClick: (text: string) => void }) {
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
          <div key={i}
            onClick={() => onSuggestionClick(s)}
            style={{
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
        wordBreak: "break-word",
      }}>
        {isUser ? (
          <span style={{ whiteSpace: "pre-wrap" }}>{message.content}</span>
        ) : (
          <div className="markdown-body">
            <ReactMarkdown
              components={{
                h1: ({ children }) => <h1 style={{ fontSize: "18px", fontWeight: "600", marginBottom: "8px", color: "var(--text-primary)" }}>{children}</h1>,
                h2: ({ children }) => <h2 style={{ fontSize: "16px", fontWeight: "600", marginBottom: "6px", color: "var(--text-primary)" }}>{children}</h2>,
                h3: ({ children }) => <h3 style={{ fontSize: "14px", fontWeight: "600", marginBottom: "4px", color: "var(--text-primary)" }}>{children}</h3>,
                p: ({ children }) => <p style={{ marginBottom: "8px", lineHeight: "1.7" }}>{children}</p>,
                ul: ({ children }) => <ul style={{ paddingLeft: "18px", marginBottom: "8px" }}>{children}</ul>,
                ol: ({ children }) => <ol style={{ paddingLeft: "18px", marginBottom: "8px" }}>{children}</ol>,
                li: ({ children }) => <li style={{ marginBottom: "4px", lineHeight: "1.6" }}>{children}</li>,
                strong: ({ children }) => <strong style={{ fontWeight: "600", color: "var(--text-primary)" }}>{children}</strong>,
                em: ({ children }) => <em style={{ fontStyle: "italic" }}>{children}</em>,
                code: ({ children }) => <code style={{ fontFamily: "var(--font-mono)", fontSize: "12px", background: "var(--bg-elevated)", padding: "2px 6px", borderRadius: "4px", color: "var(--accent)" }}>{children}</code>,
                pre: ({ children }) => <pre style={{ fontFamily: "var(--font-mono)", fontSize: "12px", background: "var(--bg-elevated)", padding: "12px", borderRadius: "8px", overflowX: "auto", marginBottom: "8px" }}>{children}</pre>,
                hr: () => <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "12px 0" }} />,
                a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent)", textDecoration: "underline" }}>{children}</a>,
                table: ({ children }) => <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: "8px", fontSize: "13px" }}>{children}</table>,
                th: ({ children }) => <th style={{ padding: "6px 12px", borderBottom: "1px solid var(--border)", textAlign: "left", fontWeight: "600", color: "var(--text-secondary)" }}>{children}</th>,
                td: ({ children }) => <td style={{ padding: "6px 12px", borderBottom: "1px solid var(--border-subtle)" }}>{children}</td>,
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
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