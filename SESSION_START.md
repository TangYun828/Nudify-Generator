# Session Start - Read Me First

This document is the required entry point for any new AI session. Always read this file first before taking actions.

## Project Goal

Build a production-ready, legally compliant NSFW image generation platform with:
- A unified FastAPI backend running inside Nudify-Generator (RunPod)
- Supabase PostgreSQL for user management, credits, and verification records
- JWT auth, API keys, and credit enforcement
- Mandatory age verification (Yoti/Veriff/Persona) per 2026 compliance
- Vue 3 frontend (nudify_us-website) with login/register/verification flow

## System Architecture (Current Plan)

Single-container backend (RunPod):
- Nudify-Generator repo hosts Fooocus + FastAPI
- Integrated user management code from nudify-backend
- Protected endpoint /v1/engine/generate/ requires:
  - Valid JWT
  - is_verified == true and not expired
  - Credits available

Data layer (Supabase PostgreSQL):
- Tables: users, credits, usage_logs, age_verifications
- SQLAlchemy ORM models
- setup_db.py initializes schema and seed test user

Frontend (Vercel):
- nudify_us-website (Vue 3)
- JWT stored client-side
- Call verification status before enabling generation

## Repository Locations (Local)

Main root: C:\working folder\intimai\
- nudify_us-website\ (frontend repo development)
- nudify-backend\    (RunPod endpoint backend)
- Nudify-Generator\  (upstream backend to merge into)

## What Is Already Done

Code complete in nudify-backend:
- database.py, security.py, schemas.py, schemas_verification.py
- db_models: user, credits, usage_log, age_verification
- routes: auth, user, credits, verification
- middleware: auth
- setup_db.py and requirements_versions.txt

Docs complete in nudify-backend:
- QUICK_START.md (copy-paste commands)
- MIGRATION_MERGE_STRATEGY.md (merge guide)
- QUICK_MERGE_CHECKLIST.md (short checklist)
- COMPLETE_ROADMAP.md (full plan)
- TROUBLESHOOTING.md (common issues)
- FILE_INVENTORY.md (file reference)
- OPTIMIZED_ARCHITECTURE.md (architecture)
- AGE_VERIFICATION_COMPLIANCE.md (legal)
- API_ENDPOINTS_REFERENCE.md (API docs)

## Work History (High Level)

1) Designed Supabase schema (users, credits, usage_logs, age_verifications)
2) Implemented full FastAPI auth + user + credits + verification routes
3) Added JWT auth, bcrypt hashing, API keys
4) Added age verification flows and admin overrides
5) Documented architecture and merge plan
6) Optimized to single RunPod container approach
7) Created multiple guides for merge, testing, and deployment

## Where We Stopped Last Time

- New session summary documents were created for onboarding.
- This file (SESSION_START.md) is the latest entry point.
- No merge into Nudify-Generator has been executed yet.
- Supabase project creation may still be pending.
- Frontend login/register pages are not built yet.

## Current Status (To Confirm)

Pending tasks likely still open:
- Create Supabase project and set env vars
- Clone Nudify-Generator and merge files
- Update handler.py to integrate FastAPI + Fooocus
- Test locally
- Implement frontend auth + verification flow
- Deploy to RunPod

## Required First Actions For Any New Session

1) Read this file fully.
2) Confirm whether Supabase project and credentials exist.
3) Check if Nudify-Generator repo has been cloned.
4) Ask user which phase to start: Supabase setup or code merge.

## Quick Links (Start Here)

- QUICK_START.md: Copy-paste commands for setup
- COMPLETE_ROADMAP.md: Full plan with phases
- MIGRATION_MERGE_STRATEGY.md: Exact merge instructions
- TROUBLESHOOTING.md: Fix common issues

## Notes

- Legal compliance requires real age verification (not a simple age gate).
- All work should stay under C:\working folder\intimai\
- Use intimai as the main root and keep frontend in nudify_us-website and backend in nudify-backend.
- Avoid splitting into multiple services; keep single container architecture.
- Maintain existing repo history; do not reset or delete git data.
