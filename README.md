# robot-tools-server

A lightweight, stateless Express.js server that acts as a **tool provider** for an ElevenLabs AI voice agent. The agent calls this server via webhooks when it needs real-world data — weather, news, search results, dictionary definitions, etc. The server fetches from external APIs and returns clean JSON responses.

No AI. No brain. No database. No sessions. Just efficient API wrappers.

---

## 🏗 Architecture Overview

```mermaid
graph TD
    A[ElevenLabs Agent (Cloud)] -->|POST /tools/<toolname>| B(robot-tools-server)
    B -->|Fetch| C[OpenWeather API]
    B -->|Fetch| D[NewsData API]
    B -->|Fetch| E[Google CSE]
    B -->|Fetch| F[Wikipedia API]
    B -->|Fetch| G[AlAdhan API]
    B -->|Fetch| H[FreeDictionary API]
    B -->|Fetch| I[MathJS API]
    B -->|Fetch| J[Quran API]
```

The ElevenLabs agent handles all AI, STT (Speech-to-Text), and TTS (Text-to-Speech). When it needs live data, it calls this server. This server returns clean JSON, which the agent processes and speaks back to the user.

---

## ✨ Features (Tools)

- 🌦 **Weather** — Current weather data for any city.
- 📰 **News** — Latest news headlines by topic.
- 🔍 **Search** — Google web search results.
- 📖 **Wikipedia** — Summary of any topic from Wikipedia.
- 🧮 **Math** — Evaluation of complex math expressions.
- 📚 **Dictionary** — Word definitions and usage examples.
- 🕌 **Islamic** — Prayer times and Hijri date.
- 🕋 **Quran** — Fetch specific verses with translations (English/Bengali).
- 🤖 **Robot Control** — Store and retrieve commands for the robot hardware.
- 🕒 **Time** — Current time in Asia/Dhaka.

---

## 🛠 Tech Stack

| Package | Purpose |
|---|---|
| **Express** | HTTP server framework |
| **Axios** | External API calls |
| **Mathjs** | Math expression evaluation |
| **Dotenv** | Environment variable management |
| **CORS** | Cross-origin resource sharing |
| **Helmet** | Security headers |
| **Morgan** | Request logging |
| **Express-rate-limit** | API rate limiting |

---

## 📂 Project Structure

```
robot-tools-server/
├── server.js               ← Entry point
├── package.json
├── .env.example
├── README.md
└── src/
    ├── config/
    │   └── env.js           ← Loads + validates env vars
    ├── controllers/         ← Request handling + input validation
    │   ├── weather.controller.js
    │   ├── news.controller.js
    │   └── ...
    ├── middleware/
    │   ├── auth.js           ← x-robot-key validation
    │   └── errorHandler.js   ← Centralized error handling
    ├── routes/               ← Express routers (one per tool)
    │   ├── weather.route.js
    │   ├── news.route.js
    │   └── ...
    ├── services/             ← External API interaction logic
    │   ├── openweather.service.js
    │   ├── newsdata.service.js
    │   └── ...
    ├── utils/
    │   ├── formatter.js      ← Response formatting helpers
    │   └── cache.js          ← Simple in-memory Map cache
```

---

## 🚀 Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-repo/robot-tools-server.git
    cd robot-tools-server
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Configure environment variables:**
    Copy `.env.example` to `.env` and fill in your API keys.
    ```bash
    cp .env.example .env
    ```

---

## ⚙️ Configuration (.env)

| Variable | Description | Source |
|---|---|---|
| `PORT` | Server port (default: 3000) | - |
| `ROBOT_API_KEY` | Shared secret for auth (x-robot-key header) | Your custom key |
| `OPENWEATHER_API_KEY` | API key for weather data | [OpenWeather](https://openweathermap.org/api) |
| `NEWSDATA_API_KEY` | API key for news headlines | [NewsData](https://newsdata.io) |
| `GOOGLE_CSE_KEY` | API key for Google Search | [Google Cloud Console](https://console.cloud.google.com/) |
| `GOOGLE_CSE_ENGINE_ID` | Engine ID for Google Search | [Google Programmable Search](https://programmablesearchengine.google.com/) |

---

## 🏃 Running the Server

### Development
Start the server with `nodemon` for automatic reloading on changes:
```bash
npm run dev
```

### Production
Start the server normally:
```bash
npm start
```

---

## 🔌 API Documentation

### Authentication
All tool endpoints require the `x-robot-key` header for authentication.
```
Header: x-robot-key: <YOUR_ROBOT_API_KEY>
```
If missing or incorrect, the server returns `401 Unauthorized`.

### Health Check
`GET /` (No authentication required)
Returns server status, service name, and version.

### Tool Endpoints (POST /tools/...)
All tool endpoints are `POST`, return `application/json`, and require the `x-robot-key` header.

#### 🌦 Weather
`POST /tools/weather`
- **Body:** `{"city": "Bogura"}`
- **Response:** `{"location": "Bogura", "temperature": "31°C", "condition": "Cloudy", ...}`

#### 📰 News
`POST /tools/news`
- **Body:** `{"topic": "technology"}`
- **Response:** `{"headlines": [{"title": "...", "url": "..."}, ...]}`

#### 🔍 Search
`POST /tools/search`
- **Body:** `{"query": "latest AI news"}`
- **Response:** `{"results": [{"title": "...", "link": "...", "snippet": "..."}, ...]}`

#### 📖 Wikipedia
`POST /tools/wiki`
- **Body:** `{"topic": "Artificial Intelligence"}`
- **Response:** `{"title": "...", "summary": "...", "url": "..."}`

#### 🧮 Math
`POST /tools/math`
- **Body:** `{"expression": "2 + 2 * 5"}`
- **Response:** `{"result": 12}`

#### 📚 Dictionary
`POST /tools/dictionary`
- **Body:** `{"word": "robot"}`
- **Response:** `{"word": "robot", "definition": "...", "example": "..."}`

#### 🕌 Islamic
`POST /tools/islamic`
- **Body:** `{"type": "prayer_times", "city": "Dhaka"}` or `{"type": "hijri_date"}`
- **Response:** `{"prayer_times": {...}}` or `{"hijri_date": "..."}`

#### 🕋 Quran
`POST /tools/get_quran_verse`
- **Body:** `{"surah": 1, "ayah": 1, "language": "en"}`
- **Response:** `{"surah": 1, "ayah": 1, "text": "...", "translation": "..."}`

#### 🤖 Robot Control
- **Command Store:** `POST /tools/control-robot`
  - **Body:** `{"action": "move_forward"}`
- **Command Fetch:** `GET /robot/commands` (Unauthenticated, for Pi polling)
  - **Response:** `{"action": "move_forward"}` (one-shot, cleared after fetch)

#### 🕒 Time
`POST /tools/time`
- **Body:** `{}`
- **Response:** `{"time": "10:30 AM", "date": "Tuesday, March 17, 2026"}`

---

## ☁️ Deployment (Namecheap / cPanel)

This project is optimized for **Namecheap Stellar Plus shared hosting** using the Node.js App Manager.

1.  **Prepare files:** Create a ZIP of the project folder, excluding `node_modules`.
2.  **Upload:** Use cPanel **File Manager** to upload and extract the ZIP.
3.  **Install dependencies:** In cPanel **Terminal**, run `npm install` in the app root.
4.  **Create App:** Use **Node.js App Manager** in cPanel:
    - **Node.js version:** Latest available.
    - **Application root:** Path to your project folder.
    - **Application startup file:** `server.js`.
5.  **Environment Variables:** Add your `.env` keys through the Node.js App Manager UI.
6.  **Start:** Click **Run NPM Install** (if available) and then **Start App**.

---

## 🧪 Testing

You can test the endpoints using `curl`. Replace `YOUR_KEY` with your `ROBOT_API_KEY`.

**Weather Test:**
```bash
curl -X POST http://localhost:3000/tools/weather \
  -H "Content-Type: application/json" \
  -H "x-robot-key: YOUR_KEY" \
  -d '{"city": "Bogura"}'
```

**Search Test:**
```bash
curl -X POST http://localhost:3000/tools/search \
  -H "Content-Type: application/json" \
  -H "x-robot-key: YOUR_KEY" \
  -d '{"query": "latest AI news"}'
```

---

## 📄 License

MIT License. See `LICENSE` for details (if applicable).
