# Snippet Error UI, Time Constraints, Team View, and Token Management Design

## 1. Overview
This document outlines the design for four key features:
1.  **Common Error UI**: A standardized error presentation adhering to the design system.
2.  **Snippet Time Constraints**: Strict server-side validation for daily (9:00 AM cutoff) and weekly (Monday 9:00 AM cutoff) snippet creation.
3.  **Team Snippet View**: A unified feed view for team members' snippets including AI analysis.
4.  **API Token Management**: A simple interface for users to generate and manage Bearer tokens for API access.

## 2. Architecture & Design

### 2.1 Common Error UI
-   **Goal**: consistent error feedback using `design-system.md` (Rose-500, Slate-50).
-   **Frontend**:
    -   **Global Toast**: Use `sonner` for API errors caught in `api.ts`.
    -   **Error Page**: New `components/views/ErrorView.tsx` for 403/404/500 page-level errors.
        -   Style: Centered layout with `ShieldAlert` icon, similar to `AccessDenied.tsx`.
-   **Backend**:
    -   Standardized `HTTPException` with clear detail messages.

### 2.2 Snippet Time Constraints (Strict Mode)
-   **Goal**: Enforce business rules for when snippets can be created/edited.
-   **Rules**:
    -   **Daily**: Before 9:00 AM -> Previous business day only. After 9:00 AM -> Current day only.
    -   **Weekly**: Before Mon 9:00 AM -> Previous week only. After Mon 9:00 AM -> Current week only.
-   **Logic Location**: `apps/server/app/utils_time.py`
    -   `validate_snippet_date(target_date: date)`: Raises 400 if `target_date` != `current_business_date()`.
    -   `validate_snippet_week(target_week: date)`: Raises 400 if `target_week` != `current_business_week_start()`.
-   **API Integration**:
    -   `POST /daily-snippets`: Call `validate_snippet_date`.
    -   `POST /weekly-snippets`: Call `validate_snippet_week`.

### 2.3 Team Snippet View
-   **Goal**: View teammates' snippets and AI feedback in a single feed.
-   **Frontend**:
    -   **Component**: `TeamSnippetFeed.tsx`
    -   **Layout**: Vertical list of cards. Each card shows:
        -   Header: User Avatar + Name + Date.
        -   Content: Snippet text (collapsible if long).
        -   Footer: AI Summary Badge + Toggle for full `SnippetAnalysisReport`.
-   **Backend**:
    -   `GET /daily-snippets` and `GET /weekly-snippets` already support team visibility via `snippet_utils.can_read_snippet`.
    -   Add `scope=team` query parameter to list endpoints to filter/fetch team snippets explicitly if needed, or just rely on the existing list logic if it returns all accessible snippets. *Decision: Modify list endpoints to return all accessible snippets (own + team) by default or via flag.*

### 2.4 API Token Management
-   **Goal**: Allow users to generate long-lived tokens for external API usage.
-   **Database**:
    -   New Table: `api_tokens`
        -   `id`: Integer, PK
        -   `user_id`: Integer, FK -> `users.id`
        -   `token`: String (Hashed/Encrypted or just random string if stored securely? *Decision: Store hashed, return once.*) -> *Correction for MVP: Store random string, if high security needed hash it. For this scope, standard opaque token stored as-is or hashed is fine. Let's store hashed for security best practice.*
        -   `description`: String (e.g., "My Script Token")
        -   `created_at`: DateTime
        -   `last_used_at`: DateTime (optional)
-   **API Endpoints**:
    -   `GET /auth/tokens`: List own tokens.
    -   `POST /auth/tokens`: Create new token (returns raw token once).
    -   `DELETE /auth/tokens/{id}`: Revoke token.
-   **Frontend**:
    -   **Page**: `apps/client/src/app/settings/page.tsx` (or new route).
    -   **UI**: List of active tokens + "Generate Token" button.

## 3. Implementation Steps

1.  **Backend Core**: Implement time validation logic in `utils_time.py`.
2.  **Backend Snippets**: Apply validation to `daily_snippets.py` and `weekly_snippets.py`.
3.  **Backend Tokens**: Create `ApiToken` model, CRUD, and `auth.py` endpoints.
4.  **Frontend Error UI**: Create `ErrorView.tsx` and integrate global error handling.
5.  **Frontend Tokens**: Implement Token Management UI in Settings.
6.  **Frontend Team View**: Implement `TeamSnippetFeed.tsx` and integrate into main navigation.
