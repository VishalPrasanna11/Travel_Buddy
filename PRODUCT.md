# PRODUCT.md: TravelBuddy

## What it is
TravelBuddy is an AI travel planner. You describe a trip in one message. A multi-agent backend (root, planning, flights, hotels, attractions, restaurants, weather) gathers data and returns one full itinerary.

## Who uses it
- Travelers planning a whole trip in one conversation: where, when, how to get there, where to stay, what to do, where to eat.
- Often on a phone, often on the move, often impatient. A single answer can take 30–40 seconds.
- Not travel agents. They want an answer they can act on, not a research tool.

## The main job
1. Describe a trip (destination, dates, origin, travelers, budget, interests).
2. Wait while the agents work, and know that something is happening.
3. Read the itinerary, scan flights and hotels, look at places, and act on it (follow links, refine, start a new trip).

Everything else is secondary: history, account, flight search.

## Surfaces and modes
| Surface | Mode | Job |
|---|---|---|
| Landing `/` | Persuade | Show a concrete, realistic answer and get the visitor to sign in. |
| Home `/home` | Persuade → Operate | Signed-in entry point. Today it repeats marketing. It should launch a trip. |
| Chat `/chat/:id` | Operate | Compose, wait, recover from errors, switch trips. |
| Assistant response | Read | Long-form itinerary: day-by-day, flights, hotels, places, weather. |
| Places, photos, map | Experience | Look at where you are going. |
| Flights `/flights` | Operate | Direct flight search form and results. |
| Waitlist `/waitlist` | Persuade | Capture interest for features that are not built yet. |
| Auth callback, 404, errors | Operate | Get the user back on track fast. |

## Voice
Warm, confident, practical. Talks like a well-traveled friend who is organized: specific nouns, short sentences, no hype. Never "supercharge", "seamless", "world-class", "unlock". No slogan contrasts. Say what happened and what to do next.

## Hard constraints
- **Never invent travel data.** Prices, availability, ratings, review counts, dates, flight numbers, and match scores come only from the APIs (RouteStack for flights and hotels, Google Places for attractions, restaurants and photos, OpenWeather for weather). Placeholders and marketing examples must be clearly illustrative and must not show fake prices or ratings as fact.
- **Simulated weather is an estimate.** When OpenWeather is not configured or fails, the backend returns simulated weather. The UI must label it as an estimate and never present it as real.
- **No fake social proof.** No invented user counts, ratings, or testimonials.
- Brand palette is locked (see DESIGN.md).
- Frontend-only makeover. Backend logic, API shapes, auth config and deployment stay as they are. Response-shape problems are reported, not patched.

## Success looks like
- A first-time visitor understands what they will get within one screen.
- A signed-in user can start a trip in one tap from a realistic example.
- During the wait, the user knows which kinds of data are being gathered and roughly how long it takes, without fake "done" claims.
- A full itinerary is easy to scan on a 390px phone, with no horizontal page scroll.
- Every failure (network, timeout, server, empty results, missing photo) has a clear next step.
