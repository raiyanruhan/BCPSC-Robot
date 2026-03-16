const express = require('express');
const router = express.Router();
const { handleWiki } = require('../controllers/wiki.controller');

// Wikipedia summary tool entrypoint.
router.post('/', handleWiki);

module.exports = router;

