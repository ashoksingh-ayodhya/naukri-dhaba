# Naukri Dhaba Visual QA & UX Audit

Date: 2026-03-16  
Scope reviewed: `index.html`, `latest-jobs.html`, `admit-cards.html`, `results.html`, `resources.html`, `study-planner.html`, `eligibility-calculator.html`, global CSS.

## Executive summary
The site has a clear overall structure, but there are several consistency and UX risks that will be visible to users on static hosting and on accessibility-sensitive devices:

1. **Navigation/link consistency is broken for static `.html` pages** (high impact).
2. **Design system is bypassed by heavy inline styling**, which causes visual drift and difficult maintenance.
3. **Some color choices have weak contrast** (notably warning states), reducing readability.
4. **Mobile/tablet experiences rely on horizontal scrolling in key tables** and hidden sidebars, reducing discoverability.
5. **Inconsistent information hierarchy and CTA styling** can make scanning and next action unclear.

---

## Findings

### 1) Extensionless internal links can break navigation on static hosting (High)
- Across pages, header/footer links use routes like `/latest-jobs` and `/results`, while files in the repo are `latest-jobs.html`, `results.html`, etc.
- If the server/CDN doesn’t rewrite extensionless routes, users will hit “Not Found” pages.

**Examples**
- Header uses `/latest-jobs`, `/results`, `/admit-cards`, `/resources`.  
- Footer/tools use `/eligibility-calculator`, `/study-planner`, `/previous-papers`.

**UX impact**
- Broken primary navigation destroys trust and increases bounce rate.

**Recommendation**
- Standardize links to explicit `.html` paths (or guarantee rewrite rules at the edge and keep one convention consistently).

### 2) Broken quick-link destinations in footer/tools (High)
- Multiple pages link to `/syllabus.html` and `/cut-off-marks.html`, but these files are not present in the repository root.

**UX impact**
- Dead-end links in “Quick Tools” feel low quality and frustrate users in high-intent flows.

**Recommendation**
- Either add the missing pages or remove/hide those links until available.

### 3) Heavy inline styling undermines design patterns (Medium)
- Many pages use large amounts of inline styles (especially `latest-jobs.html`), bypassing reusable CSS classes.
- This causes inconsistent spacing, typography, and component behavior over time.

**UX impact**
- Users perceive subtle inconsistency (“looks stitched together”), especially when moving between pages.

**Recommendation**
- Move repeated inline styles into named utility/component classes in `css/style.css`.
- Keep layout primitives (cards, sections, CTA rows, status labels) centralized in CSS.

### 4) Warning-state text color has low contrast on white backgrounds (Medium)
- `.table__row--warning` uses `color: var(--warning)` where `--warning` is `#ffc107` (yellow).
- On white/light backgrounds this is hard to read.

**UX impact**
- Important status information can be missed, especially in bright environments and by low-vision users.

**Recommendation**
- Use a darker amber/brown for text (e.g., `#8a6d00`) and reserve bright yellow for badges/background accents.

### 5) Dark mode token exists but is not consistently supported (Medium)
- Theme variables are defined for `[data-theme="dark"]`, but many elements use hardcoded light colors inline (e.g., `#666`, white surfaces, etc.).

**UX impact**
- Potentially inconsistent visuals/contrast if dark mode is activated now or later.

**Recommendation**
- Replace hardcoded inline colors with theme tokens.
- Add a short visual regression checklist for both themes.

### 6) Mobile information architecture can hide useful content (Low/Medium)
- Sidebar is removed on widths `<1024px`, taking away state selector, quick tools, and upcoming deadlines.
- Table wrappers become cards on mobile, but tablet users near breakpoints may still face dense layouts.

**UX impact**
- Important navigation/support widgets vanish rather than relocate, reducing discoverability.

**Recommendation**
- Promote top 2–3 sidebar tools into the main content on mobile.
- Validate breakpoints around 768–1024px with real-device checks.

---

## Quick wins (priority order)
1. Fix all internal navigation/quick links (`.html` consistency + remove dead links).
2. Replace warning yellow text with accessible contrast color.
3. Refactor repeated inline styles into shared utility/component classes.
4. Reintroduce critical sidebar utilities in mobile content flow.
5. Add a lightweight visual QA checklist before deploy:
   - Home + top 4 pages on desktop/mobile.
   - Header/footer link validation.
   - Contrast check for status colors and CTAs.

