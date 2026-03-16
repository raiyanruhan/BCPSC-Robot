// Main entry point for robot-tools-server.
// Sets up security middleware, rate limiting, authentication for tool routes,
// and wires all tool endpoints under the /tools prefix.

require('./src/config/env');

const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');

const { PORT } = require('./src/config/env');
const auth = require('./src/middleware/auth');
const errorHandler = require('./src/middleware/errorHandler');

// Routers for each tool.
const weatherRouter = require('./src/routes/weather.route');
const newsRouter = require('./src/routes/news.route');
const searchRouter = require('./src/routes/search.route');
const wikiRouter = require('./src/routes/wiki.route');
const mathRouter = require('./src/routes/math.route');
const dictionaryRouter = require('./src/routes/dictionary.route');
const islamicRouter = require('./src/routes/islamic.route');
const quranRouter = require('./src/routes/quran.route');
const robotRouter = require('./src/routes/robot.route');
const timeRouter = require('./src/routes/time.route');
const { getLatestRobotCommand } = require('./src/controllers/robot.controller');
const faceUpdateRouter = require('./src/routes/face-update.route');
const faceContextRouter = require('./src/routes/face-context.route');
const enrollFaceRouter = require('./src/routes/enroll-face.route');
const enrollResultRouter = require('./src/routes/enroll-result.route');

const app = express();

// Core security and parsing middleware applied globally.
app.use(helmet());
app.use(cors());
app.use(morgan('dev'));
app.use(express.json());

// Global rate limiter to protect shared hosting and upstream APIs.
const limiter = rateLimit({
  windowMs: 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many requests' }
});
app.use(limiter);

// Public health check, intentionally left unauthenticated so external monitors
// can verify availability without knowing the robot API key.
app.get('/', (req, res) => {
  res.json({
    status: 'ok',
    service: 'robot-tools-server',
    version: '1.0'
  });
});

// Apply authentication to all tool routes only.
app.use('/tools', auth);

// Mount individual tool routers.
app.use('/tools/weather', weatherRouter);
app.use('/tools/news', newsRouter);
app.use('/tools/search', searchRouter);
app.use('/tools/wiki', wikiRouter);
app.use('/tools/math', mathRouter);
app.use('/tools/dictionary', dictionaryRouter);
app.use('/tools/islamic', islamicRouter);
app.use('/tools/get_quran_verse', quranRouter);
app.use('/tools/control-robot', robotRouter);
app.use('/tools/get-face-context', faceContextRouter);
app.use('/tools/enroll-face', enrollFaceRouter);
app.use('/tools/time', timeRouter);

// Pi endpoints are authenticated too (same x-robot-key).
app.use('/pi', auth);
app.use('/pi/face-update', faceUpdateRouter);
app.use('/pi/enroll-result', enrollResultRouter);

// Robot polling endpoint used by the Raspberry Pi.
// This is deliberately left unauthenticated to simplify on-device code;
// security is expected to be handled at the network level (e.g. LAN-only).
app.get('/robot/commands', getLatestRobotCommand);

// Catch-all 404 for unknown routes to keep error responses predictable.
app.use((req, res) => {
  res.status(404).json({ error: 'Not Found' });
});

// Central error handler must be last.
app.use(errorHandler);

app.listen(PORT, () => {
  console.log(`robot-tools-server listening on port ${PORT}`);
});

