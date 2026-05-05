"use client"
import { useState, useRef, KeyboardEvent } from "react"

export default function MessageInput({ onSend, disabled }: {
  onSend: (message: string) => void
  disabled: boolean
}) {
  const [value, setValue] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = () => {
    if (!value.trim() || disabled) return
    onSend(value.trim())
    setValue("")
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = "auto"
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }

  return (
    <div style={{
      padding: "16px 24px 24px",
      borderTop: "1px solid var(--border)",
      background: "var(--bg-base)",
    }}>
      <div style={{
        display: "flex",
        alignItems: "flex-end",
        gap: "12px",
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
        padding: "12px 16px",
        transition: "border-color var(--transition)",
      }}
      onFocusCapture={e => {
        (e.currentTarget as HTMLDivElement).style.borderColor = "var(--accent-glow)"
      }}
      onBlurCapture={e => {
        (e.currentTarget as HTMLDivElement).style.borderColor = "var(--border)"
      }}>
        <textarea
          ref={textareaRef}
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder="Ask anything about your GitHub, Gmail, or Slack..."
          disabled={disabled}
          rows={1}
          style={{
            flex: 1,
            background: "transparent",
            border: "none",
            outline: "none",
            resize: "none",
            color: "var(--text-primary)",
            fontSize: "14px",
            fontFamily: "var(--font-sans)",
            lineHeight: "1.6",
            minHeight: "24px",
            maxHeight: "160px",
            overflowY: "auto",
          }}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          style={{
            width: "32px",
            height: "32px",
            borderRadius: "8px",
            background: disabled || !value.trim() ? "var(--bg-elevated)" : "var(--accent)",
            border: "none",
            cursor: disabled || !value.trim() ? "not-allowed" : "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
            transition: "all var(--transition)",
            color: disabled || !value.trim() ? "var(--text-muted)" : "white",
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </div>
      <p style={{
        fontSize: "11px",
        color: "var(--text-muted)",
        textAlign: "center",
        marginTop: "10px",
        fontFamily: "var(--font-mono)",
      }}>
        Enter to send · Shift+Enter for new line
      </p>
    </div>
  )
}