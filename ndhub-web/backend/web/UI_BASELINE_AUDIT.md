# ND-Hub Web UI Baseline Audit

Date: 2026-04-23

## Scope
- `/web/index.html`
- `/web/styles.css`
- `/web/app.js`

## Baseline findings

1. Tables are rendered directly in cards and can overflow on medium viewports.
2. Global table styles used clipping (`overflow: hidden`) without horizontal scroll containers.
3. Toolbar label widths can force awkward wrapping in dense forms.
4. Visual tokens existed, but semantic aliasing and spacing tiers were incomplete.
5. Several rendering paths in `app.js` interpolated row data into `innerHTML`.
6. Large monolithic UI logic in `app.js` reduced maintainability.

## Target outcomes implemented in this iteration

- Add semantic design token aliases while keeping existing palette continuity.
- Introduce a unified responsive table shell pattern.
- Improve component hierarchy (cards, toolbar, form controls, badges, status).
- Harden key renderers with safe text insertion helpers.
- Start incremental modularization with shared utility module loading.
- Add Vite + React foundation and first island mounting points.

