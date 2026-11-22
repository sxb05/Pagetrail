# Pagetrail Design Decisions

## 1. Reference and inspiration mapping

- Linear: dense, restrained navigation and fast keyboard-oriented workflows.
- Plane: structured project boards, clear status labels and compact operational panels.
- Asana: project health, milestones and task queues with readable summaries.
- Attio: calm typography, precise borders and low-noise data density.
- Notion: flexible document/context surfaces and familiar section hierarchy.
- Land-book, Mobbin and Design Spells: editorial composition, discoverable interactions and deliberate motion.

## 2. Application navigation

- Overview is the default authenticated destination.
- Projects remains the project-management destination.
- AI Assistant owns the existing chat, RAG, conversation and web-search experience.
- Overview uses direct links into projects and assistant actions.

## 3. Overview dashboard

- Start with a compact command bar for `Ask Pagetrail`.
- Show project, task and attention metrics.
- Add work distribution, pending tasks, upcoming milestones, recent activity and project health.
- Use real API data only. Agent insights remain empty until a real agent-insight workflow exists.

## 4. Project workspace

- Preserve Projects and project-detail routes.
- Keep project tabs, task status controls, milestones and project metadata in a single scrollable workspace.
- Use orange for primary actions and project selection; green only for completed/healthy status.

## 5. AI assistant and approvals

- Keep the assistant in `/app` as a dedicated section.
- Prefill the assistant from Overview command prompts.
- Show pending approvals only when records exist in the backend.
- Never fabricate agent output or approval counts.

## 6. Landing page

- Keep the public landing expressive and editorial.
- Retain the supplied GridScan background only; avoid stacking additional hero effects.
- Keep Sign in and Start organising persistent in the fixed navigation.
- Use section anchors with reliable smooth scrolling and scroll offsets.

## 7. Colour and typography

- Near black: `#111111`
- White: `#FFFFFF`
- Warm off-white: `#F3F0EB`
- Orange: `#F07836`
- Peach: `#FFB477`
- Neutral grey: borders and secondary text
- Green: success, completed and healthy status only

Typography uses the existing DM Sans and Geist/monospace display tokens.

## 8. Components and animation

- Reuse Lucide icons, Motion/AnimatePresence and existing CSS tokens.
- Reuse the existing operations panels and status components.
- Use restrained entrance and hover motion; disable or reduce it for `prefers-reduced-motion`.
- Do not add overlapping React effects or third-party UI libraries.

## 9. Existing components reused

- Overview
- Projects
- app workspace/sidebar
- authentication shell
- project metrics API
- project and task APIs
- existing chat, RAG and Gemini integration
