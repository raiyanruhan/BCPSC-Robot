const express = require('express');
const router = express.Router();
const { handleEnrollFace } = require('../controllers/enrollFace.controller');

// ElevenLabs tool endpoint (long-poll) to enroll a new face.
router.post('/', handleEnrollFace);

module.exports = router;

