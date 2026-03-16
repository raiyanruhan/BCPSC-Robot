const express = require('express');
const router = express.Router();
const { handleIslamic } = require('../controllers/islamic.controller');

// Islamic information tool entrypoint.
router.post('/', handleIslamic);

module.exports = router;

