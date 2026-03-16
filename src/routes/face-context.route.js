const express = require('express');
const router = express.Router();
const { handleGetFaceContext } = require('../controllers/face.controller');

// ElevenLabs tool to read current face context.
router.post('/', handleGetFaceContext);

module.exports = router;

