# Francessca frontend

Next.js 14 (App Router) + TypeScript + TailwindCSS. Minimal scaffold covering
auth, chat, lawyer search, and shared UI primitives. Talks to the backend via
`src/lib/api.ts`.

```bash
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL
npm run dev                         # http://localhost:3000
```

Pages: `/` landing, `/login` (login + register), `/chat` (AI assistant),
`/lawyers` (search). The token is held in memory for the scaffold — move it to
httpOnly cookies for production.
