export default async function handler(req, res) {
  if (req.method !== 'GET') {
    return res.status(405).end()
  }

  const backend = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:5000'
  
  try {
    // Proxy the SSE stream to the backend
    const response = await fetch(`${backend}/api/analyze_images_stream`)
    
    if (!response.ok) {
      throw new Error(`Backend responded with ${response.status}`)
    }

    // Set SSE headers
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Cache-Control'
    })

    // Stream the response from backend to frontend
    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        
        const chunk = decoder.decode(value)
        res.write(chunk)
      }
    } finally {
      reader.releaseLock()
      res.end()
    }

  } catch (error) {
    console.error('SSE proxy error:', error)
    res.writeHead(500, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ error: 'Proxy error', details: error.message }))
  }
}
