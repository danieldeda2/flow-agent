"use client"
import { useSession, signIn, signOut } from "next-auth/react"
import { useEffect, useState } from "react"

interface ConnectedServices {
  github: boolean
  google: boolean
  slack: boolean
}

export default function Sidebar() {
  const { data: session } = useSession()
  const [services, setServices] = useState<ConnectedServices>({
    github: false,
    google: false,
    slack: false,
  })

  useEffect(() => {
    if (session?.user?.email) {
      checkConnectedServices()
    }
  }, [session])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get("slack") === "connected") {
      setServices(prev => ({ ...prev, slack: true }))
      window.history.replaceState({}, "", "/")
    }
  }, [])

  const checkConnectedServices = async () => {
    const email = session?.user?.email
    if (!email) return

    const providers = ["github", "google", "slack"]
    const results = await Promise.all(
      providers.map(async (provider) => {
        try {
          const res = await fetch(
            `http://localhost:8000/auth/token/${encodeURIComponent(email)}/${provider}`
          )
          return { provider, connected: res.ok }
        } catch {
          return { provider, connected: false }
        }
      })
    )

    const updated: ConnectedServices = { github: false, google: false, slack: false }
    results.forEach(({ provider, connected }) => {
      updated[provider as keyof ConnectedServices] = connected
    })
    setServices(updated)
  }

  return (
    <aside style={{
      width: "240px",
      minWidth: "240px",
      height: "100vh",
      background: "var(--bg-surface)",
      borderRight: "1px solid var(--border)",
      display: "flex",
      flexDirection: "column",
      padding: "24px 16px",
      gap: "32px",
    }}>
      {/* Logo */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "0 8px" }}>
        <div style={{
          width: "28px", height: "28px",
          background: "var(--accent)",
          borderRadius: "8px",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "14px", fontWeight: "600",
          color: "white",
          fontFamily: "var(--font-mono)",
        }}>F</div>
        <span style={{
          fontFamily: "var(--font-mono)",
          fontWeight: "500",
          fontSize: "15px",
          color: "var(--text-primary)",
          letterSpacing: "-0.02em",
        }}>FlowAgent</span>
      </div>

      {/* Connected Services */}
      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        <p style={{
          fontSize: "11px",
          fontFamily: "var(--font-mono)",
          color: "var(--text-muted)",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          padding: "0 8px",
          marginBottom: "4px",
        }}>Connected</p>

        <ServiceItem
          icon="⌥"
          label="GitHub"
          connected={services.github}
          onConnect={() => signIn("github")}
        />
        <ServiceItem
          icon="✉"
          label="Gmail"
          connected={services.google}
          onConnect={() => signIn("google")}
        />
        <ServiceItem
          icon="#"
          label="Slack"
          connected={services.slack}
          onConnect={() => window.location.href = "http://localhost:8000/slack/connect"}
        />
      </div>

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* User */}
      <div style={{
        borderTop: "1px solid var(--border)",
        paddingTop: "16px",
        display: "flex",
        flexDirection: "column",
        gap: "8px",
      }}>
        {session ? (
          <>
            <div style={{
              display: "flex", alignItems: "center", gap: "10px",
              padding: "8px",
              borderRadius: "var(--radius-sm)",
            }}>
              {session.user?.image && (
                <img
                  src={session.user.image}
                  alt="avatar"
                  style={{ width: "28px", height: "28px", borderRadius: "50%", objectFit: "cover" }}
                />
              )}
              <div style={{ overflow: "hidden" }}>
                <p style={{ fontSize: "13px", fontWeight: "500", color: "var(--text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {session.user?.name}
                </p>
                <p style={{ fontSize: "11px", color: "var(--text-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {session.user?.email}
                </p>
              </div>
            </div>
            <button
              onClick={() => signOut()}
              style={{
                background: "transparent",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-sm)",
                color: "var(--text-secondary)",
                fontSize: "12px",
                padding: "7px 12px",
                cursor: "pointer",
                fontFamily: "var(--font-sans)",
                transition: "all var(--transition)",
                width: "100%",
              }}
              onMouseEnter={e => {
                (e.target as HTMLButtonElement).style.borderColor = "var(--error)"
                ;(e.target as HTMLButtonElement).style.color = "var(--error)"
              }}
              onMouseLeave={e => {
                (e.target as HTMLButtonElement).style.borderColor = "var(--border)"
                ;(e.target as HTMLButtonElement).style.color = "var(--text-secondary)"
              }}
            >
              Sign out
            </button>
          </>
        ) : (
          <button
            onClick={() => signIn("github")}
            style={{
              background: "var(--accent)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              color: "white",
              fontSize: "13px",
              fontWeight: "500",
              padding: "9px 12px",
              cursor: "pointer",
              fontFamily: "var(--font-sans)",
              width: "100%",
            }}
          >
            Sign in
          </button>
        )}
      </div>
    </aside>
  )
}

function ServiceItem({ icon, label, connected, onConnect }: {
  icon: string
  label: string
  connected: boolean
  onConnect: () => void
}) {
  return (
    <div
      onClick={!connected ? onConnect : undefined}
      style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "8px 10px",
        borderRadius: "var(--radius-sm)",
        cursor: connected ? "default" : "pointer",
        border: "1px solid transparent",
        transition: "all var(--transition)",
      }}
      onMouseEnter={e => {
        if (!connected) {
          (e.currentTarget as HTMLDivElement).style.background = "var(--bg-hover)"
          ;(e.currentTarget as HTMLDivElement).style.borderColor = "var(--border)"
        }
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLDivElement).style.background = "transparent"
        ;(e.currentTarget as HTMLDivElement).style.borderColor = "transparent"
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <span style={{
          fontFamily: "var(--font-mono)",
          fontSize: "13px",
          color: connected ? "var(--accent)" : "var(--text-muted)",
          width: "16px",
          textAlign: "center",
        }}>{icon}</span>
        <span style={{
          fontSize: "13px",
          color: connected ? "var(--text-primary)" : "var(--text-secondary)",
        }}>{label}</span>
      </div>
      <div style={{
        width: "6px", height: "6px",
        borderRadius: "50%",
        background: connected ? "var(--success)" : "var(--text-muted)",
        opacity: connected ? 1 : 0.4,
        boxShadow: connected ? "0 0 6px var(--success)" : "none",
      }} />
    </div>
  )
}