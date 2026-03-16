const express = require('express');
const router = express.Router();
const { handleMath } = require('../controllers/math.controller');

// Math evaluation tool entrypoint.
router.post('/', handleMath);

module.exports = router;

