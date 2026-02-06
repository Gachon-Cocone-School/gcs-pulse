# Auth Context (src/context)

## OVERVIEW
This directory owns client-side auth state and user identity.

- `AuthProvider` loads session state on mount via `/auth/me`.
- `useAuth()` is the only supported way to access `{ user, isAuthenticated, isLoading, checkAuth, logout }`.

## WHERE TO LOOK
| File | Purpose | Notes |
|------|---------|------|
| `src/context/auth-context.tsx` | Auth context + hook | Defines `User` shape (roles, consents) and exposes auth actions. |

## CONVENTIONS
- **App-wide mount**: Provider is mounted from `src/app/layout.tsx`.
- **Initial auth check**: `AuthProvider` calls `checkAuth()` in an effect.
- **Cookie auth**: `checkAuth()` uses `api.get('/auth/me')` (which uses `credentials: 'include'`).
- **Logout flow**: `logout()` calls `/auth/logout`, clears local auth state, then hard-navigates to `/`.

## NOTES / GOTCHAS
- `checkAuth()` toggles `isLoading` internally; consumers should gate redirects/UI using `isLoading`.
- Error handling in `checkAuth()` currently logs and forces `{ isAuthenticated: false, user: null }`.
- `User.roles` is used for admin checks (see `ProtectedRoute` / admin layouts).
