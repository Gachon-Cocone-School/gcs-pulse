# Page Views (src/components/views)

## OVERVIEW
This directory contains “full page” view components used by the App Router entrypoints.

These are larger compositions (layout + copy + components) that keep `src/app/*` thin.

## WHERE TO LOOK
| File | Purpose |
|------|---------|
| `src/components/views/MainDashboard.tsx` | Main dashboard showcase view |
| `src/components/views/AccessDenied.tsx` | No-roles / access denied view (includes logout CTA) |

## CONVENTIONS
- Views are typically **client components** and freely compose `src/components/*` atoms.
- Gatekeeping / routing decisions should remain in `src/app/page.tsx`; views should just render.

## NOTES / GOTCHAS
- `AccessDeniedView` calls `useAuth().logout()` and includes a small “ID” string derived from `window.location.host`.
- These views currently use the **custom** component set (`../Button`, `../Card`, etc.), not `src/components/ui/*`.
