// Compatibility proxy. New clients call FastAPI directly.
export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).end();
  let backendUrl = process.env.BACKEND_API_URL || 'https://api.getrootlink.com';
  if (backendUrl.endsWith('/')) backendUrl = backendUrl.slice(0, -1);
  const response = await fetch(backendUrl + '/api/archive/save', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': req.headers.authorization || ''
    },
    body: JSON.stringify({ data: req.body.data || {} })
  });
  return res.status(response.status).send(await response.text());
}
