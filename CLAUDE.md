# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

- **Type**: Monorepo managed by TurboRepo
- **Client**: Next.js 16 (App Router), React 18, Tailwind CSS, Radix UI
- **Server**: FastAPI (Python), SQLAlchemy, AsyncPG
- **Language**: TypeScript (Frontend), Python (Backend)

## Build & Run

### Root
- **Install Dependencies**: `npm install`
- **Start Dev Server**: `npx turbo run dev` (starts both client and server)
- **Build**: `npx turbo run build`
- **Lint**: `npx turbo run lint`

### Client (`apps/client`)
- **Start Dev**: `npm run dev` (runs `@react-grab/opencode` hook + `next dev`)
- **Build**: `npm run build`
- **Lint**: `npm run lint`
- **Test**: No test script currently configured.

### Server (`apps/server`)
- **Setup**: `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
- **Start Dev**: `uvicorn app.main:app --reload`
- **Test**: `pytest` (configuration in `pytest.ini`)
- **Lint/Format**: Follow Python standards (no specific script in root package.json for server linting, but check `apps/server/scripts/` if needed).

## Code Structure

### Client (`apps/client/src`)
- **`app/`**: Next.js App Router pages and layouts.
- **`components/`**: React components.
  - **`ui/`**: Reusable UI components (Radix/Tailwind based).
  - **`views/`**: Feature-specific view components.
- **`lib/`**: Utilities and API clients (`api.ts`).
- **`context/`**: React context providers (e.g., `auth-context.tsx`).
- **`styles/`**: Global styles (`globals.css`).

### Server (`apps/server`)
- **`app/`**: Main application code.
  - **`routers/`**: API route definitions.
  - **`models.py`**: SQLAlchemy database models.
  - **`schemas.py`**: Pydantic models for request/response validation.
  - **`crud.py`**: Database CRUD operations.
  - **`database.py`**: Database connection and session handling.
- **`tests/`**: Pytest tests (`test_e2e.py`, `test_features.py`, etc.).
- **`scripts/`**: Utility scripts for DB init, migration, and inspection.

## Conventions

- **Language**:
  - **Output**: Korean (한국어) for user interactions.
  - **Internal**: English for thinking and searching.
- **Paths**: Always use absolute paths.
- **Naming**:
  - **React Components**: PascalCase (e.g., `Button.tsx`)
  - **TypeScript Utilities**: camelCase (e.g., `formatDate.ts`)
  - **Python Files**: snake_case (e.g., `main.py`)
- **Design System**: Refer to `apps/client/docs/design-system.md` before creating UI.

## Architecture Notes

- **Communication**: Client communicates with Server via REST API.
- **Database**: PostgreSQL (inferred from `asyncpg`).
- **Authentication**: Authlib used on server.
- **Validation**: Zod (Client) and Pydantic (Server).
