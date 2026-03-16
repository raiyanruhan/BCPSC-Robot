const express = require('express');
const router = express.Router();
const { handleFaceUpdate } = require('../controllers/face.controller');

// Pi pushes face state updates here.
router.post('/', handleFaceUpdate);

module.exports = router;

