# API Client Knowledge Base

## OVERVIEW
The `src/lib` directory contains the core API client for the application. It provides a lightweight, consistent interface for making HTTP requests to the backend server, ensuring that all requests are properly formatted and authenticated.

## WHERE TO LOOK
- **`src/lib/api.ts`**: The primary file containing the `apiFetch` utility and the `api` helper object for standard HTTP methods.

## CONVENTIONS
- **Base URL**: The client uses the `NEXT_PUBLIC_API_URL` environment variable. If not provided, it defaults to `http://localhost:8000`.
- **API Helper**: Use the `api` object for most interactions:
  - `api.get(endpoint, options)`
  - `api.post(endpoint, data, options)`
  - `api.put(endpoint, data, options)`
  - `api.delete(endpoint, options)`
- **Auth Credentials**: All requests include `credentials: 'include'`, which is essential for cookie-based session management across different domains/ports.
- **Automatic JSON**: The client automatically adds `'Content-Type': 'application/json'` to headers and stringifies request bodies for POST and PUT methods.

## ANTI-PATTERNS
- **Bypassing `apiFetch`**: Avoid calling `fetch` directly for backend requests; the wrapper standardizes `credentials: 'include'` + error parsing.
- **Inconsistent endpoint shape**: Pick a convention for endpoints (leading `/` vs none) and stick to it across the app.

## NOTES / GOTCHAS
- **Auth Gatekeeping (401)**: The `/auth/me` endpoint has a special-case handler. If it returns a `401 Unauthorized` status, the client returns `{ authenticated: false, user: null }` instead of throwing an exception, allowing the application to handle the "not logged in" state gracefully.
- **204 No Content**: For HTTP 204 responses, the client returns an empty object `{}` to prevent JSON parsing errors.
- **Error Propagation**: For other non-OK statuses, the client attempts to parse the error message from the backend's `detail` or `message` fields before throwing a standard `Error`.
