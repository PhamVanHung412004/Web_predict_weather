import axios from 'axios'
import { useEffect, useState, useRef } from 'react'
import { ChartBarIcon, SparklesIcon, XMarkIcon, ArrowDownTrayIcon } from '@heroicons/react/24/outline'

export default function AnalysisResults({ data, polling = false, setPolling }) {
  const [selectedImage, setSelectedImage] = useState(null) // { filename, title }
  const [images, setImages] = useState([]) // { filename, title, url?, analysis? }
  const [lastFetch, setLastFetch] = useState(null)
  const endRef = useRef(null)
  const sseRef = useRef(null)
  const pollSessionStartedRef = useRef(false) // để chỉ clear images khi vừa bắt đầu polling

  // ESC để đóng modal
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') setSelectedImage(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const openModal = (file) => setSelectedImage(file)
  const closeModal = () => setSelectedImage(null)

  // Polling danh sách ảnh
  useEffect(() => {
    let timer = null
    let isMounted = true
    let consecutiveEmptyResponses = 0

    const fetchList = async () => {
      try {
        const res = await axios.get('/api/results/list', { timeout: 5000 })
        if (!isMounted) return

        if (res.data && res.data.images) {
          setLastFetch(Date.now())

          if (res.data.images.length > 0) {
            consecutiveEmptyResponses = 0
          } else {
            consecutiveEmptyResponses++
          }

          setImages(prev => {
            const exist = new Set(prev.map(i => i.filename))
            const combined = [...prev]
            res.data.images.forEach(img => {
              if (!exist.has(img.filename)) {
                combined.push(img)
              }
            })

            // nếu tất cả đã có analysis thì dừng polling
            if (combined.length > 0 && combined.every(img => img.analysis)) {
              console.log('All images have analysis, stopping polling')
              setPolling?.(false)
            }

            return combined
          })

          // sau 3 lần rỗng thì dừng polling
          if (consecutiveEmptyResponses >= 3) {
            console.log('No new images after 3 attempts, stopping polling')
            setPolling?.(false)
          }
        }
      } catch (e) {
        console.error('Error fetching image list:', e)
        setPolling?.(false)
      }
    }

    if(polling) {
      console.log('Polling started; keeping existing images and accumulating new ones')

      // Fetch list of images and analyze each one
      const analyzeAllImages = async () => {
        try {
          // Fetch list of images
          const res = await axios.get('/api/results/list', { timeout: 5000 })
          if(res.data && res.data.images) {
            console.log('Found images:', res.data.images.length)
            
            // Reset images state with new images
            const incoming = res.data.images.map(img => ({
              ...img,
              analysis: null,
              url: img.url || `/api/results/${img.filename}`
            }))

            // Merge incoming with existing without dropping older items
            let mergedForLoop = []
            setImages(prev => {
              const existingByName = new Map(prev.map(i => [i.filename, i]))
              const merged = [...prev]
              incoming.forEach(img => {
                if (!existingByName.has(img.filename)) merged.push(img)
              })
              mergedForLoop = merged
              return merged
            })

            // Analyze images one by one
            for (const img of mergedForLoop) {
              try {
                console.log('Analyzing image:', img.filename)
                const analysisRes = await axios.post('/api/analyze_image', {
                  filename: img.filename
                })
                
                if (analysisRes.data && analysisRes.data.analysis) {
                  console.log('Got analysis for:', img.filename, analysisRes.data.analysis)
                  
                  // Cập nhật state ngay lập tức cho ảnh này
                  const updatedImage = { 
                    ...img, 
                    analysis: analysisRes.data.analysis
                  }
                  
                  setImages(prev => {
                    const updatedImages = [...prev]
                    const index = updatedImages.findIndex(i => i.filename === img.filename)
                    if (index !== -1) {
                      updatedImages[index] = updatedImage
                    }
                    return updatedImages
                  })
                  
                  // Đợi một chút để đảm bảo UI cập nhật
                  await new Promise(resolve => setTimeout(resolve, 100))
                }
              } catch(e) {
                console.error('Error analyzing image:', img.filename, e)
              }
            }
          }
        } catch(e) {
          console.error('Error fetching image list:', e)
          setPolling(false)
        }
      }

      analyzeAllImages()
      timer = setInterval(analyzeAllImages, 10000) // Increased interval to 10 seconds
    }

    return () => {
      isMounted = false
      if (timer) clearInterval(timer)
      // khi polling kết thúc, reset cờ phiên
      if (!polling) {
        pollSessionStartedRef.current = false
      }
    }
  }, [polling, setPolling])

  // Hàm để phân tích một ảnh cụ thể
  const analyzeImage = async (filename) => {
    try {
      console.log('Analyzing image:', filename)
      const response = await axios.post('/api/analyze_image', {
        filename: filename
      })
      if (response.data && response.data.analysis) {
        setImages(prev => {
          return prev.map(img => 
            img.filename === filename 
              ? { ...img, analysis: response.data.analysis }
              : img
          )
        })
      }
    } catch (error) {
      console.error('Error analyzing image:', filename, error)
    }
  }

  // SSE nhận tiến độ phân tích từng ảnh
  useEffect(() => {
    console.log('AnalysisResults useEffect triggered, polling:', polling)
    if (!polling) {
      if (sseRef.current) {
        console.log('Stopping previous SSE connection')
        sseRef.current.close()
        sseRef.current = null
      }
      return
    }

    if (sseRef.current) {
      console.log('SSE connection already exists')
      return
    }

    // Phân tích tất cả ảnh hiện có ngay lập tức
    const analyzeExistingImages = async () => {
      for (const img of images) {
        if (!img.analysis) {
          try {
            console.log('Analyzing existing image:', img.filename)
            const analysisRes = await axios.post('/api/analyze_image', {
              filename: img.filename
            })
            if (analysisRes.data && analysisRes.data.analysis) {
              setImages(prev => 
                prev.map(i => 
                  i.filename === img.filename
                    ? { ...i, analysis: analysisRes.data.analysis }
                    : i
                )
              )
            }
          } catch (e) {
            console.error('Error analyzing existing image:', img.filename, e)
          }
        }
      }
    }
    analyzeExistingImages()

    console.log('Opening new SSE connection to analyze_images_stream')
    const es = new EventSource('/api/analyze_images_stream')
    sseRef.current = es

    es.addEventListener('progress', (evt) => {
      console.log('SSE progress event received')
      try {
        const payload = JSON.parse(evt.data)
        if (!payload?.image) return

        setImages(prev => {
          const found = prev.find(i => i.filename === payload.image)
          if (found) {
            console.log('Updating existing image analysis:', payload.image)
            const updated = prev.map(i =>
              i.filename === payload.image
                ? {
                    ...i,
                    title: i.title || payload.title,
                    analysis: payload.analysis ?? i.analysis,
                    url: `/api/results/${i.filename}`
                  }
                : i
            )

            if (updated.length > 0 && updated.every(img => img.analysis)) {
              console.log('All images have analysis, will stop polling')
              setTimeout(() => setPolling?.(false), 1000)
            }

            return updated
          }

          console.log('Adding new image analysis:', payload.image)
          // Only add if not exists (should be ensured, but double-check)
          const exists = prev.some(i => i.filename === payload.image)
          if (exists) return prev
          return [
            ...prev,
            {
              filename: payload.image,
              title: payload.title,
              analysis: payload.analysis || null,
              url: `/api/results/${payload.image}`
            },
          ]
        })
      } catch (e) {
        console.error('Error parsing SSE progress data:', e)
      }
    })

    es.addEventListener('done', () => {
      console.log('SSE done event received')
      es.close()
      sseRef.current = null
      setPolling?.(false)
    })

    es.onerror = (error) => {
      console.error('SSE connection error:', error)
      try {
        es.close()
        setPolling?.(false)
      } catch {}
      sseRef.current = null
    }

    es.onopen = () => {
      console.log('SSE connection opened successfully')
    }

    return () => {
      if (sseRef.current) {
        try {
          sseRef.current.close()
        } catch {}
        sseRef.current = null
      }
    }
  }, [polling, setPolling])

  // Auto scroll xuống cuối khi thêm ảnh mới
  useEffect(() => {
    if (endRef.current) {
      endRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  }, [images.length])

  // Khi nhận data mới (kết quả final), reset images theo data
  useEffect(() => {
    if (data?.analysis_plots) {
      // Giữ lại analysis cũ nếu có
      setImages(prev => {
        const newImages = data.analysis_plots.map(p => {
          const existingImage = prev.find(img => img.filename === p.filename)
          return {
            filename: p.filename,
            title: p.title,
            url: p.url || `/api/results/${p.filename}`,
            analysis: existingImage?.analysis || null
          }
        })
        console.log('Reset images with new analysis plots:', newImages)
        return newImages
      })
    }
  }, [data])

  return (
    <div className="bg-white/3 border border-white/5 rounded-xl p-6 mt-4">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-semibold">Kết quả phân tích</h3>
          <div className="text-sm text-slate-400 mt-1">
            Số mẫu: <strong className="text-slate-100">{data?.sample_count ?? '—'}</strong> • Features số:{' '}
            <strong className="text-slate-100">{data?.feature_count ?? '—'}</strong>
          </div>
        </div>
        <div className="flex gap-3">
          <div className="text-sm text-slate-400">{data?.timestamp ? new Date(data.timestamp).toLocaleString() : ''}</div>
        </div>
      </div>

      <div className="mt-4">
        <h4 className="font-medium text-sm text-slate-200 flex items-center gap-2">
          <SparklesIcon className="w-4 h-4 text-accent" />
          Tóm tắt thống kê
        </h4>
        <div className="text-sm text-slate-300 mt-2 max-h-56 overflow-auto p-2 bg-black/20 rounded-md">
          <pre className="whitespace-pre-wrap text-xs">
            {JSON.stringify(data?.statistical_analysis?.summary || data?.statistical_analysis || {}, null, 2)}
          </pre>
        </div>
      </div>

      <div className="mt-4">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-medium text-sm text-slate-200 flex items-center gap-2">
            <ChartBarIcon className="w-4 h-4 text-accent" />
            Biểu đồ
          </h4>
        </div>

        <div className="flex flex-col gap-6 mt-4">
          {images && images.length > 0 ? (
            [...images]
              .map((p, _idx) => ({ ...p, _idx }))
              .sort((a, b) => {
                const score = (f) => {
                  if (f?.includes('ml_residual_plot')) return -1 // always last
                  if (f?.includes('ml_elbow_method')) return 3 // first
                  if (f?.includes('ml_pca_clusters')) return 2 // then KMeans clusters
                  return 0 // others keep original relative order
                }
                const sa = score(a.filename)
                const sb = score(b.filename)
                if (sa !== sb) return sb - sa
                return a._idx - b._idx
              })
              .map((p) => (
              <div key={p.filename} className="w-full">
                <img
                  src={p.url || `/api/results/${p.filename}`}
                  alt={p.title}
                  className="w-full h-[520px] object-contain rounded-md border border-white/5"
                  onClick={() => openModal(p)}
                  onError={(e) => {
                    console.error('Error loading image:', p.filename)
                    e.currentTarget.src = `/api/results/${p.filename}`
                  }}
                />
                <div className="text-sm text-slate-300 mt-2">{p.title}</div>

                {/* Gemini AI analysis (nếu có) */}
                <div className="mt-2 p-3 bg-black/20 rounded text-sm text-slate-300">
                  {p.analysis ? (
                    <>
                      <div className="font-medium text-slate-100">Gemini AI đánh giá</div>
                      <div className="mt-1 whitespace-pre-wrap">
                        {typeof p.analysis === 'string' ? p.analysis : (p.analysis?.evaluation || '')}
                      </div>
                      {typeof (typeof p.analysis === 'object' && p.analysis?.confidence) !== 'undefined' && (
                        <div className="text-xs text-slate-400 mt-2">
                          Độ tin cậy: {(Number(typeof p.analysis === 'object' ? p.analysis.confidence : 0) * 100).toFixed(1)}%
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="text-slate-400">Đang chờ phân tích bởi Gemini AI...</div>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="text-sm text-slate-400">Không có biểu đồ để hiển thị</div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      {/* Modal / Lightbox */}
      {selectedImage && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-6"
          onClick={(e) => {
            if (e.target === e.currentTarget) closeModal()
          }}
        >
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />
          <div className="relative max-w-6xl w-full z-10">
            <div className="flex items-start justify-end gap-2 mb-3">
              <a
                href={`/api/results/${selectedImage.filename}`}
                download
                className="inline-flex items-center gap-2 bg-white/6 text-slate-100 px-3 py-2 rounded-md hover:bg-white/10"
              >
                <ArrowDownTrayIcon className="w-5 h-5" />
                Tải về
              </a>
              <button
                onClick={closeModal}
                className="inline-flex items-center justify-center w-10 h-10 rounded-md bg-white/6 hover:bg-white/10"
              >
                <XMarkIcon className="w-5 h-5 text-slate-100" />
              </button>
            </div>

            <div className="bg-transparent p-4 rounded">
              <img
                src={`/api/results/${selectedImage.filename}`}
                alt={selectedImage.title}
                className="w-full max-h-[80vh] object-contain rounded-md mx-auto"
              />
              <div className="text-sm text-slate-300 mt-3 text-center">{selectedImage.title}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
