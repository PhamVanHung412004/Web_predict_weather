import axios from 'axios'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:5000'

export default async function handler(req, res){
  const { filename } = req.query

  if(!filename) return res.status(400).json({ error: 'Filename missing' })

  try{
    const response = await axios.get(`${BACKEND}/results/${filename}`, { responseType: 'arraybuffer', timeout: 10000 })
    const contentType = response.headers['content-type'] || 'image/png'
    res.setHeader('Content-Type', contentType)
    res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
    return res.status(200).send(Buffer.from(response.data, 'binary'))
  }catch(e){
    console.error(e.message || e)
    return res.status(500).json({ error: 'Proxy error', details: e.message })
  }
}