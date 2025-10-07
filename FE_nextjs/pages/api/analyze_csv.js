import axios from 'axios'

export const config = {
  api: {
    bodyParser: false,
  }
}

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:5001'

function getRawBody(req){
  return new Promise((resolve, reject) =>{
    const chunks = []
    req.on('data', (chunk) => chunks.push(chunk))
    req.on('end', () => resolve(Buffer.concat(chunks)))
    req.on('error', (err) => reject(err))
  })
}

export default async function handler(req, res){
  if(req.method !== 'POST') return res.status(405).end()

  try{
    const raw = await getRawBody(req)
    const contentType = req.headers['content-type'] || 'multipart/form-data'

    const response = await axios.post(`${BACKEND}/api/analyze_csv`, raw, {
      headers: {
        'Content-Type': contentType
      },
      maxBodyLength: Infinity,
      timeout: 120000
    })

    return res.status(response.status).json(response.data)
  }catch(e){
    console.error('analyze_csv proxy error', e?.message || e)
    return res.status(500).json({ error: 'Proxy error', details: e?.message || String(e) })
  }
}

