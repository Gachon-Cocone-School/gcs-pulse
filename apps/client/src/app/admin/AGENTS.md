# Admin Area (src/app/admin)

## OVERVIEW
`/admin` is the restricted management area.

- Protected at the layout level via `<ProtectedRoute adminOnly>`.
- Uses an internal sidebar menu to navigate between admin subsections.

## ROUTES
| Route | File |
|------|------|
| `/admin` | `src/app/admin/page.tsx` |
| `/admin/users` | `src/app/admin/users/page.tsx` |
| `/admin/role-rules` | `src/app/admin/role-rules/page.tsx` |
| `/admin/terms` | `src/app/admin/terms/page.tsx` |
| `/admin/permissions` | `src/app/admin/permissions/page.tsx` |

## WHERE TO LOOK
| File | Purpose |
|------|---------|
| `src/app/admin/layout.tsx` | Wraps all admin routes; enforces admin-only access and renders sidebar |

## CONVENTIONS
- **Access control**: rely on the layout wrapper; individual pages should not re-implement auth checks.
- **Admin check**: `ProtectedRoute` considers a user admin if `user.roles.includes('admin')`.

## NOTES
- If a user is authenticated but not an admin, `ProtectedRoute adminOnly` redirects to `/`.
