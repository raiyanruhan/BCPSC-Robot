// Controller for robot control commands shared between the ElevenLabs agent
// and the Raspberry Pi. Commands are stored in-memory so the Pi can poll
// cheaply without adding any extra infrastructure.

// In-memory store for the latest pending command.
let latestCommand = null;
let pendingEnrollRes = null;

const VALID_ACTIONS = new Set([
  'look_left',
  'look_right',
  'look_front',
  'handshake',
  'hand_open',
  'hand_fist',
  'hand_peace',
  'hand_ok',
  'hand_point',
  'hand_CLAW',
  'hand_1',
  'hand_2',
  'hand_3',
  'hand_4',
  'hand_5',
  'jaw_open',
  'jaw_close',
  'jaw_chew',
  'jaw_stop'
]);

async function queueRobotCommand(req, res, next) {
  try {
    const body = req.body || {};
    const action = body.action;

    if (!action || typeof action !== 'string' || !VALID_ACTIONS.has(action)) {
      return res.status(400).json({
        error:
          'Invalid or missing action. Valid actions: wave, nod, shake_head, look_left, look_right, look_up, look_down, celebrate, idle'
      });
    }

    const previous = latestCommand ? latestCommand.action : null;

    // Store the latest command so the Pi can pick it up on the next poll.
    latestCommand = {
      action,
      created_at: Date.now()
    };

    // Keep the response intentionally small: the agent only needs to know it
    // was queued, and whether something got overwritten.
    const responseBody = { success: true, queued: true };
    if (previous && previous !== action) {
      responseBody.warning = `previous command ${previous} was overwritten`;
    }

    res.json(responseBody);
  } catch (err) {
    next(err);
  }
}

async function getLatestRobotCommand(req, res, next) {
  try {
    if (!latestCommand) {
      // Returning a structured "no command" response keeps the Pi logic simple.
      return res.json({
        success: false,
        data: null
      });
    }

    const commandToSend = latestCommand;
    // Clear the stored command so each one is delivered exactly once.
    latestCommand = null;

    res.json({
      success: true,
      // Return the whole command object so special actions (like enroll_face)
      // can carry extra fields to the Pi. Regular actions only include action.
      data: commandToSend
    });
  } catch (err) {
    next(err);
  }
}

function overwritePendingCommand(command) {
  const previous = latestCommand ? latestCommand.action : null;
  latestCommand = { ...command, created_at: Date.now() };
  return previous;
}

function setPendingEnrollRes(value) {
  pendingEnrollRes = value;
}

function getPendingEnrollRes() {
  return pendingEnrollRes;
}

module.exports = {
  queueRobotCommand,
  getLatestRobotCommand,
  overwritePendingCommand,
  setPendingEnrollRes,
  getPendingEnrollRes
};

