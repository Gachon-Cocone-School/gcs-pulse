# App Router & Routes (src/app)

## OVERVIEW
This directory contains the core routing logic, layouts, and page components of the Modern LMS application using the **Next.js App Router**. It manages the user flow, from authentication and onboarding to the main dashboard and admin areas.

## STRUCTURE
- `/admin`: Restricted management area for users, roles, and terms.
- `/login`: Entry point for Google OAuth authentication.
- `/terms`: Mandatory onboarding flow for legal agreements.
- `page.tsx`: The root "Gatekeeper" that orchestrates user redirection.
- `layout.tsx`: Root layout providing `AuthProvider` and global styles.

## WHERE TO LOOK
| File | Purpose | Key Logic |
|------|---------|-----------|
| `src/app/page.tsx` | **Gatekeeper** | Orchestrates `auth` -> `terms` -> `roles` redirection flow. |
| `src/app/layout.tsx` | Root Layout | Wraps the application with `AuthProvider` and imports global CSS. |
| `src/app/globals.css` | Global CSS | Primary Tailwind v4 configuration and global design tokens. |
| `src/app/admin/layout.tsx` | Admin Layout | Protects all nested `/admin` routes using `<ProtectedRoute adminOnly>`. |
| `src/app/terms/page.tsx` | Terms Onboarding | Handles mandatory user consent submission. |

## CONVENTIONS
- **'use client' usage**: Most pages and layouts in this directory are client components because they rely on `useAuth()` and `useRouter()` for dynamic redirection.
- **Gatekeeper Flow**:
  1. **Unauthenticated**: Render `LoginPage` (or redirect).
  2. **Authenticated but No Terms**: Redirect to `/terms`.
  3. **No Roles**: Show `AccessDeniedView`.
  4. **All Clear**: Show `MainDashboardView`.
- **Styling**: `src/app/globals.css` is the source of truth for global styles and Tailwind v4 theme variables.

## ANTI-PATTERNS
- **Direct Auth Logic in Sub-pages**: Avoid manually checking `isAuthenticated` in every admin page. Use the `AdminLayout`'s `ProtectedRoute` wrapper instead.
- **CSS Duplication**: Do not rely on `src/styles/globals.css` for new styles; use `src/app/globals.css` or component-level styling.

## NOTES
- `src/styles/globals.css` exists as a secondary or legacy file; always prefer `src/app/globals.css` for design system tokens.
- Gatekeeper logic in `src/app/page.tsx` is central to the application security; modify with caution.
