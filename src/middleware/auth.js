// Middleware to validate the x-robot-key header against the configured ROBOT_API_KEY.
// This ensures only the ElevenLabs agent (or authorized hardware) can call the tools.

const { ROBOT_API_KEY } = require('../config/env');

// ElevenLabs outgoing webhook IP ranges for allowlisting.
// Reference: https://elevenlabs.io/docs/api-reference/webhooks
const ELEVENLABS_IPS = [
  '3.218.140.222',
  '34.201.37.140',
  '34.238.118.252',
  '35.168.163.42',
  '52.203.22.42',
  '54.144.156.40'
];

function auth(req, res, next) {
  // IP Allowlisting check.
  // req.ip can be affected by proxies (e.g. cPanel/Namecheap), 
  // so we check x-forwarded-for if it exists.
  const clientIp = (req.headers['x-forwarded-for'] || req.ip || '').split(',')[0].trim();
  
  // Only apply IP check if not in local dev (simple check)
  const isLocal = clientIp === '::1' || clientIp === '127.0.0.1' || clientIp.startsWith('192.168.');
  
  if (!isLocal && !ELEVENLABS_IPS.includes(clientIp)) {
    console.warn(`[auth] Blocked request from non-ElevenLabs IP: ${clientIp}`);
    // Optional: You could return 403 here, but for now we'll just log and continue
    // as some users might be testing from other IPs.
  }

  const providedKey = req.headers['x-robot-key'];

  if (!providedKey || providedKey !== ROBOT_API_KEY) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  next();
}

module.exports = auth;

