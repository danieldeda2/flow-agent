"use client"
import { useSession, signIn } from "next-auth/react"
import { useState, useEffect } from "react"
import Sidebar from "./components/Sidebar"
import ChatWindow, { Message } from "./components/ChatWindow"
import MessageInput from "./components/MessageInput"

interface ConnectedAccounts {
  github?: string
  google?: string
  slack?: string
  master?: string
}

export default function Home() {
  const { data: session } = useSession()
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [connectedAccounts, setConnectedAccounts] = useState<ConnectedAccounts>({})
  const [inputValue, setInputValue] = useState("")
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    if (session?.user?.email) {
      fetchConnectedAccounts()
    }
  }, [session])

  const fetchConnectedAccounts = async () => {
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/auth/connected/${encodeURIComponent(session!.user!.email!)}`
      )
      if (res.ok) {
        const data = await res.json()
        setConnectedAccounts(data)
      }
    } catch (err) {
      console.error("Failed to fetch connected accounts", err)
    }
  }

  const handleSend = async (content: string) => {
    if (!session?.user?.email) return

    const userMessage: Message = {
      role: "user",
      content,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setLoading(true)

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/agent/orchestrate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          github_email: connectedAccounts.github || null,
          gmail_email: connectedAccounts.google || null,
          slack_email: connectedAccounts.slack || null,
          message: content,
        }),
      })

      const data = await res.json()

      setMessages(prev => [...prev, {
        role: "assistant",
        content: data.response || data.detail || "Something went wrong.",
        timestamp: new Date(),
      }])
    } catch (err) {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "Failed to reach the server. Make sure the backend is running.",
        timestamp: new Date(),
      }])
    } finally {
      setLoading(false)
    }
  }

  if (!session) {
    return (
      <div style={{
        height: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--bg-base)",
        flexDirection: "column",
        gap: "32px",
        padding: "24px",
        position: "relative",
        zIndex: 1,
        touchAction: "manipulation",
      }}>
        <div style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: "16px", alignItems: "center" }}>
          <div style={{
            width: "56px", height: "56px",
            background: "var(--accent)",
            borderRadius: "16px",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "24px", fontWeight: "700",
            color: "white",
            fontFamily: "var(--font-mono)",
            boxShadow: "0 0 40px var(--accent-glow)",
          }}>F</div>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <h1 style={{
              fontSize: "28px",
              fontWeight: "600",
              color: "var(--text-primary)",
              letterSpacing: "-0.04em",
              fontFamily: "var(--font-mono)",
            }}>FlowAgent</h1>
            <p style={{
              fontSize: "15px",
              color: "var(--text-secondary)",
              maxWidth: "320px",
            }}>
              AI orchestration across GitHub, Gmail, and Slack. Sign in to get started.
            </p>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "10px", width: "280px" }}>
          <SignInButton
            onClick={() => signIn("github")}
            icon="⌥"
            label="Continue with GitHub"
          />
        </div>
      </div>
    )
  }

  return (
    <div style={{
      display: "flex",
      height: "100vh",
      background: "var(--bg-base)",
      overflow: "hidden",
    }}>
      {/* Desktop sidebar */}
      <div className="sidebar-desktop">
        <Sidebar />
      </div>

      {/* Mobile overlay */}
      <div
        className={`sidebar-overlay ${sidebarOpen ? "open" : ""}`}
        onClick={() => setSidebarOpen(false)}
      />

      {/* Mobile drawer */}
      <div className={`sidebar-drawer ${sidebarOpen ? "open" : ""}`}>
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      <main style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        minWidth: 0,
      }}>
        <header style={{
          padding: "16px 24px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexShrink: 0,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px", flex: 1 }}>
            {/* Mobile menu button */}
            <button
              className="mobile-header-btn"
              onClick={() => setSidebarOpen(true)}
              style={{
                display: "flex",
                width: "32px", height: "32px",
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                alignItems: "center", justifyContent: "center",
                cursor: "pointer",
                color: "var(--text-secondary)",
                flexShrink: 0,
                touchAction: "manipulation",
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                <line x1="3" y1="6" x2="21" y2="6"/>
                <line x1="3" y1="12" x2="21" y2="12"/>
                <line x1="3" y1="18" x2="21" y2="18"/>
              </svg>
            </button>
            <div style={{ display: "flex", flexDirection: "column", gap: "2px", paddingLeft: "10px" }}>
              <h1 style={{
                fontSize: "15px",
                fontWeight: "600",
                color: "var(--text-primary)",
                letterSpacing: "-0.02em",
              }}>Chat</h1>
              <p style={{
                fontSize: "12px",
                color: "var(--text-muted)",
                fontFamily: "var(--font-mono)",
              }}>Orchestrating GitHub · Gmail · Slack</p>
            </div>
          </div>
          <div className="desktop-model-badge" style={{
            padding: "4px 10px",
            background: "var(--accent-dim)",
            border: "1px solid var(--accent-glow)",
            borderRadius: "20px",
            fontSize: "11px",
            fontFamily: "var(--font-mono)",
            color: "var(--accent)",
            flexShrink: 0,
          }}>
            claude-sonnet-4-6
          </div>
        </header>

        <ChatWindow
          messages={messages}
          loading={loading}
          onSuggestionClick={(text) => setInputValue(text)}
        />
        <MessageInput
          onSend={handleSend}
          disabled={loading}
          value={inputValue}
          onChange={setInputValue}
        />
      </main>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 0.3; transform: scale(0.8); }
          50% { opacity: 1; transform: scale(1); }
        }
        textarea::placeholder {
          color: var(--text-muted);
        }
        @media (max-width: 768px) {
          .desktop-model-badge {
            display: none !important;
          }
        }
      `}</style>
    </div>
  )
}

function SignInButton({ onClick, icon, label }: {
  onClick: () => void
  icon: string
  label: string
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "12px",
        padding: "16px",
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-md)",
        color: "var(--text-primary)",
        fontSize: "16px",
        fontWeight: "500",
        cursor: "pointer",
        fontFamily: "var(--font-sans)",
        width: "100%",
        WebkitTapHighlightColor: "transparent",
        touchAction: "manipulation",
        userSelect: "none",
        minHeight: "52px",
      }}
    >
      <span style={{
        fontFamily: "var(--font-mono)",
        fontSize: "16px",
        color: "var(--accent)",
        width: "20px",
        textAlign: "center",
      }}>{icon}</span>
      {label}
    </button>
  )
}