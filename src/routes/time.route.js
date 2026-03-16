const express = require('express');
const router = express.Router();
const { handleTime } = require('../controllers/time.controller');

// Time tool entrypoint.
router.post('/', handleTime);

module.exports = router;

