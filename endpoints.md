# robot-tools-server — Endpoints (Tools)

All tool endpoints are:
- `POST` method
- Under `/tools/` prefix
- Protected by `x-robot-key` header
- Return `Content-Type: application/json`

---

## Authentication (Required on ALL endpoints)

```
Header: x-robot-key: <your ROBOT_API_KEY>
```

Missing or incorrect → `401 Unauthorized`
```json
{ "error": "Unauthorized" }
```

---

## Health Check

### `GET /`
No auth required.

**Response:**
```json
{
  "status": "ok",
  "service": "robot-tools-server",
  "version": "1.0"
}
```

---

## Tool 1 — Weather

### `POST /tools/weather`

Fetches current weather for a city.

**External API:** OpenWeather Current Weather API  
**Caching:** Yes — 10 minutes, keyed by city (lowercased)

**Request body:**
```json
{
  "city": "Bogura"
}
```

**Required fields:** `city`

**Success response `200`:**
```json
{
  "location": "Bogura",
  "temperature": "31°C",
  "feels_like": "34°C",
  "condition": "Cloudy",
  "humidity": "70%",
  "wind_speed": "5 km/h"
}
```

**Errors:**
- `400` — missing `city`
- `502` — OpenWeather API failure

---

## Tool 2 — News

### `POST /tools/news`

Fetches latest news headlines by topic.

**External API:** NewsData.io  
**Caching:** Yes — 10 minutes, keyed by topic (lowercased)

**Request body:**
```json
{
  "topic": "world"
}
```

**Required fields:** `topic`  
**Suggested topics:** `world`, `technology`, `sports`, `health`, `bangladesh`

**Success response `200`:**
```json
{
  "headlines": [
    {
      "title": "Headline text here",
      "source": "BBC News",
      "summary": "Brief summary of the article",
      "url": "https://..."
    }
  ]
}
```

Returns top 5 headlines maximum.

**Errors:**
- `400` — missing `topic`
- `502` — NewsData API failure

---

## Tool 3 — Google Search

### `POST /tools/search`

Performs a Google web search and returns top results.

**External API:** Google Custom Search JSON API  
**Caching:** None

**Request body:**
```json
{
  "query": "capital of Japan"
}
```

**Required fields:** `query`

**Success response `200`:**
```json
{
  "results": [
    {
      "title": "Tokyo - Wikipedia",
      "snippet": "Tokyo is the capital and most populous city of Japan...",
      "link": "https://en.wikipedia.org/wiki/Tokyo"
    }
  ]
}
```

Returns top 3 results maximum.

**Errors:**
- `400` — missing `query`
- `502` — Google CSE API failure

---

## Tool 4 — Wikipedia

### `POST /tools/wiki`

Fetches a Wikipedia summary for a topic.

**External API:** Wikipedia REST API (`/page/summary/{topic}`)  
**Caching:** None

**Request body:**
```json
{
  "topic": "photosynthesis"
}
```

**Required fields:** `topic`

**Success response `200`:**
```json
{
  "title": "Photosynthesis",
  "summary": "Photosynthesis is a process used by plants...",
  "url": "https://en.wikipedia.org/wiki/Photosynthesis"
}
```

**Errors:**
- `400` — missing `topic`
- `404` — Wikipedia page not found
- `502` — Wikipedia API failure

---

## Tool 5 — Math

### `POST /tools/math`

Evaluates a mathematical expression.

**Library:** mathjs (`math.evaluate()`)  
**External API:** None — runs locally  
**Caching:** None

**Request body:**
```json
{
  "expression": "12 * 5 + 3"
}
```

**Required fields:** `expression`

**Success response `200`:**
```json
{
  "expression": "12 * 5 + 3",
  "result": "63"
}
```

**Supported expressions:** arithmetic, algebra, trigonometry, sqrt, fractions, unit conversions (anything mathjs supports)

**Errors:**
- `400` — missing `expression`
- `400` — invalid/unparseable expression

---

## Tool 6 — Dictionary

### `POST /tools/dictionary`

Looks up the definition of an English word.

**External API:** Free Dictionary API (`https://api.dictionaryapi.dev/api/v2/entries/en/{word}`)  
**Caching:** None

**Request body:**
```json
{
  "word": "ephemeral"
}
```

**Required fields:** `word`

**Success response `200`:**
```json
{
  "word": "ephemeral",
  "meaning": "Lasting for a very short time",
  "example": "Fashions are ephemeral: new ones regularly drive out the old."
}
```

If no example exists in the API response, `example` will be `null`.

**Errors:**
- `400` — missing `word`
- `404` — word not found
- `502` — Dictionary API failure

---

## Tool 7 — Islamic Information

### `POST /tools/islamic`

Returns Islamic prayer times or the current Hijri date.

**External API:** AlAdhan API  
**Caching:** None

**Request body:**
```json
{
  "type": "prayer_times",
  "city": "Bogura"
}
```

**Required fields:** `type`  
**Required for `prayer_times`:** `city`

### Type: `prayer_times`

Returns today's prayer times for the given city.

```json
{
  "type": "prayer_times",
  "city": "Bogura",
  "country": "Bangladesh",
  "date": "16 Mar 2026",
  "fajr": "04:55",
  "dhuhr": "12:15",
  "asr": "16:10",
  "maghrib": "18:20",
  "isha": "19:40"
}
```

**AlAdhan endpoint used:** `GET /v1/timingsByCity?city=Bogura&country=Bangladesh&method=1`

### Type: `hijri_date`

Returns today's Hijri (Islamic calendar) date.

```json
{
  "type": "hijri_date",
  "hijri_date": "16 Sha'ban 1447",
  "gregorian_date": "16 Mar 2026"
}
```

**AlAdhan endpoint used:** `GET /v1/gToH?date=DD-MM-YYYY`

**Errors:**
- `400` — missing `type`
- `400` — unknown `type` value
- `400` — missing `city` when type is `prayer_times`
- `502` — AlAdhan API failure

---

## Tool 8 — Translate

### `POST /tools/translate`

Translates text between languages.

**External API:** LibreTranslate (`https://libretranslate.com/translate`)  
**Caching:** None

**Request body:**
```json
{
  "text": "Good morning",
  "from": "en",
  "to": "bn"
}
```

**Required fields:** `text`, `from`, `to`

**Common language codes:**
| Language | Code |
|---|---|
| English | `en` |
| Bangla | `bn` |
| Arabic | `ar` |
| Hindi | `hi` |
| French | `fr` |

**Success response `200`:**
```json
{
  "translated_text": "শুভ সকাল"
}
```

**Errors:**
- `400` — missing `text`, `from`, or `to`
- `502` — LibreTranslate API failure

---

## Tool 9 — Time

### `POST /tools/time`

Returns the current server time in the Bangladesh timezone.

**External API:** None — server system time  
**Caching:** None

**Request body:** None required (empty body or `{}`)

**Success response `200`:**
```json
{
  "time": "10:35 AM",
  "date": "Monday, 16 March 2026",
  "day": "Monday",
  "timezone": "Asia/Dhaka"
}
```

---

## Error Response Format (All Endpoints)

All errors follow this consistent shape:

```json
{
  "error": "Human readable message here"
}
```

| Status | Meaning |
|---|---|
| `400` | Missing or invalid input |
| `401` | Wrong or missing `x-robot-key` |
| `404` | Resource not found |
| `429` | Rate limit exceeded (100 req/min) |
| `502` | External API call failed |
| `500` | Unexpected server error |