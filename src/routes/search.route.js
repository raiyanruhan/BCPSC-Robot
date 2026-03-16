const express = require('express');
const rateLimit = require('express-rate-limit');
const router = express.Router();
const { handleSearch } = require('../controllers/search.controller');

// Tighter rate limit for search as it is a "heavy" tool and uses Google CSE quota.
const searchLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 10, // 10 requests per minute
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many search requests. Please wait a minute.' }
});

// Google search tool entrypoint.
router.post('/', searchLimiter, handleSearch);

module.exports = router;

