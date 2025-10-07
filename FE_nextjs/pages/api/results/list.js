import axios from 'axios'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:5000'

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).end()
  }

  try {
    const response = await axios.get(`${BACKEND}/api/results/list`, {
      timeout: 10000
    })

    return res.status(response.status).json(response.data)
  } catch (error) {
    console.error('Results list proxy error:', error?.message || error)
    return res.status(500).json({ 
      error: 'Proxy error', 
      details: error?.message || String(error) 
    })
  }
}