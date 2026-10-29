# SHADOWOPS — Production Monorepo

> **"Your AI Security Team. Always Watching."**

ShadowOps is an AI-native cybersecurity SaaS platform designed primarily for startups and engineering teams. It continuously discovers vulnerabilities, analyzes findings with specialized AI security agents, correlates them into attack paths, prioritizes risk with deterministic formulas, produces human-approved remediations, empirically verifies fixes, and reports security posture.

---

## Technical Stack Architecture

- **Frontend**: Next.js 14 (App Router), TypeScript (Strict), Tailwind CSS, Lucide Icons, React Query, Zustand.
- **Backend**: Python 3.11+, FastAPI Core, SQLAlchemy 2.0 (async), Pydantic v2, structlog.
- **Database**: Supabase PostgreSQL 16+ with Row Level Security (RLS) policies.
- **Storage**: Supabase Storage (S3-compatible object storage with signed URLs).
- **Authentication**: Firebase Authentication (ID Token verification via Firebase Admin SDK).
- **AI Orchestration**: Multi-model routing abstraction supporting Google Gemini & xAI Grok.
- **Code Analysis**: Semgrep SAST/SCA runner interface.
- **Deployment**: Railway multi-service production topology.

---

## Directory Structure

```
shadowops/
├── frontend/             # Next.js 14 App Router client application
│   ├── app/              # Routes, layout, and pages
│   ├── components/       # Design system foundation (cards, buttons, tables, badges)
│   ├── lib/              # API client, Firebase client, utils
│   ├── hooks/            # Custom React hooks
│   └── types/            # TypeScript API and entity definitions
├── backend/              # Python FastAPI REST API server
│   ├── app/
│   │   ├── api/          # Route handlers (/api/v1/*)
│   │   ├── core/         # Settings, logging, config
│   │   ├── db/           # Database sessions, base models
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic v2 request/response schemas
│   │   ├── services/     # Business logic layer
│   │   ├── repositories/ # Database data access layer
│   │   ├── security/     # Firebase auth dependency, permissions
│   │   ├── ai/           # AI provider abstraction (Gemini / Grok)
│   │   ├── scanners/     # Semgrep runner abstraction & normalizer
│   │   └── workers/      # Asynchronous worker boundary specifications
│   └── tests/            # Automated Pytest suite
├── supabase/
│   └── migrations/       # Canonical PostgreSQL DDL migrations & RLS policies
├── docs/                 # Architectural specifications and reports
└── scripts/              # Helper utility scripts
```

---

## Stage 1: Production Foundation

This repository contains the verified Stage 1 technical foundation:
- Typed, parameterized database repository layer.
- Firebase Auth JWT verification dependency with automatic user profile mapping.
- Workspace membership and role-based access control (OWNER, ADMIN, MEMBER, VIEWER).
- Mandatory security boundary: `NO AUTHORIZATION → NO SCAN`.
- Pluggable AI provider abstraction for Gemini and Grok with structured schema support.
- Ephemeral Semgrep runner integration boundary.
- Reusable dark cybersecurity command center UI component foundation.
