# Team Feed Comments Design

## Overview
Add a commenting feature to the Team Feed to allow team members to leave feedback and discussions on Daily and Weekly snippets. The feature will support markdown text and a flat comment structure.

## Goals
-   Enable communication within the team via snippets.
-   Keep the UI clean by expanding comments only when requested.
-   Allow users to comment on their own snippets (self-reflection or additional notes).

## Architecture

### Database Schema
New `Comment` model in `apps/server/app/models.py`:
-   `id`: Integer, PK
-   `user_id`: Integer, FK to `users.id`
-   `daily_snippet_id`: Integer, FK to `daily_snippets.id`, Nullable
-   `weekly_snippet_id`: Integer, FK to `weekly_snippets.id`, Nullable
-   `content`: Text (Markdown support)
-   `created_at`: DateTime
-   `updated_at`: DateTime

Constraints:
-   Check constraint to ensure either `daily_snippet_id` OR `weekly_snippet_id` is set (not both, not neither - or at least one). Actually, for simplicity, we can make both nullable but enforce logic that exactly one is set.

### API Endpoints
New router `apps/server/app/routers/comments.py`:
-   `POST /comments`: Create a comment. Payload: `{ content, daily_snippet_id?, weekly_snippet_id? }`
-   `GET /comments`: List comments. Query params: `daily_snippet_id` OR `weekly_snippet_id`.
-   `PUT /comments/{id}`: Update comment (Author only).
-   `DELETE /comments/{id}`: Delete comment (Author only).

Modifications to `daily_snippets.py` and `weekly_snippets.py`:
-   Update `DailySnippetResponse` and `WeeklySnippetResponse` to include `comments_count: int` (computed field).

### Frontend
-   **`CommentList` Component**:
    -   Displays a list of comments.
    -   Includes a textarea for adding a new comment.
    -   Handles edit/delete actions for own comments.
    -   Renders markdown.
-   **`TeamSnippetCard` Component**:
    -   Add a "💬 N" button.
    -   Clicking toggles the `CommentList` visibility.
    -   Fetches comments when expanded.
-   **`TeamSnippetFeed` Component**:
    -   Remove the filter that hides the current user's snippets.

## detailed Implementation Steps

1.  **Backend**
    -   Define `Comment` model in `models.py`.
    -   Create migration script (if using alembic/migration tool, otherwise sync DB). *Note: The project seems to use `scripts/init_db.py` or similar. I'll check `apps/server/scripts`.*
    -   Create Pydantic schemas in `schemas.py`.
    -   Implement CRUD in `crud.py`.
    -   Create `routers/comments.py` and register in `main.py`.
    -   Update Snippet read operations to include comment counts.

2.  **Frontend**
    -   Update `api.ts` types.
    -   Create `components/views/CommentList.tsx`.
    -   Update `components/views/TeamSnippetCard.tsx`.
    -   Update `components/views/TeamSnippetFeed.tsx` to show own posts.

## Security & Permissions
-   **Read**: Anyone in the team can read comments on visible snippets.
-   **Write**: Authenticated users can create comments.
-   **Update/Delete**: Only the comment author can update/delete.

## Future Considerations (Out of Scope)
-   Notifications (Slack/Email).
-   Nested replies (Threads).
-   Rich text editor.
-   Reactions (Emoji).
