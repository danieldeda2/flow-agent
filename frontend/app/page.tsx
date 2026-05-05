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

  useEffect(() => {
    if (session?.user?.email) {
      fetchConnectedAccounts()
    }
  }, [session])

  const fetchConnectedAccounts = async () => {
    try {
      const res = await fetch(
        `http://localhost:8000/auth/connected/${encodeURIComponent(session!.user!.email!)}`
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

  const missingServices = []
  if (!connectedAccounts.github) missingServices.push("GitHub")
  if (!connectedAccounts.google) missingServices.push("Gmail")
  if (!connectedAccounts.slack) missingServices.push("Slack")

  const userMessage: Message = {
    role: "user",
    content,
    timestamp: new Date(),
  }

  setMessages(prev => [...prev, userMessage])

  if (missingServices.length === 3) {
    setMessages(prev => [...prev, {
      role: "assistant",
      content: "You haven't connected any services yet. Connect GitHub, Gmail, or Slack from the sidebar to get started.",
      timestamp: new Date(),
    }])
    return
  }

  if (missingServices.length > 0) {
    setMessages(prev => [...prev, {
      role: "assistant",
      content: `Note: ${missingServices.join(", ")} ${missingServices.length === 1 ? "is" : "are"} not connected. I'll do my best with the services you have connected.`,
      timestamp: new Date(),
    }])
  }

  setLoading(true)

  try {
    const res = await fetch("http://localhost:8000/agent/orchestrate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        github_email: connectedAccounts.github || session.user.email,
        gmail_email: connectedAccounts.google || session.user.email,
        slack_email: connectedAccounts.slack || session.user.email,
        message: content,
      }),
    })

    const data = await res.json()

    setMessages(prev => [...prev, {
      role: "assistant",
      content: data.response || "Something went wrong.",
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
          <SignInButton
            onClick={() => signIn("google")}
            icon="✉"
            label="Continue with Google"
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
      <Sidebar />
      <main style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}>
        <header style={{
          padding: "16px 24px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexShrink: 0,
        }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
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
          <div style={{
            padding: "4px 10px",
            background: "var(--accent-dim)",
            border: "1px solid var(--accent-glow)",
            borderRadius: "20px",
            fontSize: "11px",
            fontFamily: "var(--font-mono)",
            color: "var(--accent)",
          }}>
            claude-sonnet-4-6
          </div>
        </header>

        <ChatWindow messages={messages} loading={loading} />
        <MessageInput onSend={handleSend} disabled={loading} />
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
        padding: "12px 16px",
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-md)",
        color: "var(--text-primary)",
        fontSize: "14px",
        fontWeight: "500",
        cursor: "pointer",
        fontFamily: "var(--font-sans)",
        transition: "all var(--transition)",
        width: "100%",
      }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--accent-glow)"
        ;(e.currentTarget as HTMLButtonElement).style.background = "var(--bg-elevated)"
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--border)"
        ;(e.currentTarget as HTMLButtonElement).style.background = "var(--bg-surface)"
      }}
    >
      <span style={{
        fontFamily: "var(--font-mono)",
        fontSize: "14px",
        color: "var(--accent)",
        width: "20px",
        textAlign: "center",
      }}>{icon}</span>
      {label}
    </button>
  )
}