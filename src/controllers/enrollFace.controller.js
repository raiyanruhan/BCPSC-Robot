// Face enrollment controllers (long-poll pattern).
// ElevenLabs calls POST /tools/enroll-face and the server holds the connection
// open until the Raspberry Pi confirms via POST /pi/enroll-result, or a timeout.
//
// This avoids needing websockets or a database, and works with the Pi's
// existing polling model (GET /robot/commands).

const {
  overwritePendingCommand,
  setPendingEnrollRes,
  getPendingEnrollRes
} = require('./robot.controller');

async function handleEnrollFace(req, res, next) {
  try {
    const body = req.body || {};
    const personName = body.person_name;
    const role = body.role;
    const details = body.Details;
    const language = body.language === 'bn' ? 'bn' : 'en';

    if (!personName || typeof personName !== 'string') {
      return res.status(400).json({ error: 'Missing required field: person_name' });
    }

    if (!role || typeof role !== 'string') {
      return res.status(400).json({ error: 'Missing required field: role' });
    }

    if (!details || typeof details !== 'string') {
      return res.status(400).json({ error: 'Missing required field: Details' });
    }

    // Only allow one enrollment request at a time. If another is already
    // pending, we overwrite it to match the server's single-slot design.
    const existing = getPendingEnrollRes();
    if (existing && existing.timeoutId) {
      clearTimeout(existing.timeoutId);
      try {
        existing.res.json({
          success: false,
          data: {
            enrolled: false,
            person: existing.personName,
            summary:
              'Face enrollment was cancelled because a new enrollment request started.'
          }
        });
      } catch (e) {
        // Ignore broken connections; the new request takes precedence.
      }
    }

    // Push the enrollment command through the same robot command slot the Pi polls.
    overwritePendingCommand({
      action: 'enroll_face',
      person_name: personName,
      role,
      Details: details,
      language
    });

    const timeoutId = setTimeout(() => {
      const pending = getPendingEnrollRes();
      if (!pending || pending.res !== res) {
        return;
      }

      try {
        res.json({
          success: false,
          data: {
            enrolled: false,
            person: personName,
            summary:
              'Face enrollment timed out. The camera did not respond. Please try again.'
          }
        });
      } finally {
        setPendingEnrollRes(null);
      }
    }, 15 * 1000);

    // Store the response so /pi/enroll-result can resolve it later.
    setPendingEnrollRes({ res, personName, role, details, language, timeoutId });
    // Intentionally do not respond now (long-poll).
  } catch (err) {
    next(err);
  }
}

async function handleEnrollResult(req, res, next) {
  try {
    const body = req.body || {};
    const ok = Boolean(body.success);
    const person = body.person || null;
    const errMsg = typeof body.error === 'string' ? body.error : null;

    const pending = getPendingEnrollRes();
    if (pending && pending.timeoutId) {
      clearTimeout(pending.timeoutId);
    }

    if (pending) {
      try {
        if (ok) {
          pending.res.json({
            success: true,
            data: {
              enrolled: true,
              person: person || pending.personName,
              role: pending.role,
              Details: pending.details,
              language: pending.language,
              summary: `${person || pending.personName}'s face has been saved successfully as a ${
                pending.role
              }. I will recognise them from now on.`
            }
          });
        } else {
          const reason = errMsg || 'Face enrollment failed';
          pending.res.json({
            success: false,
            data: {
              enrolled: false,
              person: person || pending.personName,
              role: pending.role,
              Details: pending.details,
              language: pending.language,
              error: reason,
              summary: `I could not save ${person || pending.personName}'s face. ${reason}. Please try again.`
            }
          });
        }
      } catch (e) {
        // Ignore if ElevenLabs disconnected; still acknowledge Pi and clear state.
      } finally {
        setPendingEnrollRes(null);
      }
    }

    // Always acknowledge Pi regardless of whether a request was pending.
    res.json({ success: true });
  } catch (err) {
    next(err);
  }
}

module.exports = {
  handleEnrollFace,
  handleEnrollResult
};

