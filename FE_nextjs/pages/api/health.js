import axios from 'axios'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:5000'

export default async function handler(req, res){
  try{
    const response = await axios.get(`${BACKEND}/api/health`, { timeout: 3000 })
    return res.status(response.status).json(response.data)
  }catch(e){
    return res.status(200).json({ status: 'offline' })
  }
}
