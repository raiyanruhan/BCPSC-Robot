const express = require('express');
const router = express.Router();
const { handleGetQuranVerse } = require('../controllers/quran.controller');

// Quran verse retrieval tool entrypoint.
router.post('/', handleGetQuranVerse);

module.exports = router;

