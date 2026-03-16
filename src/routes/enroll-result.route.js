const express = require('express');
const router = express.Router();
const { handleEnrollResult } = require('../controllers/enrollFace.controller');

// Pi posts enrollment success/failure here to resolve the pending long-poll.
router.post('/', handleEnrollResult);

module.exports = router;

