"use client"
import { useSession, signIn, signOut } from "next-auth/react"
import { useEffect, useState } from "react"

interface ServiceInfo {
  connected: boolean
  email: string | null
}

interface ConnectedServices {
  github: ServiceInfo
  google: ServiceInfo
  slack: ServiceInfo
}

export default function Sidebar({ onClose }: { onClose?: () => void }) {
  const { data: session } = useSession()
  const [services, setServices] = useState<ConnectedServices>({
    github: { connected: false, email: null },
    google: { connected: false, email: null },
    slack: { connected: false, email: null },
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (session?.user?.email) {
      checkConnectedServices()
    }
  }, [session])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get("slack") === "connected" || params.get("google") === "connected") {
      checkConnectedServices()
      window.history.replaceState({}, "", "/")
    }
  }, [])



  const checkConnectedServices = async () => {
    setLoading(true)
    const email = session?.user?.email
    if (!email) return

    try {
      const res = await fetch(
        `http://localhost:8000/auth/connected/${encodeURIComponent(email)}`
      )
      if (res.ok) {
        const data = await res.json()
        setServices({
          github: { connected: !!data.github, email: data.github || null },
          google: { connected: !!data.google, email: data.google || null },
          slack: { connected: !!data.slack, email: data.slack || null },
        })
      }
    } catch {
      console.error("Failed to fetch connected services")
    }
    setLoading(false)
  }

  const handleDisconnect = async (provider: string) => {
    const email = session?.user?.email
    if (!email) return
    try {
      await fetch(
        `http://localhost:8000/auth/disconnect/${encodeURIComponent(email)}/${provider}`,
        { method: "DELETE" }
      )
      setServices(prev => ({
        ...prev,
        [provider]: { connected: false, email: null },
      }))
    } catch {
      console.error("Failed to disconnect", provider)
    }
  }

  const connectedCount = Object.values(services).filter(s => s.connected).length
  const allConnected = connectedCount === 3

  return (
    <aside style={{
      width: "260px",
      minWidth: "260px",
      height: "100vh",
      background: "var(--bg-surface)",
      borderRight: "1px solid var(--border)",
      display: "flex",
      flexDirection: "column",
      padding: "20px 14px",
      gap: "24px",
    }}>
      {/* Logo */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "4px 6px" }}>
        <div style={{
          width: "28px", height: "28px",
          background: "var(--accent)",
          borderRadius: "8px",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "13px", fontWeight: "700",
          color: "white",
          fontFamily: "var(--font-mono)",
          boxShadow: "0 0 12px var(--accent-glow)",
          flexShrink: 0,
        }}>F</div>
        <span style={{
          fontFamily: "var(--font-mono)",
          fontWeight: "500",
          fontSize: "14px",
          color: "var(--text-primary)",
          letterSpacing: "-0.02em",
        }}>FlowAgent</span>
      </div>

      {/* Orchestration Status */}
      <div style={{
        padding: "12px 14px",
        borderRadius: "var(--radius-md)",
        background: allConnected ? "rgba(61, 214, 140, 0.06)" : "rgba(79, 142, 255, 0.04)",
        border: `1px solid ${allConnected ? "rgba(61, 214, 140, 0.2)" : "var(--border)"}`,
        display: "flex",
        flexDirection: "column",
        gap: "8px",
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{
            fontSize: "11px",
            fontFamily: "var(--font-mono)",
            color: allConnected ? "var(--success)" : "var(--text-secondary)",
            fontWeight: "500",
          }}>
            {allConnected ? "✓ Fully orchestrated" : `${connectedCount} / 3 connected`}
          </span>
          <div style={{ display: "flex", gap: "4px" }}>
            {(["github", "google", "slack"] as const).map(p => (
              <div key={p} style={{
                width: "6px", height: "6px",
                borderRadius: "50%",
                background: services[p].connected ? "var(--success)" : "var(--bg-elevated)",
                border: `1px solid ${services[p].connected ? "var(--success)" : "var(--border)"}`,
                boxShadow: services[p].connected ? "0 0 4px var(--success)" : "none",
                transition: "all var(--transition)",
              }} />
            ))}
          </div>
        </div>
        <p style={{
          fontSize: "11px",
          color: "var(--text-muted)",
          lineHeight: "1.5",
        }}>
          {allConnected
            ? "Cross-service commands enabled"
            : "Connect all services to enable full orchestration"}
        </p>
      </div>

      {/* Services */}
      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <p style={{
          fontSize: "10px",
          fontFamily: "var(--font-mono)",
          color: "var(--text-muted)",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
          padding: "0 6px",
          marginBottom: "2px",
        }}>Services</p>

        <ServiceCard
          icon={<GithubIcon />}
          label="GitHub"
          description="Repos & issues"
          service={services.github}
          loading={loading}
          onConnect={() => signIn("github")}
          onDisconnect={() => handleDisconnect("github")}
        />
        <ServiceCard
          icon={<GmailIcon />}
          label="Gmail"
          description="Email & inbox"
          service={services.google}
          loading={loading}
          onConnect={() => window.location.href = `http://localhost:8000/google/connect?master_email=${encodeURIComponent(session?.user?.email || "")}`}          onDisconnect={() => handleDisconnect("google")}
        />
        <ServiceCard
          icon={<SlackIcon />}
          label="Slack"
          description="Channels & messages"
          service={services.slack}
          loading={loading}
          onConnect={() => window.location.href = `http://localhost:8000/slack/connect?master_email=${encodeURIComponent(session?.user?.email || "")}`}
          onDisconnect={() => handleDisconnect("slack")}
        />
      </div>

      <div style={{ flex: 1 }} />

      {/* User */}
      <div style={{
        borderTop: "1px solid var(--border)",
        paddingTop: "14px",
        display: "flex",
        flexDirection: "column",
        gap: "8px",
      }}>
        {session ? (
          <>
            <div style={{
              display: "flex", alignItems: "center", gap: "10px",
              padding: "8px 6px",
            }}>
              {session.user?.image ? (
                <img
                  src={session.user.image}
                  alt="avatar"
                  style={{ width: "30px", height: "30px", borderRadius: "50%", objectFit: "cover", flexShrink: 0 }}
                />
              ) : (
                <div style={{
                  width: "30px", height: "30px", borderRadius: "50%",
                  background: "var(--bg-elevated)",
                  border: "1px solid var(--border)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "12px", color: "var(--text-secondary)",
                  flexShrink: 0,
                }}>
                  {session.user?.name?.[0] || "U"}
                </div>
              )}
              <div style={{ overflow: "hidden", flex: 1 }}>
                <p style={{
                  fontSize: "13px", fontWeight: "500",
                  color: "var(--text-primary)",
                  whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis"
                }}>
                  {session.user?.name}
                </p>
                <p style={{
                  fontSize: "11px", color: "var(--text-muted)",
                  whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis"
                }}>
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
                color: "var(--text-muted)",
                fontSize: "12px",
                padding: "7px 12px",
                cursor: "pointer",
                fontFamily: "var(--font-sans)",
                transition: "all var(--transition)",
                width: "100%",
              }}
              onMouseEnter={e => {
                (e.currentTarget).style.borderColor = "var(--error)"
                ;(e.currentTarget).style.color = "var(--error)"
              }}
              onMouseLeave={e => {
                (e.currentTarget).style.borderColor = "var(--border)"
                ;(e.currentTarget).style.color = "var(--text-muted)"
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

function ServiceCard({ icon, label, description, service, loading, onConnect, onDisconnect }: {
  icon: React.ReactNode
  label: string
  description: string
  service: ServiceInfo
  loading: boolean
  onConnect: () => void
  onDisconnect: () => void
}) {
  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: "10px",
      padding: "10px 12px",
      borderRadius: "var(--radius-md)",
      background: service.connected ? "rgba(61, 214, 140, 0.03)" : "var(--bg-elevated)",
      border: `1px solid ${service.connected ? "rgba(61, 214, 140, 0.12)" : "var(--border-subtle)"}`,
      transition: "all var(--transition)",
    }}>
      <div style={{
        width: "32px", height: "32px",
        borderRadius: "8px",
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        display: "flex", alignItems: "center", justifyContent: "center",
        flexShrink: 0,
      }}>
        {icon}
      </div>

      <div style={{ flex: 1, overflow: "hidden", minWidth: 0 }}>
        <p style={{
          fontSize: "13px", fontWeight: "500",
          color: "var(--text-primary)",
          lineHeight: "1.3",
        }}>{label}</p>
        {service.connected && service.email ? (
          <p style={{
            fontSize: "10px",
            fontFamily: "var(--font-mono)",
            color: "var(--success)",
            opacity: 0.8,
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
            marginTop: "1px",
          }}>
            {service.email}
          </p>
        ) : (
          <p style={{
            fontSize: "11px",
            color: "var(--text-muted)",
            marginTop: "1px",
          }}>{description}</p>
        )}
      </div>

      {loading ? (
        <div style={{
          width: "6px", height: "6px",
          borderRadius: "50%",
          background: "var(--text-muted)",
          opacity: 0.3,
          flexShrink: 0,
        }} />
      ) : service.connected ? (
        <button
          onClick={onDisconnect}
          title="Disconnect"
          style={{
            background: "transparent",
            border: "1px solid transparent",
            borderRadius: "6px",
            color: "var(--text-muted)",
            fontSize: "14px",
            width: "24px",
            height: "24px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            flexShrink: 0,
            transition: "all var(--transition)",
            padding: 0,
          }}
          onMouseEnter={e => {
            (e.currentTarget).style.borderColor = "var(--error)"
            ;(e.currentTarget).style.color = "var(--error)"
            ;(e.currentTarget).style.background = "rgba(255,80,80,0.06)"
          }}
          onMouseLeave={e => {
            (e.currentTarget).style.borderColor = "transparent"
            ;(e.currentTarget).style.color = "var(--text-muted)"
            ;(e.currentTarget).style.background = "transparent"
          }}
        >
          ✕
        </button>
      ) : (
        <button
          onClick={onConnect}
          style={{
            padding: "4px 10px",
            borderRadius: "20px",
            background: "var(--accent-dim)",
            border: "1px solid var(--accent-glow)",
            color: "var(--accent)",
            fontSize: "11px",
            fontFamily: "var(--font-mono)",
            cursor: "pointer",
            whiteSpace: "nowrap",
            flexShrink: 0,
            transition: "all var(--transition)",
          }}
          onMouseEnter={e => {
            (e.currentTarget).style.background = "var(--accent)"
            ;(e.currentTarget).style.color = "white"
          }}
          onMouseLeave={e => {
            (e.currentTarget).style.background = "var(--accent-dim)"
            ;(e.currentTarget).style.color = "var(--accent)"
          }}
        >
          Connect
        </button>
      )}
    </div>
  )
}

function GithubIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="var(--text-secondary)">
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/>
    </svg>
  )
}

function GmailIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
      <path d="M24 5.457v13.909c0 .904-.732 1.636-1.636 1.636h-3.819V11.73L12 16.64l-6.545-4.91v9.272H1.636A1.636 1.636 0 0 1 0 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L5.455 4.64 12 9.548l6.545-4.91 1.528-1.145C21.69 2.28 24 3.434 24 5.457z" fill="var(--text-secondary)"/>
    </svg>
  )
}

function SlackIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="var(--text-secondary)">
      <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"/>
    </svg>
  )
}