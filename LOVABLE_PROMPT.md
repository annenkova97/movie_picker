# Промпт для Lovable

> Скопируй всё ниже и вставь первым сообщением в новом Lovable-проекте.
> Перед отправкой замени `https://YOUR-API-URL` на реальный URL твоего Railway-деплоя.

---

## Project

Build a modern, polished web frontend for **Movie Picker** — a personal movie watchlist with AI-powered recommendations and Instagram Reel import.

The backend is **already built** (FastAPI). Do NOT reimplement business logic. The frontend only calls existing REST endpoints.

**API base URL:** `https://YOUR-API-URL`
**Swagger docs:** `https://YOUR-API-URL/docs`

## Tech stack

- React + Vite + TypeScript
- Tailwind CSS + shadcn/ui
- TanStack Query (React Query) for API calls
- React Router for navigation
- Lucide icons

## API endpoints

All endpoints are under the base URL above. CORS is already open.

### Movies (watchlist CRUD)
- `GET /api/movies` — list user's saved movies. Query params: `watched` (bool), `sort` (e.g. `added_desc`)
- `POST /api/movies` — add movie manually `{ title, year?, notes?, rating? }`
- `GET /api/movies/{id}` — get one
- `PATCH /api/movies/{id}` — update (mark watched, edit rating/notes)
- `DELETE /api/movies/{id}` — remove
- `POST /api/movies/by-imdb/{imdb_id}` — add a movie by IMDb ID (auto-fills from OMDB)

### Search
- `GET /api/search?query=...` — search OMDB for a title, returns candidates with posters

### AI recommendations
- `POST /api/recommend` — body `{ mood?, genre?, limit? }` — returns AI-generated picks based on watchlist

### Instagram Reel import
- `POST /api/instagram/import` — body `{ url }` — imports a reel, extracts mentioned movies, adds them
- `POST /api/instagram/search` — body `{ url }` — same but returns candidates without saving

### Health
- `GET /api/health` — `{ status: "ok" }`

The full OpenAPI spec is at `https://YOUR-API-URL/openapi.json` — fetch it to generate a typed client.

## Pages to build (in this order — one per prompt iteration)

1. **Landing / Home** — hero, value prop, CTA to open the app. Clean, minimal, cinematic feel (dark mode default, movie-poster vibe).
2. **Watchlist** — grid/list of saved movies with posters, year, rating. Filters: watched/unwatched, sort. Click → detail drawer. Add button opens search modal.
3. **Search modal** — input → calls `/api/search`, shows poster cards, click to add to watchlist via `POST /api/movies/by-imdb/{imdb_id}`.
4. **Movie detail drawer** — poster, metadata, personal notes, rating slider, "mark watched" toggle, delete.
5. **Recommend** — form (mood, genre) → `POST /api/recommend` → animated card reveal of suggestions.
6. **Instagram import** — paste reel URL → `POST /api/instagram/search` → review extracted movies → confirm to add.

## Design direction

- Dark, cinematic, Letterboxd × Mubi × Apple TV+ vibe
- Generous whitespace, large posters, smooth transitions
- Typography: Inter or Geist for UI, a display serif for hero
- Subtle gradients, no loud colors — let posters be the color
- Loading states with skeletons, not spinners
- Mobile-first, fully responsive

## Rules

- **No mock data.** Every list/detail must call the real API.
- **No auth** for now — single-user app, all endpoints are open.
- Use React Query with proper cache keys per endpoint; invalidate on mutations.
- Handle API errors gracefully with toast notifications (shadcn `sonner`).
- Keep components small and composable.

Start with page 1 (Landing). When I approve, move to page 2.
