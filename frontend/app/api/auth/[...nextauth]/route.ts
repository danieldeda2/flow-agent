import NextAuth from "next-auth"
import GithubProvider from "next-auth/providers/github"
import GoogleProvider from "next-auth/providers/google"

const handler = NextAuth({
  providers: [
    GithubProvider({
        clientId: process.env.GITHUB_CLIENT_ID!,
        clientSecret: process.env.GITHUB_CLIENT_SECRET!,
        authorization: {
            params: {
            scope: "read:user user:email repo",
            },
        },
    }),
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          scope: "openid email profile https://www.googleapis.com/auth/gmail.readonly",
          access_type: "offline",
          prompt: "consent",
        },
      },
    }),
    {
        id: "slack",
        name: "Slack",
        type: "oauth",
        authorization: {
            url: "https://slack.com/oauth/v2/authorize",
            params: {
            scope: "openid email profile",
            user_scope: "channels:read,groups:read,im:read,im:history,users:read",
            },
        },
        token: {
            url: "https://slack.com/api/oauth.v2.access",
            async request({ client, params, checks, provider }: any) {
            const response = await client.oauthCallback(
                provider.callbackUrl,
                params,
                checks,
                { exchangeBody: { client_id: process.env.SLACK_CLIENT_ID, client_secret: process.env.SLACK_CLIENT_SECRET } }
            )
            return {
                tokens: {
                access_token: response.authed_user?.access_token,
                token_type: "bearer",
                },
            }
            },
        },
        userinfo: {
            url: "https://slack.com/api/openid.connect.userinfo",
            async request({ tokens }: any) {
            const response = await fetch("https://slack.com/api/openid.connect.userinfo", {
                headers: { Authorization: `Bearer ${tokens.access_token}` },
            })
            return response.json()
            },
        },
        profile(profile: any) {
            return {
            id: profile.sub,
            name: profile.name,
            email: profile.email,
            image: profile.picture,
            }
        },
        clientId: process.env.SLACK_CLIENT_ID!,
        clientSecret: process.env.SLACK_CLIENT_SECRET!,
    },   
  ],
  callbacks: {
    async signIn({ user, account }) {
      try {
        await fetch("http://localhost:8000/auth/callback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: user.email,
            name: user.name,
            avatar_url: user.image,
            access_token: account?.access_token,
            refresh_token: account?.refresh_token,
            provider: account?.provider,
          }),
        })
      } catch (error) {
        console.error("Failed to sync user to backend:", error)
      }
      return true
    },
    async jwt({ token, account, user }) {
      if (account) {
        token.accessToken = account.access_token
        token.provider = account.provider
      }
      return token
    },
    async session({ session, token }) {
      return session
    },
  },
})

export { handler as GET, handler as POST }