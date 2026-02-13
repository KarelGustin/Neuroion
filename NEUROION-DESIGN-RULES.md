# Neuroion design rules

Use this document to keep all Neuroion UIs (touchscreen-ui, setup-ui, dashboard, etc.) visually and behaviorally consistent. The target aesthetic is **Vercel/Apple-like**: calm, premium, clear hierarchy, and plenty of whitespace.

---

## 1. Design tokens

Define these (or equivalent) in each app so values stay consistent. Prefer CSS custom properties in a single `variables.css` or theme file.

### 1.1 Colors

| Token | Value | Use |
|-------|--------|-----|
| `--bg` | `#0a0a0a` | Page background (avoid pure `#000`) |
| `--bg-elevated` | `rgba(255, 255, 255, 0.03)` | Cards, buttons, elevated surfaces |
| `--border` | `rgba(255, 255, 255, 0.06)` | Subtle borders (low contrast) |
| `--text` | `#fafafa` | Primary text |
| `--text-secondary` | `#a1a1a1` | Labels, secondary copy |
| `--text-muted` | `#71717a` | Placeholders, hints |
| `--accent` | `#0071e3` | Primary actions, links, focus |
| `--accent-hover` | `#0077ed` | Hover state for accent |
| `--success` | `#30d158` | Success states, positive indicators |
| `--warning` | `#ff9f0a` | Warnings, confirm states |
| `--error` | `#ff453a` | Errors, destructive actions |
| `--error-bg` | `rgba(255, 69, 58, 0.15)` | Error banner background |
| `--error-border` | `rgba(255, 69, 58, 0.3)` | Error banner border |

### 1.2 Typography

| Token | Value | Use |
|-------|--------|-----|
| `--font-sans` | `"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif` | Body and UI |
| `--text-xs` | `11px` | Captions, metadata |
| `--text-sm` | `13px` | Secondary text, small labels |
| `--text-base` | `15px` | Body default |
| `--text-lg` | `17px` | Emphasized body |
| `--text-xl` | `20px` | Section titles, modal titles |
| `--text-2xl` | `24px` | Page section headers |
| `--text-3xl` | `28px` | Page title (e.g. app name) |
| `--font-normal` | `400` | Body |
| `--font-medium` | `500` | Buttons, labels |
| `--font-semibold` | `600` | Headings |
| `--tracking-tight` | `-0.02em` | Large headings (page title, card titles) |

- Use the type scale; avoid arbitrary font sizes.
- Apply `-webkit-font-smoothing: antialiased` and `-moz-osx-font-smoothing: grayscale` on `body`.

### 1.3 Spacing

Use a consistent scale. Prefer tokens over raw pixels.

| Token | Value |
|-------|--------|
| `--space-1` | 4px |
| `--space-2` | 8px |
| `--space-3` | 12px |
| `--space-4` | 16px |
| `--space-5` | 20px |
| `--space-6` | 24px |
| `--space-8` | 32px |
| `--space-12` | 48px |

- Grid gaps: `--space-4` (or `--space-6` for larger layouts).
- Section margins: `--space-6` or `--space-8`.
- Card/internal padding: `--space-4` to `--space-6`.

### 1.4 Radii

| Token | Value | Use |
|-------|--------|-----|
| `--radius-card` | `12px` | Cards, buttons, inputs |
| `--radius-modal` | `16px` | Modals, dialogs |
| `--radius-btn` | `12px` | Buttons (can match card) |

### 1.5 Shadows

| Token | Value | Use |
|-------|--------|-----|
| `--shadow-card` | `0 1px 3px rgba(0, 0, 0, 0.2)` | Cards |
| `--shadow-modal` | `0 8px 32px rgba(0, 0, 0, 0.4)` | Modals, overlays |

---

## 2. Component patterns

### 2.1 Cards

- Background: `var(--bg-elevated)`.
- Border: `1px solid var(--border)`.
- Border-radius: `var(--radius-card)`.
- Padding: `var(--space-5)` (or `--space-6`).
- Shadow: `var(--shadow-card)` (optional, subtle).
- No heavy borders or bright outlines.

### 2.2 Buttons

- **Primary:** Background and border `var(--accent)`, text white. Hover: `var(--accent-hover)`.
- **Secondary:** Background `var(--bg-elevated)`, border `var(--border)`. Hover: slightly lighter (`rgba(255,255,255,0.06)` bg, `rgba(255,255,255,0.1)` border).
- **Danger:** Background and border `var(--error)`. Use sparingly (e.g. restart, delete).
- **Confirm / long-press state:** `var(--warning)` (amber) so it’s clearly distinct.
- Min height for touch targets: **44px** (ideally **80px** for primary actions on touch UIs).
- Border-radius: `var(--radius-btn)`.
- Active/press: `transform: scale(0.98)`.
- Disable default tap highlight: `-webkit-tap-highlight-color: transparent`; use `touch-action: manipulation` where appropriate.

### 2.3 Modals / overlays

- Backdrop: `rgba(0, 0, 0, 0.6)` with `backdrop-filter: blur(12px)` (and `-webkit-backdrop-filter`). Provide a fallback (e.g. darker solid overlay) when blur isn’t supported or when `prefers-reduced-motion: reduce`.
- Modal container: same language as cards (`--bg-elevated`, `--border`, `--radius-modal`, `--shadow-modal`), with larger padding (e.g. `--space-8`).
- Click outside to close where it makes sense.

### 2.4 Icons

- Prefer **inline SVG** or a small icon set (e.g. Lucide-style). Avoid emoji for UI actions and status.
- Default size **24px** for actions and list items; use `currentColor` so icons inherit text color.
- Icon color: `var(--text-secondary)` next to titles; on buttons, inherit (white on primary/danger).

### 2.5 Status indicators

- **Success:** `var(--success)` (e.g. dot + “connected”).
- **Warning:** `var(--warning)` (e.g. “degraded”, “pending”).
- **Error:** `var(--error)` (e.g. “failed”, “disconnected”).
- Use a small dot (e.g. 10px) with optional soft glow; keep labels in `var(--text-secondary)`.

### 2.6 Error banners

- Background: `var(--error-bg)`, border: `var(--error-border)`, text: `var(--error)`.
- Border-radius: `var(--radius-card)`.
- Keep copy short; avoid harsh or flashing treatment.

### 2.7 Loading

- Prefer a **spinner** (simple CSS circle + rotation) over plain “Loading…” text.
- Spinner: border using `var(--border)` and `var(--accent)` (e.g. top segment), ~32px size.
- Optional label below in `var(--text-muted)`.

---

## 3. Layout

- **Max content width:** Consider ~900px for main content, centered, on large screens.
- **Padding:** Use spacing tokens (e.g. `--space-6` for page padding).
- **Background:** Default `var(--bg)`. Optional very subtle gradient (e.g. radial from top, `rgba(255,255,255,0.03)` to transparent) for depth; remove or simplify when `prefers-reduced-motion: reduce`.

---

## 4. Accessibility

- **Focus:** Remove default `outline`; use `:focus-visible` with a visible ring (e.g. `2px solid var(--accent)`, `outline-offset: 2px`) so keyboard users can see focus.
- **Motion:** Respect `@media (prefers-reduced-motion: reduce)`: disable or simplify animations (e.g. spinner, blur, transitions).
- **Touch:** Minimum 44px touch targets; for critical actions on kiosk/touch UIs, prefer larger (e.g. 80px min-height for primary buttons).
- **Color:** Don’t rely on color alone for status or actions; use text/labels and icons too.

---

## 5. Implementation per app

- **touchscreen-ui:** Reference implementation; uses `variables.css` and the patterns above.
- **setup-ui (Vite/React):** Add a `variables.css` (or copy from touchscreen-ui) and import it first; use the same tokens in component CSS.
- **dashboard (Next.js):** Use the same token names in CSS Modules, Tailwind theme, or global CSS so values match this doc. If using Tailwind, map `colors`, `fontSize`, `spacing`, and `borderRadius` to these tokens.

When in doubt, align with the touchscreen-ui implementation and this document.
