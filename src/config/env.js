// Centralized environment configuration.
// This is the only place where dotenv is loaded so the rest of the app
// can safely import already-parsed environment values.

const path = require('path');
const dotenv = require('dotenv');

// Load .env from the project root so it works both locally and on shared hosting.
dotenv.config({
  path: path.resolve(__dirname, '..', '..', '.env')
});

// Read environment variables once so consumers do not touch process.env directly.
const PORT = process.env.PORT || 3000;
const ROBOT_API_KEY = process.env.ROBOT_API_KEY || 'changeme';
const OPENWEATHER_API_KEY = process.env.OPENWEATHER_API_KEY || '';
const NEWSDATA_API_KEY = process.env.NEWSDATA_API_KEY || '';
const GNEWS_API_KEY = process.env.GNEWS_API_KEY || '';
const GOOGLE_CSE_KEY = process.env.GOOGLE_CSE_KEY || '';
const GOOGLE_CSE_ENGINE_ID = process.env.GOOGLE_CSE_ENGINE_ID || '';

// Warn once at startup if the robot key is not configured.
// This helps catch misconfiguration without blocking local development.
if (!process.env.ROBOT_API_KEY || ROBOT_API_KEY === 'changeme') {
  console.warn(
    '[robot-tools-server] ROBOT_API_KEY is missing or still set to "changeme". ' +
      'Set a strong secret in your .env before exposing this server publicly.'
  );
}

module.exports = {
  PORT,
  ROBOT_API_KEY,
  OPENWEATHER_API_KEY,
  NEWSDATA_API_KEY,
  GNEWS_API_KEY,
  GOOGLE_CSE_KEY,
  GOOGLE_CSE_ENGINE_ID
};

