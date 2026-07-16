# 5-minute demo script

Everything below works in **demo mode** (no API key). With a `GEMINI_API_KEY` configured
the same prompts run through live Gemini and the header badge switches to **Gemini live**.

Start both processes (see the README quickstart) and open http://localhost:3000.
The demo clock starts 45 sim-minutes before kickoff at 30× speed — the stadium state
visibly evolves while you demo.

## Minute 0-1 — orientation

- Note the header: sim clock, phase chip, **kickoff countdown**, provider badge.
- The **2D map** shows all zones colored by live congestion (legend below); gates glow
  amber/orange in the pre-match rush.
- The ticket card shows the persona: Section 324, Row 12, Seat 7, Gate C.

## Minute 1-2 — grounded navigation

Type or click the quick actions:

1. **"Take me to my seat"** — numbered, congestion-aware steps + an animated route line
   from Gate C up to Section 324. Note the *grounded via get_route* chip.
2. **"I need a step-free accessible route to my seat"** — the route now takes the
   **elevator**; the steps card shows a ♿ Step-free badge and no stairs.

## Minute 2-3 — multilingual + amenities ("rest rooms, stalls, etc.")

3. Type **"¿Dónde puedo comprar comida halal?"** — Spanish in, Spanish out, with Empire
   Halal Grill highlighted on the map with a walk-time estimate.
4. Click **Restrooms nearby** — nearest restrooms by congestion-weighted walk time.
5. Switch the language selector to **العربية** — the whole UI flips to RTL. Ask
   **"أين مقعدي؟"** — the route is still grounded through the same tools.

## Minute 3-4 — the 3D stadium

6. Switch the map to **3D view**. Drag to orbit, scroll to zoom.
   - **Crowd mode**: both tiers, concourses, gates, and the rail plaza are colored by
     live crowd density; the gold beacon shows where the fan currently is.
   - **Seats mode**: sections recolor by availability (green = available, amber = a few
     left, grey = sold out).
7. Click any green stand → details panel (crowd, seats left) → **"Take me here"** hands
   the request to the copilot, which routes there on the 2D map.
8. Ask **"Are there any seats available to buy?"** — the copilot lists the top open
   sections, grounded via `find_available_seats`.

## Minute 4-5 — the VR seat view + decision support

9. In 3D, press **🎥 Watch from my seat** — the camera flies to Section 324 and the
   simulated **live broadcast** plays on the pitch: players and ball in motion, LIVE
   scoreboard overhead. Around the 23rd minute Alvarez scores — watch for the ⚽ GOAL
   banner (67' Mbappe and 88' Messi are also scripted).
10. Ask **"When should I leave to catch the train?"** — pre-match you'll be told to relax;
    ask again after full time (≈5 real minutes in) and the advice changes to crowd-aware
    exit guidance with the rail plaza highlighted.

## Bonus checks for reviewers

- Kill the Python service — the web app shows a friendly offline banner and recovers when
  it returns.
- Send 11 rapid messages — the rate limiter answers 429 with `Retry-After`.
- Ask **"Tell me about quantum physics"** — the assistant politely stays in scope.
- `cd service && pytest` (52 tests) · `cd web && npm test` (17 tests).
