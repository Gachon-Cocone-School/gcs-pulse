# PROJECT KNOWLEDGE BASE (AGENTS.md)

**Generated:** 2026-01-17
**Frameworks:** Next.js 14+ (App Router), React 18, Tailwind CSS v4, shadcn/ui
**Language:** TypeScript 5.9
**Package Manager:** npm

## 1. COMMANDS

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server (with Opencode wrapper) |
| `npm run build` | Production build |
| `npm run start` | Start production server |
| `npm run lint` | Run Next.js linter |
| *No test command* | No testing framework (Jest/Vitest) is currently configured. |

## 2. PROJECT STRUCTURE

```
src/
├── app/                 # Next.js App Router (Layouts, Pages, API routes)
├── components/          # React Components
│   ├── ui/              # shadcn/ui atomic components (Do not modify logic here)
│   ├── views/           # Complex page views (keep page.tsx clean)
│   └── *.tsx            # Custom project-specific components
├── context/             # React Context (AuthProvider)
├── lib/                 # Utilities & API Client
├── styles/              # Global styles
└── types/               # TypeScript definitions
```

## 3. CODE STYLE & CONVENTIONS

### General
- **Imports**: Use absolute paths with `@/` alias (e.g., `import { Button } from "@/components/ui/button"`).
- **Exports**: Named exports preferred for components.
- **Strict Mode**: TypeScript `strict: true` is enabled. No `any` unless absolutely necessary (and commented).

### Naming
- **Components**: PascalCase (e.g., `UserProfile.tsx`, `function UserProfile()`).
- **Files**:
    - Components: PascalCase (e.g., `Button.tsx`).
    - Utilities/Hooks/Logic: camelCase (e.g., `api.ts`, `useAuth.ts`).
- **Variables/Functions**: camelCase.
- **Constants**: UPPER_SNAKE_CASE for global constants.

### React / Next.js
- **Server vs Client**: Default to Server Components. Add `'use client'` at the top for interactive components.
- **Props Interface**: Define props interface explicitly, usually named `${ComponentName}Props`.
- **Hooks**: Custom hooks should start with `use`.

### Styling (Tailwind CSS)
- **Utility First**: Use Tailwind utility classes.
- **Conditionals**: Use `cn()` helper for conditional class merging.
  ```tsx
  import { cn } from "@/lib/utils"; // or "@/components/ui/utils"
  // ...
  <div className={cn("base-class", isActive && "active-class", className)} />
  ```
- **Shadcn/ui**:
  - Located in `src/components/ui`.
  - Treat these as library code. **Avoid adding business logic to them.**
  - If you need a custom version, create a wrapper or a new component in `src/components/`.

### API & Data Fetching
- **Client**: Use `src/lib/api.ts`.
  - **Do NOT** use `fetch` directly in components.
  - **Do NOT** omit `credentials: 'include'` (handled by wrapper).
  ```ts
  import { api } from "@/lib/api";
  const data = await api.get<MyType>('/endpoint');
  ```
- **Auth**:
    - Cookie-based authentication.
    - Handled by `AuthProvider` (`src/context/auth-context.tsx`).

## 4. SPECIFIC RULES & GOTCHAS

### Two Button Systems
1.  **`src/components/ui/button.tsx`**: Standard shadcn/ui button. Use for generic UI.
2.  **`src/components/Button.tsx`**: Custom project-specific button. Use for LMS-specific actions if needed.
    *Preference: Use `ui/button.tsx` for consistency unless the custom one is required.*

### Anti-Patterns
- **Direct Logic in `ui/`**: Never add API calls or complex state to `src/components/ui/*`.
- **Editing `next-env.d.ts`**: This is auto-generated.
- **Using `vite-env.d.ts`**: Ignore/Delete this if found (legacy artifact).

### Error Handling
- API errors are thrown as `ApiError` with a `status` property.
- Handle errors in calling components or global boundaries.
- `/auth/me` returning 401 is handled gracefully (returns `null` user), not thrown.

## 5. EXAMPLE COMPONENT STRUCTURE

```tsx
"use client";

import * as React from "react";
import { cn } from "@/components/ui/utils";
import { Button } from "@/components/ui/button";

interface MyComponentProps {
  title: string;
  className?: string;
}

export function MyComponent({ title, className }: MyComponentProps) {
  return (
    <div className={cn("p-4 border rounded", className)}>
      <h2 className="text-xl font-bold">{title}</h2>
      <Button variant="default">Click Me</Button>
    </div>
  );
}
```
