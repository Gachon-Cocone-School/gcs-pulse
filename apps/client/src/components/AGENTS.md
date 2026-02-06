# UI Components (src/components)

## OVERVIEW
This directory is the central repository for all UI components in the application. It follows a layered approach:
1.  **Atomic/Primitive Components**: Reusable, low-level building blocks (mostly shadcn/ui).
2.  **Custom/Business Components**: Higher-level components with project-specific styling or logic.
3.  **Page Views**: Full-page assemblies used by the Next.js App Router.

## STRUCTURE
- `src/components/`: Core custom components (e.g., `Navigation`, `ProtectedRoute`, `Card`).
- `src/components/ui/`: Atomic components based on **shadcn/ui** and Radix UI. These are typically generated/copied and should be modified sparingly.
- `src/components/views/`: Orchestrated page views (e.g., `MainDashboard`, `AccessDenied`) that are consumed primarily by `src/app/page.tsx`.

## WHERE TO LOOK
| Component | Location | Role |
|-----------|----------|------|
| `ProtectedRoute` | `src/components/ProtectedRoute.tsx` | Client-side route protection. Supports `adminOnly` flag. |
| `Navigation` | `src/components/Navigation.tsx` | Main application header and top-level navigation. |
| **Custom Button** | `src/components/Button.tsx` | A simplified, project-specific button with predefined variants. |
| **UI Button** | `src/components/ui/button.tsx` | The standard **shadcn/ui** button with `cva` and `Slot` support. |
| `views/` | `src/components/views/*` | Full-page view components that keep `src/app/page.tsx` clean. |

## CONVENTIONS
- **Two Button Systems**: 
  - Use `src/components/Button.tsx` for quick, standard LMS-themed buttons.
  - Use `src/components/ui/button.tsx` when you need advanced features like `asChild` or standard shadcn/ui variants.
- **View Pattern**: Complex logic for the main entry point (`/`) is offloaded to `src/components/views/`. This keeps the gatekeeper logic in `src/app/page.tsx` readable.
- **Client Components**: Most components interacting with `useAuth` or `lucide-react` icons are marked with `'use client'`.

## ANTI-PATTERNS
- **Mixing UI and Business Logic**: Avoid putting heavy API calls inside `src/components/ui/`. Keep them as pure as possible.
- **Direct App Router Imports**: Avoid importing `src/components/views/` directly into sub-routes if they are meant to be managed by the `page.tsx` gatekeeper.

## NOTES
- `ProtectedRoute` is used both as a wrapper in layouts (e.g., `src/app/admin/layout.tsx`) and as a standalone component for conditional rendering.
- Many components in the root of `src/components/` (like `Badge.tsx` or `Card.tsx`) are simplified versions of their `ui/` counterparts, tailored for this project's specific design.
