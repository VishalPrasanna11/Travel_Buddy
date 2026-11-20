# DESIGN.md: TravelBuddy

Status: **Phase 2 (foundations) complete.** Tokens live in `client/src/global.css` (`@theme`). Motion presets live in `client/src/lib/motion.ts`. Surface-level work (landing, chat states, itinerary rendering) comes in Phase 3. See §6 for what is still drifting.

---

## 1. Brand palette (LOCKED, source of truth)

The ten hex values below never change. Each one is a Tailwind v4 `@theme` token. Tailwind's default palette is switched off (`--color-*: initial`), so `gray-500`, `blue-600` and the like generate nothing. Only these tokens exist.

| Token (`bg-*`, `text-*`, …) | Role | Hex | As text on white | `#374151` text on it |
|---|---|---|---|---|
| `raspberry` | Primary | `#AA4465` | 5.64:1 ✅ | 1.83 ❌ (use white: 5.64 ✅) |
| `amber` | Secondary / accent | `#F5A65B` | 2.00 ❌ | 5.15 ✅ |
| `teal-blue` | Tertiary | `#96C3CE` | 1.91 ❌ | 5.40 ✅ |
| `leaf-green` | Quaternary | `#6CAE75` | 2.64 ❌ | **3.90 ❌** |
| `sunshine-yellow` | Highlight | `#FFCF00` | 1.48 ❌ | 6.96 ✅ |
| `soft-pink` | Subtle | `#F4CAE0` | 1.46 ❌ | 7.05 ✅ |
| `white` | Background | `#FFFFFF` | n/a | 10.31 ✅ |
| `ink` | Foreground | `#374151` | 10.31 ✅ | n/a |
| `light-gray` | Muted | `#E9E9E9` | 1.21 ❌ | 8.49 ✅ |
| `red` | Destructive | `#EF4444` | **3.76 ❌** | 2.74 ❌ |

Rules:
- Only `raspberry` and `ink` are text colors on white. All other brand colors are fills, borders, icons or chart colors.
- Text on Amber, Teal Blue, Sunshine Yellow, Soft Pink or Light Gray is `ink`.
- Leaf Green and Red never carry text. Use their derived tint or ink tokens.
- No gradient text, decorative halos, blurred glows, purple/blue gradients, neon, beige or cream.

## 2. Derived tokens (oklch, from the locked hue)

| Token | From | oklch | ≈ hex | Use | Contrast |
|---|---|---|---|---|---|
| `raspberry-hover` | Raspberry | 0.48 0.137 2.8 | `#993456` | primary hover | white 7.05 |
| `raspberry-pressed` | Raspberry | 0.43 0.137 2.8 | `#882449` | primary active | white 8.77 |
| `raspberry-tint` | Raspberry | 0.965 0.025 2.8 | `#FFEDF2` | selected/hover wash (`accent`) | ink 9.15, raspberry 5.01 |
| `ink-muted` | Dark Gray | 0.50 0.024 259.7 | `#5B6472` | secondary text, metadata, placeholders (`muted-foreground`) | 5.98 on white, 4.93 on Light Gray |
| `gray-sunken` | Light Gray | 0.975 0 0 | `#F7F7F7` | quiet surfaces (`muted`) | ink 9.62 |
| `gray-strong` | Light Gray | 0.82 0 0 | `#C4C4C4` | control borders (`input`), non-text | n/a |
| `leaf-tint` | Leaf Green | 0.93 0.037 147.6 | `#D8EFDA` | success surface | ink 8.48 |
| `leaf-ink` | Leaf Green | 0.50 0.096 147.6 | `#397242` | success icon/text | 5.74 on white |
| `red-ink` | Red | 0.52 0.177 25.3 | `#B92D2F` | error text, destructive fill (`destructive`) | 6.04 both ways with white |
| `red-tint` | Red | 0.96 0.025 25.3 | `#FFECE9` | error surface | ink 9.04, red-ink 5.77 |
| `amber-tint` / `amber-ink` | Amber | 0.94 0.039 62.5 / 0.50 0.104 62.5 | `#FFE6D1` / `#8C5416` | stay chip / stay icon | ink 8.59 / 6.19 on white |
| `teal-tint` / `teal-ink` | Teal Blue | 0.95 0.020 214.4 / 0.48 0.040 214.4 | `#E0F2F7` / `#43646C` | flight chip / flight icon | ink 8.94 / 6.41 on white |
| `sunshine-tint` | Sunshine | 0.96 0.062 91.8 | `#FFF1C3` | "Estimate" surface | ink 9.14 |

## 3. Palette roles

| Color | Job | Semantic tokens |
|---|---|---|
| Raspberry | The only "act here" color: primary buttons, links, focus ring, selected state, assistant mark, attraction pins | `primary`, `ring`, `sidebar-primary` |
| Amber | Secondary accent. **Hotels / stays.** Secondary button fill. | `secondary`, `stay`, `stay-tint`, `stay-ink` |
| Teal Blue | **Flights** | `flight`, `flight-tint`, `flight-ink` |
| Leaf Green | **Confirmations and live data** | `success`, `success-tint`, `success-ink` |
| Sunshine Yellow | **Estimates and warnings** (simulated weather label). Fill only, sparingly. | `estimate`, `estimate-tint` |
| Soft Pink | **Subtle surfaces**: user message bubble, text selection | (raw) `soft-pink` |
| Light Gray | Borders, dividers | `border` |
| Red | Errors and destructive actions via `red-ink` / `red-tint` | `destructive`, `danger-tint` |
| Ink | Body text; restaurant pins on the map | `foreground` |
| Attractions, restaurants | Neutral cards with a Raspberry icon | |

Map pins: attractions `#AA4465`, hotels `#F5A65B`, restaurants `#374151`.

## 4. Type

- **Display:** Bricolage Grotesque, 500–700, optical sizing on (`font-display`, applied to h1–h4). Warm, slightly quirky grotesque; gives headings a voice without shouting.
- **Text:** Atkinson Hyperlegible Next, 400–700 (`font-sans`, body). Built for legibility. Its distinct numerals (slashed zero, open 1/l/I) help with flight codes, times and prices on phones.
- **Mono:** Atkinson Hyperlegible Mono (`font-mono`, code blocks).
- Loaded from Google Fonts with `preconnect` in `index.html` (no render-blocking CSS `@import`).

| Token | Size / line-height | Use |
|---|---|---|
| `text-display` | clamp(36→44px) / 1.1, −0.02em | page hero (max one per page) |
| `text-title` | 24 / 32, −0.01em | section / page titles |
| `text-heading` | 18 / 24 | card and day headings |
| `text-body` (= `text-base`) | 16 / 24 | body, chat answers |
| `text-sm` | 14 / 20 | secondary UI text |
| `text-meta` (= `text-xs`) | 13 / 18 | prices, times, ratings, captions (use `.tabular`) |

Legacy `text-4xl`–`text-6xl` are capped at 44px, so no oversized heroes.
Headings get `text-wrap: balance`; paragraphs and list items get `text-wrap: pretty`.
Answers use a reading width of `max-w-prose` (68ch).
`time`, `data` and `.tabular` use tabular numerals.

## 5. Space, radius, shadow, motion

- **Spacing:** Tailwind 4px base. Named: `gutter` 16px (phone side padding), `gutter-lg` 32px, `section` clamp(56→96px), `header` 64px.
- **Radius:** `rounded-control` 10px (buttons, inputs), `rounded-surface` 16px (cards, panels), `rounded-full` (pills, avatars, chips). Legacy `rounded-3xl` is capped at 20px.
- **Shadow:** two real levels, both ink-tinted. `shadow-raised` (= `shadow-sm`) for resting surfaces, `shadow-overlay` (= `shadow-lg`) for popovers and floating panels. `shadow-xl` and `shadow-2xl` collapse to overlay. Cards are border-only by default.
- **Motion:**
  - Durations: fast 150ms (hover, press), base 200ms (UI changes), slow 280ms (layout shifts).
  - Easing: `ease-out` (quart) for routine UI, `ease-out-expo` for larger moves, `ease-in` for exits. No bounce or elastic.
  - Keyframes: `animate-fade-in`, `animate-rise-in`, `animate-breathe` (opacity only, for waiting indicators).
  - `prefers-reduced-motion: reduce` collapses all CSS animations and transitions to 1ms globally.
  - Framer Motion uses `transition.fast/base/slow` from `lib/motion.ts`.
- **Focus:** one style everywhere: 2px Raspberry outline, 2px offset (`:focus-visible`). Inputs add a 2px Raspberry ring at 25%.
- **Touch:** buttons and inputs grow to 44px on coarse pointers (`pointer-coarse:`).

## 6. Components (shared)

| Component | File | Variants / notes |
|---|---|---|
| Button | `ui/button.tsx` | `default` (Raspberry, one per view), `secondary` (Amber), `outline`, `ghost`, `destructive` (red-ink), `link`. Sizes `sm`/`default`/`lg`/`icon`. |
| Badge / Chip | `ui/badge.tsx` | `default`, `secondary`, `outline`, `neutral`, `destructive`, plus category chips `flight`, `stay`, `success`, `estimate`, `subtle`. Text is always ink or white. |
| Input | `ui/input.tsx` | 16px text on phones (no iOS zoom), `gray-strong` border, Raspberry focus. |
| Card | `ui/card.tsx` | Bordered `rounded-surface`, no shadow. Never nest cards. |
| Notice | `ui/notice.tsx` | `info`, `error` (role=alert), `success`, `estimate`. Title + description + actions (Retry / Edit query / New trip). |
| EmptyState | `ui/empty-state.tsx` | Icon in a Raspberry tint, title, description, actions; heading level is configurable. |
| MessageRow | `ui/message-row.tsx` | `user`: right-aligned Soft Pink bubble. `assistant`: full reading width with the TravelBuddy mark, no bubble. Includes screen-reader speaker labels. |
| App shell | `layouts/layout.tsx` | `variant="page"` (document scroll) or `"app"` (`h-dvh` workspace; panes scroll). Skip link, single `<main>`. Sidebar is a drawer on mobile; inert when collapsed on desktop. |

Planned for Phase 3, built against real response fields: FlightSummary, HotelSummary, PlaceCard (photo), DaySection, AgentProgress.

## 7. Still drifting (tracked for later phases)
- Landing and home content: pill badge above the headline, colored keyword in the headline, gradient washes, a side-tab border (`LandingPage.tsx:115`), a nested card, skipped heading levels, fake stats and testimonials. **Phase 3.**
- `Hero.tsx` bounce scroll hint and pulse circles; Steps pulse glow. **Phase 3/4.**
- The map "Detected Locations" panel uses side-tab borders. **Phase 3.**
- `WeatherDisplay` structure (duplicate content, no estimate label). **Phase 3.**
- Mixed `font-medium` vs `font-semibold` on headings in older pages. **Phase 3, as surfaces are rebuilt.**
- Dark mode: none. The old `.dark` block with altered brand hexes was removed. `dark:` utilities are inert.
- Bundle: entry JS 436 KB gzip (unchanged). Shiki still ships every grammar. **Phase 5.**
