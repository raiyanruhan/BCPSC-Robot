const express = require('express');
const rateLimit = require('express-rate-limit');
const router = express.Router();
const { handleNews } = require('../controllers/news.controller');

// Tighter rate limit for news as it is a "heavy" tool and uses GNews/NewsData quota.
const newsLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 15, // 15 requests per minute
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many news requests. Please wait a minute.' }
});

// News tool entrypoint.
router.post('/', newsLimiter, handleNews);

module.exports = router;

