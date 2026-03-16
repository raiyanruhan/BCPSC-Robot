# robot-tools-server — Project Details

## What Is This?

A lightweight, stateless Express.js HTTP server that acts as a **tool provider** for an ElevenLabs AI voice agent. The agent calls this server via webhooks when it needs real-world data — weather, news, search results, etc. The server fetches from external APIs and returns clean JSON. That's it.

No AI. No brain. No database. No sessions. Just API wrappers.

---

## Where It Lives

**Namecheap Stellar Plus shared hosting** — Node.js app managed via cPanel's Node.js App Manager (Passenger).

### Hosting constraints this project must respect:
- CommonJS only (`require`, not `import`)
- No Docker
- No Redis
- No external database
- `server.js` is the entry point
- Runs via `npm start`

---

## How It Fits Into the Larger System

```
ElevenLabs Agent (Cloud)
        |
        | POST /tools/<toolname>
        | Header: x-robot-key
        v
robot-tools-server  ←── THIS PROJECT
        |
        | calls external APIs
        v
OpenWeather / NewsData / Google CSE /
Wikipedia / AlAdhan / LibreTranslate /
FreeDictionary / MathJS
```

The ElevenLabs agent handles all AI, STT, and TTS. When it needs live data (weather, news, search), it calls this server. The server returns JSON. The agent reads that JSON and speaks the answer.

The Raspberry Pi (robot hardware) is a separate layer entirely — not this project's concern.

---

## Tech Stack

| Package | Purpose |
|---|---|
| express | HTTP server |
| axios | External API calls |
| mathjs | Math expression evaluation |
| dotenv | Environment variable loading |
| cors | Cross-origin headers |
| helmet | Security headers |
| morgan | Request logging |
| express-rate-limit | Rate limiting |

No TypeScript. No ORM. No framework beyond Express.

---

## Project Structure

```
robot-tools-server/
├── server.js               ← Entry point
├── package.json
├── .env.example
├── README.md
└── src/
    ├── config/
    │   └── env.js           ← Loads + validates env vars
    ├── middleware/
    │   ├── auth.js           ← x-robot-key validation
    │   └── errorHandler.js   ← Centralized error responses
    ├── utils/
    │   ├── formatter.js      ← Response formatting helpers
    │   └── cache.js          ← Simple in-memory Map cache
    ├── routes/               ← Express routers (one per tool)
    │   ├── weather.route.js
    │   ├── news.route.js
    │   ├── search.route.js
    │   ├── wiki.route.js
    │   ├── math.route.js
    │   ├── dictionary.route.js
    │   ├── islamic.route.js
    │   ├── translate.route.js
    │   └── time.route.js
    ├── controllers/          ← Request handling + input validation
    │   ├── weather.controller.js
    │   ├── news.controller.js
    │   ├── search.controller.js
    │   ├── wiki.controller.js
    │   ├── math.controller.js
    │   ├── dictionary.controller.js
    │   ├── islamic.controller.js
    │   ├── translate.controller.js
    │   └── time.controller.js
    └── services/             ← External API call logic
        ├── openweather.service.js
        ├── newsdata.service.js
        ├── googlecse.service.js
        ├── wiki.service.js
        ├── dictionary.service.js
        ├── islamic.service.js
        └── translate.service.js
```

**The flow for every request:**

```
Incoming POST
    → auth middleware (check x-robot-key)
    → route (match URL)
    → controller (validate input, call service)
    → service (call external API, return data)
    → controller (format + send JSON response)
    → errorHandler (if anything threw)
```

---

## Security

### API Key Auth
Every request to `/tools/*` must include:
```
x-robot-key: <ROBOT_API_KEY from .env>
```
Missing or wrong key → `401 Unauthorized`. No exceptions.

### Rate Limiting
100 requests per minute globally via `express-rate-limit`.

### Helmet
Sets secure HTTP headers automatically.

### No secrets in code
All API keys live in `.env` only. Never hardcoded.

---

## Caching

Simple in-memory `Map` cache with TTL (time-to-live).

Only applied to:
- **Weather** — 10 minute cache keyed by city (lowercased)
- **News** — 10 minute cache keyed by topic (lowercased)

All other tools are called fresh every time.

---

## Input Validation

Every controller validates its required fields before calling any service.

If a required field is missing → `400 Bad Request` with a clear message.

Example:
```json
{ "error": "Missing required field: city" }
```

---

## Error Handling

All errors flow to the centralized `errorHandler.js` middleware.

- External API failures → `502 Bad Gateway`
- Missing input → `400 Bad Request`
- Bad auth → `401 Unauthorized`
- Unknown routes → `404 Not Found`
- Everything else → `500 Internal Server Error`

Stack traces are never exposed in production.

---

## Environment Variables

```
PORT=3000
ROBOT_API_KEY=changeme
OPENWEATHER_API_KEY=
NEWSDATA_API_KEY=
GOOGLE_CSE_KEY=
GOOGLE_CSE_ENGINE_ID=
LIBRETRANSLATE_URL=https://libretranslate.com
```

---

## NPM Scripts

```json
"start": "node server.js"
"dev":   "nodemon server.js"
```

---

## Deployment on Namecheap Stellar Plus

1. Zip project (excluding `node_modules`) and upload via cPanel File Manager, or push via Git
2. Extract to desired directory (e.g. `~/robot-tools-server/`)
3. Open cPanel Terminal → `cd ~/robot-tools-server && npm install`
4. Go to **Node.js App Manager** in cPanel
5. Create new app:
   - Node.js version: latest available
   - Application root: `robot-tools-server/`
   - Application startup file: `server.js`
6. Add environment variables in the App Manager UI
7. Click **Run NPM Install** then **Start App**

---

## What This Server Is NOT

- Not an AI
- Not a conversation manager
- Not a knowledge base
- Not stateful
- Not responsible for voice, STT, or TTS
- Not connected to the Raspberry Pi directly