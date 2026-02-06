# shadcn/ui Layer (src/components/ui)

## OVERVIEW
This directory contains mostly shadcn/ui-style components (Radix primitives + Tailwind classes).

- These components are intended to be *reused* and kept relatively generic.
- Project-specific composition should generally live in `src/components/` or `src/components/views/`.

## WHERE TO LOOK
| File | Purpose |
|------|---------|
| `src/components/ui/utils.ts` | `cn()` helper (clsx + tailwind-merge) |
| `src/components/ui/button.tsx` | CVA-based button with `asChild` support |
| `src/components/ui/form.tsx` | React Hook Form bindings/patterns |
| `src/components/ui/sidebar.tsx` | Sidebar primitives used by layouts |

## CONVENTIONS
- **Classnames**: use `cn()` for conditional classes.
- **Radix wrappers**: most components are thin wrappers around Radix (props-forwarding is the norm).
- **Keep it “headless-ish”**: avoid coupling to auth/API or route logic here.

## ANTI-PATTERNS
- Adding backend calls or app navigation logic in `src/components/ui/*`.
- Duplicating `cn()` usage patterns instead of importing from `ui/utils`.

## NOTES
- Many files here are copied/generated; prefer minimal, surgical changes.
