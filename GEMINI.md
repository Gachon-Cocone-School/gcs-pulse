# Project: GCS LMS (Learning Management System)

## Overview
This is a monorepo project for a Learning Management System.
- **Root**: Project orchestration and docs.
- **apps/client**: Frontend application.
- **apps/server**: Backend application.

## Tech Stack

### Client (`apps/client`)
- **Framework**: Next.js 16 (App Router)
- **Language**: TypeScript (5.9.3)
- **UI Library**: React 18, Radix UI, Tailwind CSS
- **State/Form**: React Hook Form, Zod
- **Icons**: Lucide React
- **Package Manager**: NPM (via Turbo)

### Server (`apps/server`)
- **Framework**: FastAPI (Python)
- **Server**: Uvicorn
- **Database ORM**: SQLAlchemy (AsyncPG)
- **Auth**: Authlib
- **Environment**: Python Virtualenv (`venv`)

## Architecture
- **Monorepo**: Managed by TurboRepo.
- **API Communication**: Client consumes FastAPI endpoints.

## Conventions
- **Language**: 
  - **Thinking/Search**: English
  - **User Output**: Korean (한국어)
- **Path**: Always use absolute paths.
- **File Naming**: 
  - React Components: PascalCase (e.g., `Button.tsx`).
  - Utilities: camelCase (e.g., `formatDate.ts`).
  - Python files: snake_case (e.g., `main.py`).

## Agent Roles
Refer to [AGENTS.md](file:///Users/hexa/projects/temp/gcs-lms/AGENTS.md) for agent definitions.
