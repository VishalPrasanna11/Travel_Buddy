# DESIGN.md: TravelBuddy

Status: **Phase 1 draft.** This file documents the current system as it is in code (Nov 2026), corrected with the locked brand palette, and flags drift. Final tokens, type scale, components and motion rules get filled in during Phase 2 and Phase 6.

---

## 1. Brand palette (LOCKED, source of truth)

These ten hex values do not change. Each one becomes a Tailwind v4 `@theme` token.

| Token | Role | Name | Hex | As text on white | `#374151` text on it |
|---|---|---|---|---|---|
| `--color-raspberry` | Primary | Raspberry | `#AA4465` | 5.64:1 ✅ | 1.83:1 ❌ (use white: 5.64:1 ✅) |
| `--color-amber` | Secondary / accent | Amber | `#F5A65B` | 2.00:1 ❌ | 5.15:1 ✅ |
| `--color-teal-blue` | Tertiary | Teal Blue | `#96C3CE` | 1.91:1 ❌ | 5.40:1 ✅ |
| `--color-leaf-green` | Quaternary | Leaf Green | `#6CAE75` | 2.64:1 ❌ | **3.90:1 ❌** (needs a lighter derived tint behind body text) |
| `--color-sunshine` | Highlight | Sunshine Yellow | `#FFCF00` | 1.48:1 ❌ | 6.96:1 ✅ |
| `--color-soft-pink` | Subtle | Soft Pink | `#F4CAE0` | 1.46:1 ❌ | 7.05:1 ✅ |
| `--color-white` | Background | White | `#FFFFFF` | n/a | 10.31:1 ✅ |
| `--color-ink` | Foreground | Dark Gray | `#374151` | 10.31:1 ✅ | n/a |
| `--color-light-gray` | Muted | Light Gray | `#E9E9E9` | 1.21:1 ❌ | 8.49:1 ✅ |
| `--color-red` | Destructive | Red | `#EF4444` | **3.76:1 ❌** | 2.74:1 ❌ (white on it: 3.76:1 ❌) |

Rules:
- Only Raspberry and Dark Gray may be used as text on white. Every other brand color is a fill, border, icon, or chart color.
- When text sits on Amber, Teal Blue, Sunshine Yellow, Soft Pink or Light Gray, it is `#374151`.
- Leaf Green and Red cannot carry readable text in either direction at AA. They need derived tokens (below).
- No gradient text. No decorative radial halos or blurred glows. No purple/blue gradients, neon, beige or cream.

### Palette roles (proposed, confirm before Phase 2)
| Color | Job |
|---|---|
| Raspberry | Primary buttons, links, focus rings, selected states, active nav. The only "act here" color. |
| Amber | Secondary accent. **Hotels / stays** (icon, card accent, chip fill). |
| Teal Blue | **Flights** (icon, route line, chip fill). |
| Leaf Green | **Confirmations and live data**: success toasts, "live weather" marker, good-weather icon. |
| Sunshine Yellow | **Attention, used sparingly**: the "Estimate" label on simulated weather, warnings. Fill only. |
| Soft Pink | **Subtle surfaces**: user message bubble, selected sidebar row, hover wash on primary-adjacent elements. |
| Light Gray | Borders, dividers, input outlines, skeletons. |
| Red | Destructive actions and errors, via the derived accessible shade. |
| Attractions, restaurants | Neutral cards with a Raspberry icon. They are the main itinerary content, so they get no extra hue. |

### Derived tokens (to be finalized in Phase 2, in oklch)
Each one is derived from a locked color and documented here. Targets:

| Token | Derived from | Purpose | Target |
|---|---|---|---|
| `--color-raspberry-hover` | Raspberry, darker in oklch L | Primary hover | white text ≥ 4.5:1 |
| `--color-raspberry-pressed` | Raspberry, darker still | Primary active | white text ≥ 4.5:1 |
| `--color-raspberry-tint` | Raspberry, very light | Selected row, subtle focus wash | `#374151` ≥ 4.5:1 |
| `--color-ink-muted` | Dark Gray, lighter | Secondary text, metadata, placeholders | ≥ 4.5:1 on white **and** on Light Gray |
| `--color-leaf-tint` | Leaf Green, lighter | Success surface behind text | `#374151` ≥ 4.5:1 |
| `--color-leaf-ink` | Leaf Green, darker | Success icon or text where needed | ≥ 4.5:1 on white |
| `--color-red-ink` | Red, darker | Error text, destructive button fill with white text | ≥ 4.5:1 |
| `--color-red-tint` | Red, very light | Error surface | `#374151` ≥ 4.5:1 |
| `--color-amber-tint`, `--color-teal-tint`, `--color-sunshine-tint` | respective color, lighter | Category chips and cards | `#374151` ≥ 4.5:1 |

---

## 2. Current state in code (as found)

### Color
- Tokens live in `client/src/global.css` as shadcn-style CSS variables (`--primary`, `--secondary`, …) mapped through `@theme inline`. The locked hexes are present and correct in `:root`.
- ~350 lines of hand-written utilities (`.bg-raspberry`, `.bg-raspberry\/10`, gradient helpers, `.animate-pulse`, `.scale-110`, `.blur-lg`, `.font-sans`) duplicate what Tailwind v4 generates from `@theme`. Several override Tailwind's own utilities with v3 syntax (`--tw-scale-x` etc.).
- **Drift:**
  - `--muted-foreground: #9ca3af` is not a brand color and fails contrast (2.54:1 on white, 2.1:1 on Light Gray). It is used for all secondary text.
  - `.dark` block redefines brand colors to new hexes (`#c25a7b`, `#ffb76e`, `#a8d4df`, …). Nothing toggles dark mode, so it is dead, but it contradicts the locked palette.
  - Stray Tailwind colors in components: `text-gray-*` (≈35), `bg-black` / `text-black` (13), `text-blue-*`, `bg-blue-50`, `border-blue-100` (weather card), `text-red-500`, `text-green-500`, `text-orange-500`, `bg-orange-600` (user avatar), `to-indigo-50`, `text-yellow-500`.
  - Raw hex in TSX: `#d1d5db`, `#9CA3AF`, `#4B5563`, `#333`.
  - Footer is `bg-black` with the default `#374151` heading on it (2.04:1).
  - `.text-amber`, `.text-teal-blue`, `.text-leaf-green` utilities exist and are used as text (fail AA).

### Typography
- Inter from Google Fonts, 300–700 (flagged by `impeccable detect` as overused). Loaded via CSS `@import` (render-blocking).
- No type scale. Sizes in use: `text-xs` 16×, `text-sm` 51×, `text-base` 2×, `text-lg` 6×, `text-xl` 21×, `text-2xl` 4×, `text-3xl` 11×, `text-4xl` 8×, `text-5xl` 1×, `text-6xl` 4×.
- Chat body text is `text-sm` (14px). Should be ~16px with 1.5 line-height and a 65–75ch measure.
- Weights drift between `font-medium` and `font-bold` for the same role (logo is `font-medium` in the header and `font-bold` in the sidebar).
- `.text-balance` and `.text-pretty` are defined but not used on headings or paragraphs.

### Radius
- `--radius: 0.5rem` with sm/md/lg/xl derived. In use: `rounded-full` 30×, `rounded-lg` 14×, `rounded-md` 8×, `rounded-3xl` 4×, `rounded-xl` 3×, plus `rounded`, `rounded-l`, `rounded-r`. Buttons are pill in the sidebar and `rounded-md` elsewhere.

### Spacing and layout
- No spacing rhythm. `container mx-auto py-6` wraps every page inside `Layout`, so full-bleed sections (landing hero, footer) are boxed, and the chat page gets extra padding inside a fixed-height split.
- Heights use `h-screen` and `calc(100vh-64px)` (breaks with mobile browser chrome and on-screen keyboard). No `dvh`/`svh`, no safe-area insets.

### Shadows
- `shadow-sm`, `shadow-md`, `shadow-lg`, `shadow-xl` mixed with no scale. Blurred gradient glow behind the landing preview card.

### Motion
- Framer Motion entrance on almost every landing element (0.5s, staggered), with reveal-on-scroll that **leaves 65% of landing text at opacity 0** (detector: `content-hidden-at-rest`).
- Endless `animate-pulse` on decorative elements, `animate-bounce` scroll hint, bouncing typing dots (`@keyframes bounce` defined twice). No `prefers-reduced-motion` handling anywhere.

### Components (current)
- shadcn/ui "new-york" primitives in `components/ui/` (button, card, badge, tabs, sheet, sidebar, dropdown, tooltip, popover, calendar, etc.).
- Two parallel chat stacks:
  - `components/ChatComponent.tsx` (live, used by `/chat/:id`): hand-rolled regex markdown → `dangerouslySetInnerHTML`.
  - `components/ui/chat.tsx` + `message-list` + `chat-message` + `markdown-renderer` (react-markdown + Shiki): used only by `/chatmaps` and the unrouted `ChatPage`.
- Duplicate files: `pages/ChatMapsPage 2.tsx`, `types/geocodingService 2.ts`, `types/locationUtils 2.ts`.

---

## 3. To be defined in Phase 2
- Type: new families (display + text), scale, line-heights, measure.
- Spacing scale and section rhythm.
- Radius scale (one for controls, one for surfaces, one for pills).
- Shadow scale (two levels at most).
- Motion tokens: durations (fast 150ms, base 200ms, slow 250–300ms), easing (ease-out quart/expo), reduced-motion policy.
- Component variants: Button, Chip, Card (Flight, Hotel, Place), MessageBubble, EmptyState, ErrorBlock, AgentProgress.
