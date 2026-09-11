// Compatibility proxy for older clients. agent.html now calls FastAPI directly.
export default async function handler(req, res) {
  const allowedOrigins = (process.env.FRONTEND_ORIGINS ||
    'https://getrootlink.com,https://www.getrootlink.com')
    .split(',')
    .map(origin => origin.trim());
  const origin = req.headers.origin;
  if (origin && allowedOrigins.includes(origin)) {
    res.setHeader('Access-Control-Allow-Origin', origin);
    res.setHeader('Vary', 'Origin');
  }
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const userId = req.body.user_id || req.body.session_id || 'default_session';
  const message = req.body.message || req.body.text;
  if (!message) return res.status(400).json({ error: 'Missing message' });

  const backendUrl = (process.env.BACKEND_API_URL ||
    'https://api.getrootlink.com').replace(/\/$/, '');

  try {
    const response = await fetch(backendUrl + '/api/chat/sse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        message,
        lang: req.body.lang || 'zh'
      })
    });

    if (!response.ok) {
      return res.status(response.status).send(await response.text());
    }

    res.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
    res.setHeader('Cache-Control', 'no-cache, no-transform');
    res.setHeader('Connection', 'keep-alive');

    const reader = response.body.getReader();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      res.write(Buffer.from(value));
    }
    return res.end();
  } catch (error) {
    return res.status(502).json({ error: error.message });
  }
}
