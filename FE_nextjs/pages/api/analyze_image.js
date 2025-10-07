import axios from 'axios'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:5001'

export default async function handler(req, res){
  if(req.method !== 'POST') return res.status(405).end()

  try{
    const response = await axios.post(`${BACKEND}/api/analyze_image`, req.body, { timeout: 30000 })
    return res.status(response.status).json(response.data)
  }catch(e){
    console.error('analyze_image proxy error', e?.message || e)
    return res.status(500).json({ error: 'Proxy error', details: e?.message || String(e) })
  }
}


