# TravelBuddy UI makeover: final report

Branch `ui_fix` · Nov 2026 · Phases 1–6 · Frontend only. No backend, API contract, auth config or deployment changes. The 10 brand hexes are unchanged.

Source of truth: [`/DESIGN.md`](../../DESIGN.md) (tokens, roles, type, components, motion) and [`/PRODUCT.md`](../../PRODUCT.md). Phase 1 findings: [`phase-1-findings.md`](phase-1-findings.md).

## Results at a glance

| | Before | After |
|---|---|---|
| Entry JS (gzip) | 435 KB | **202 KB** |
| Build output | 338 files, 14 MB (every Shiki grammar) | **32 files, 4.2 MB** (6 grammars, lazy) |
| Impeccable `detect src/` | 3 issues + 3 advisories | **0** |
| Impeccable live `/` | 8 issues (contrast, hidden content, side-tab, nested cards, skipped headings) | **0** (`/waitlist`, 404 also 0) |
| WCAG text contrast failures | secondary text 2.5:1, footer 2.0:1, Amber/Teal/Leaf as text | none found; every text pair is ≥ 4.5:1 |
| TypeScript errors | 83 | 25 (all pre-existing, in legacy files) |
| Horizontal scroll at 360 / 390 / 768 / 1024 / 1440 | chat text overflowed into the map | none (measured) |

## What changed, per surface

### Foundations (Phase 2)
- Tailwind v4 `@theme`: locked hexes, AA-verified oklch tints and shades, semantic and category roles, sidebar tokens, a type scale, spacing, radius, two shadow levels, motion tokens. The default Tailwind palette is disabled.
- Type: Bricolage Grotesque (display) and Atkinson Hyperlegible Next/Mono (text, code). 16px body, 68ch answers, balance/pretty wrapping, tabular numerals for prices and times.
- Shared primitives: Button, Badge (flight/stay/success/estimate chips), Input, Tabs, Card, Dialog, Notice, EmptyState, Skeleton, MessageRow.

### Chat (Operate + Read)
- **Fixed P0s:**
  - Double submit no longer drops answers. There's an in-flight guard, functional state updates, and no fake Stop button.
  - Answers render through safe markdown (no raw HTML); the old regex → `dangerouslySetInnerHTML` path is gone.
  - "Start New Chat" no longer overwrites history; it opens a new trip.
  - Messages no longer hide under the header, and the composer is never covered by the map.
- **Waiting:** an honest progress card with stage text, elapsed time, and what's being checked (Flights, Hotels, Places to see, Restaurants, Weather). It never marks a step done. A screen-reader live region announces the start and the result.
- **Answers:**
  - Headings, lists, tables and code (lazy Shiki, palette theme, scrolls inside its box) render properly, and the stray `<br/>` tags are cleaned up.
  - Result cards come only from returned fields: places with 4:3 lazy photos, alt text, a fallback icon, rating and review count, address and "Open in Google Maps"; hotel and flight rows when the API returns them.
  - Copy answer button.
- **Weather honesty:** the backend's simulated template is detected and labelled "Weather is an estimate."
- **Errors:** timeout, network, server and cut-off answers each get their own title and body, with **Try again**, **Edit question** and **Start a new trip**. Error turns are never sent back to the model as history.
- **Composer:** Enter / Shift+Enter, IME-safe, 44px send, a sending state, autosize, hint text, safe-area padding.
- **Scroll:** follows only when you're at the bottom; otherwise a "Jump to latest" pill appears.
- **Onboarding:** "Where are you headed?" with 4 realistic example trips (no invented data).
- **Trip history:** the sidebar lists saved trips from IndexedDB with active state, relative dates, Rename and Delete (confirmed in a dialog), and live updates. It says plainly that trips are saved on this device.
- **Map:** opt-in toggle below 1280px. Zoom fits the pins (Lisbon now opens at street level, not continent). The places panel is collapsible, with keyboard buttons and colored dots plus a legend (no side-tabs). Pins survive reloads.
- **Home → chat:** the home launcher's prompt is auto-sent once, and the router state is cleared so a refresh doesn't resend it.

### Landing (Persuade) and Home
- **Landing:**
  - One Raspberry CTA ("Plan a trip", Auth0 signup) and a quiet "See how it works".
  - A realistic answer preview labelled "Example", with no prices, ratings or availability.
  - An uneven 3-step explainer that names the data sources.
- **Removed:** badge above the headline, colored keyword, gradients, halo, avatar stack, "50,000+", mindmap, pulsing glows, bounce, side-tab, nested card, and the wrong product name ("TravelMood AI").
- **Home:**
  - A real "Describe your trip" launcher and 4 example trips.
  - "Ideas to explore" with lazy images, fallbacks and marked external links.
  - Removed fake stats, "98% Match" scores, fake personalization, testimonials, the typing-animation fake search and the dead `/ai-planner` form.
- **Footer:** light surface, newsletter kept, dead legal and social links removed, GitHub link added.

### Flights, waitlist, auth, system
- **Flights:**
  - Uses `VITE_BASE_URL` instead of localhost. **The fake-flight generator is deleted.**
  - Designed idle, loading, error (Try again / Edit search), empty and results states, using the real response shape.
- **Waitlist:** honest "not built yet" copy, accessible errors, a way back. The 5 unbuilt sidebar items are now clearly marked "Soon", as are Upgrade/Account/Billing in the account menu.
- **Auth:**
  - Calm loader while Auth0 checks the session.
  - Signed-out deep links and expired sessions go to sign-in and come back to the same page.
  - The callback awaits user creation and has an error screen.
- **System:**
  - 404 page and an app-wide error boundary.
  - Lazy routes.
  - `/chat` → new trip, `/chatmain/:id` → `/chat/:id`.
  - Dead duplicate files deleted.

### Motion, responsive, accessibility (Phases 4–5)
- **Motion:** CSS motion tokens throughout. Message rise-in 220ms, drawer 280ms expo-out, dialog fade+scale. View Transitions cross-fade on route changes where supported. Global reduced-motion rule. No bounce, no decorative loops.
- **Responsive:** checked at 360, 390, 768, 1024 and 1440: no horizontal scroll; 44px targets on touch; drawer below md; chat/map split from xl.
- **Accessibility:**
  - Skip link first, one `<main>`, one `h1` per page, no skipped heading levels on any route checked.
  - Visible Raspberry focus everywhere; labelled icon buttons; the collapsed sidebar is inert.
  - Radix dialogs trap focus and return it.
  - Live regions for waiting, answers and errors; external links announced.

## Screenshots (`docs/ui-makeover/screenshots/`)

| Before | After |
|---|---|
| `before-landing-desktop.jpg` | `after-landing-desktop.jpg` |
| `before-landing-mobile-hidden-sections.jpg` (sections blank) | `after-landing-mobile.jpg` |
| `before-home-desktop.jpg` | `after-home-desktop.jpg` |
| `before-chat-746-text-over-map.jpg` | `after-chat-desktop-answer.jpg`, `after-chat-desktop-places-weather.jpg`, `after-chat-desktop-waiting.jpg` |
| `before-chat-mobile-composer-hidden.jpg` | `after-chat-mobile-answer.jpg`, `after-chat-mobile-welcome.jpg`, `after-chat-mobile-error.jpg` |
| `before-mobile-drawer-transparent.jpg` | `after-mobile-drawer-history.jpg` |

## Verified live (signed in, `localhost:3000`)
- Home → chat handoff.
- Waiting card and live announcements.
- A real Lisbon answer with headings, photos and the estimate notice.
- Double Enter while pending sends nothing.
- Simulated network failure → error turn → Edit question (Try again uses the same path).
- Rename dialog focus in and out.
- Skip link first.
- Mobile drawer, map toggle, and layout at 360, 390, 768, 1024 and 1440.

**Not verified:**
- Signed-out deep-link return and the Auth0 error screen (they need a logout).
- A real timeout or server error from the backend.
- Responses that include flights or hotels data. None of my test queries returned it; the rows are built against the typed shape.
- Reduced-motion emulation (the tool can't toggle it; enforced in CSS).
- Impeccable live scans of signed-in routes (the CLI can't sign in; source scan and manual audit cover them).

## Needs backend work (reported, not changed)
1. **Per-agent progress.** `/api/llm/ask-question` only streams keep-alive spaces. Real progress needs SSE or NDJSON events (e.g. `{"agent":"flights","state":"done"}`).
2. **Weather is simulated and mis-keyed.** Every report in our tests was the fixed "22°C, clear skies" template. Locations are parsed from query fragments ("adults with flights", "hotels"). Add `is_simulated` / `source` and use the resolved destination as the key.
3. **Errors after streaming starts.** If the agent fails after keep-alive bytes, the client gets HTTP 200 plus a truncated body. Send a final JSON error object instead.
4. **Auth.** `ask-question` takes no bearer token and trusts `user_email` from the body.
5. **Places API key exposure.** Every `photo_url` embeds the server's Google API key. Proxy photos through the backend, or return short-lived media URLs.
6. **Invented pricing in prompts.** The planning prompt asks the LLM to "simulate" seat and room pricing (`server/subagents/planning/prompt.py:183,305`). Hotel prices with "(saving $X)" appear in answer text with no structured source.
7. **Structured data gaps.** Hotels and flights rarely come back as structured fields (only text). The flights search response shape (`segments[]`, `fareSourceCode`) doesn't match the old frontend type, and there's no booking URL; "Book on airline site" links are best-effort and labelled as such.
8. **Topic filter.** It rejected "Best neighborhoods to stay in Lisbon?" as not travel-related.
9. **History is device-local** (IndexedDB). The backend stores chat history (`/api/user/...`), but the UI has no API to list it. Cross-device history needs an endpoint.

## Remaining frontend items
- `/chatmaps` (a demo against a stub echo endpoint) is restyled but still on the legacy chat kit and Framer Motion.
- The thumbs up/down feedback was replaced by **Copy answer**. Feedback had no backend; restore it when an endpoint exists.
- `package-lock.json` is out of sync with `package.json` (`npm ci` fails). Unchanged, because the Docker build skips the lockfile.
- 25 pre-existing TypeScript errors in legacy files (calendar/date-picker library drift, `@ai-sdk/react` v4 API in ChatMapsPage, Maps loader options).
- Impeccable skills weren't installed in Claude Code; the CLI detector (`impeccable@4.10.0`, telemetry off) plus the Impeccable rules were applied by hand.
