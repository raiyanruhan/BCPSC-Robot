const express = require('express');
const router = express.Router();
const { handleDictionary } = require('../controllers/dictionary.controller');

// Dictionary lookup tool entrypoint.
router.post('/', handleDictionary);

module.exports = router;

