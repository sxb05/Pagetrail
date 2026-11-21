# Pagetrail frontend redesign

## Reference research

The following references were inspected for design principles and interaction
patterns:

- React Bits: source-owned animated components, restrained backgrounds and
  discoverable micro-components.
- Motion: layout transitions, AnimatePresence, gesture feedback and reduced
  motion.
- Aceternity UI: selective spotlight, network and bento patterns.
- Magic UI: restrained bento layouts and lightweight status effects.
- AIDesigner: a single animated hero effect, capped motion and static
  fallbacks.
- Mobbin: real-product authentication, navigation, forms, empty states and
  responsive application patterns.
- Land-book: editorial hierarchy, strong art direction and composed SaaS
  sections.
- Design Spells: purposeful hover, press, loading and contextual feedback.

Design Spells and Land-book returned access limits during automated fetches;
the design principles documented above were applied without copying a specific
site or component.

## Design system

The public and application surfaces now share:

- restrained near-black and pale sage surfaces;
- warm amber only as a small existing-brand accent;
- serif/monospace and sans-serif type combinations;
- 8/12/16/24/40px spacing rhythm;
- 8/12/16/22px radius hierarchy;
- spring and 150-700ms duration easing;
- light borders, low-contrast elevation and visible keyboard states;
- reduced-motion fallbacks.

## Landing

The landing route remains at `/`. It now communicates AI project operations,
with a functional fluid hero, navigation anchors, an interactive product
preview, bento capabilities, an operational process timeline, workspace
preview, final CTA and compact footer.

The WebGL fluid background remains a single signature effect and retains an
CSS fallback for unsupported environments.

The hero copy and headline match the project operations positioning, while the
shader palette is restricted to the existing teal, sage and amber brand tones.
Desktop navigation uses styled anchors and mobile navigation has a functional
menu with reduced-motion-safe behaviour.

## Authentication

`/login` and `/signup` retain the existing username/password API handlers.
They now use a split brand/story and form composition, password visibility,
loading feedback and existing validation/error behavior. No authentication
field or endpoint was added or replaced.

## Application workspace

The existing sidebar, chat, conversation history, document upload and project
routes are preserved. The Projects destination remains in the sidebar and
uses real API-backed data. Project dashboard and detail styling remain
consistent with the application shell.

## Accessibility and responsiveness

The redesign uses semantic navigation, labelled form controls, visible focus
states, responsive media layouts and `prefers-reduced-motion` fallbacks.
Mobile auth, landing and project layouts were adjusted with a stacked/single
column composition.

## Verification

- Frontend production build: passed.
- Full backend suite: 27 passed, 2 skipped.
- Vite landing and login routes: HTTP 200 on local smoke check.
- Existing chat, auth, RAG, LangGraph and project tests passed in the backend
  suite.
- No backend endpoints or authentication contracts were changed.
