# UI Makeover — API Requirements

> What the server needs to deliver for a first-rate frontend experience.
> Each item names the UX it unlocks. Today the frontend works around these gaps, mostly with guesses and labels.

## P0: needed for a top-tier experience

### 1. Stream progress and results, not keep-alive spaces
Today `ask-question` sends spaces for 30–40 seconds, then everything at once. The UI can only show a time-based guess.
- Add `POST /api/llm/ask` returning Server-Sent Events (or NDJSON), and keep the current endpoint for compatibility.
- Events needed:
```
event: agent    {"agent":"flights","state":"running"}            // queued|running|done|empty|failed|skipped
event: section  {"type":"restaurants","items":[...]}             // send each section as soon as it's ready
event: delta    {"text":"Day 1 starts in Alfama..."}             // answer text, token by token
event: final    {"request_id":"r_123","itinerary":{...}}
event: error    {"code":"FLIGHTS_TIMEOUT","retryable":true,"section":"flights"}
```
- **UX:** a real checklist ("Hotels ✓ 8 found · Flights: no results"), result cards appearing as they arrive, and an answer that types in. Waiting stops feeling like a frozen screen.

### 2. A structured itinerary, not just markdown
Answers today are flat lists in markdown; there was no day-by-day plan even when asked for one.
```json
"trip": { "destination": {"name":"Lisbon","place_id":"…","lat":38.72,"lng":-9.14,"timezone":"Europe/Lisbon"},
          "origin":"BOS", "start_date":"2027-03-12", "end_date":"2027-03-15", "travelers":{"adults":2} },
"days": [ { "date":"2027-03-12", "items":[ {"slot":"morning","kind":"place","ref":"pl_1","note":"Go early"} ] } ]
```
- Keep `answer` as the narrative summary.
- **UX:** day-by-day sections, a timeline, "Day 2" on the map, calendar export.

### 3. One schema per entity, with source and freshness
Every Place, Hotel, Flight and Weather item needs `id`, `source` (`google_places` / `routestack` / `openweather`), `fetched_at`, and `is_estimate`.
- **Prices must be data, never only prose:**
```json
"price": {"amount":277.70,"currency":"USD","basis":"per_night","total":833.10,"taxes_included":true,"as_of":"2026-11-20T09:12Z"}
```
- **UX:** reliable price chips, "prices as of 9:12" freshness notes, sorting and filtering, and no invented numbers.

### 4. Per-section status for partial results
```json
"sections": { "flights": {"status":"empty","message":"No flights BOS→LIS on Mar 12","alternatives":["2027-03-13"]},
              "hotels": {"status":"ok","count":8},
              "weather": {"status":"estimate","reason":"provider_unavailable"} }
```
- **UX:** "No flights that day — try Mar 13" with a one-tap retry for just that section.

### 5. Honest weather
- Every report in tests was the simulated "22°C, clear skies" template.
- Needs: `is_simulated` / `source`, keyed to the resolved destination, daily forecast for trip dates.
- **UX:** a real forecast strip per day, or a clear "Estimate" badge.

### 6. A consistent error contract, even mid-stream
```json
{"error": {"code":"AGENT_TIMEOUT","message":"Flight search took too long","retryable":true,"section":"flights","request_id":"r_123"}}
```
- Today a failure after the keep-alive bytes returns HTTP 200 and a truncated body.
- Also: `429` with `Retry-After`, and an `Idempotency-Key` header.
- **UX:** exact, actionable error messages, safe retries, and a support reference number.

### 7. Authentication and privacy
- Require the bearer token on `ask` and identify the user from the token, not `user_email` in the body.
- Proxy photos through `GET /api/places/photo/{ref}?w=640`, cached and returned with `width`, `height` and attribution.
- **UX:** faster, stable images with correct aspect ratios, no layout shift, required Google attribution.

## P1: what makes it feel polished

| # | API | UX it unlocks |
|---|---|---|
| 8 | **Conversation API:** `GET/POST/PATCH/DELETE /api/conversations` | History across devices, rename and delete synced everywhere |
| 9 | **Cancel:** `DELETE /api/llm/ask/{request_id}` | A real Stop button |
| 10 | **Clarifying questions:** `type:"clarification"`, `missing:["origin","dates"]` | Quick-reply chips or a mini form |
| 11 | **Out of scope:** `status:"out_of_scope"`, `reason`, `suggestions[]` | Helpful redirects instead of refusals |
| 12 | **Follow-up suggestions:** `suggestions:["Add a Sintra day trip","Cheaper hotels"]` | One-tap refinement chips |
| 13 | **Flights:** segments, layovers, ISO 8601 durations, local times with UTC offsets, baggage, booking URL | Real "Book" buttons, correct timezone display |
| 14 | **Hotels:** check-in/out, nightly and total price, star vs guest rating, amenities, cancellation, booking URL | Comparable hotel cards |
| 15 | **Places:** opening hours, price level, categories, google_maps_uri, editorial summary | "Closed Mondays" warnings, filters |
| 16 | **Destination geocode + map bounds** | Map opens on the right area before results arrive |
| 17 | **Feedback:** `POST /api/feedback {message_id, rating, reason}` | Restore thumbs buttons |

## P2: scale and delight
- Performance targets: first event <1s, first section <8s, p95 total <30s, compression, caching.
- Preferences: locale, currency, units, home airport, traveler defaults.
- Sharing and export: share link, .ics, PDF.
- Saved places / bookmarks.
- OpenAPI spec + fixture responses.
- Data integrity: stop the planning prompt from simulating prices.

**Suggested order:** 1 (streaming), 3 and 4 (entities and section status), 6 and 7 (errors, auth, photos), 5 (weather), then 2 (itinerary) and 8 (history).
