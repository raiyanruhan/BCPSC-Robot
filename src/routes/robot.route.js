const express = require('express');
const router = express.Router();
const { queueRobotCommand } = require('../controllers/robot.controller');

// Robot control tool entrypoint for the ElevenLabs agent.
router.post('/', queueRobotCommand);

module.exports = router;

