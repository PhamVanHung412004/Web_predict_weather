import { useEffect, useState } from 'react'
import UploadForm from '../components/UploadForm'
import AnalysisResults from '../components/AnalysisResults'
import axios from 'axios'

export default function Home(){
  const [backendStatus, setBackendStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [analysisData, setAnalysisData] = useState(null)
  const [polling, setPolling] = useState(false)

  useEffect(()=>{
    let mounted = true
    axios.get(`/api/health`, { timeout: 3000 }).then(res=>{
      if(mounted) setBackendStatus(res.data)
    }).catch(()=>{
      if(mounted) setBackendStatus({status:'offline'})
    })
    return ()=>mounted=false
  },[])

  return (
    <div className="max-w-6xl mx-auto p-6">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-lg flex items-center justify-center font-bold text-[#021124]" style={{background:'linear-gradient(135deg,#06b6d4,#8b5cf6)'}}>AQ</div>
          <div>
            <div className="text-xl font-bold">Air Quality Analyzer</div>
            <div className="text-sm text-slate-400">Upload CSV → Statistical analysis & ML pipeline</div>
          </div>
        </div>

        <div className="text-sm text-slate-400">
          Backend: <span className="text-slate-100">{backendStatus?.status || 'unknown'}</span>
          {backendStatus?.message && <div className="text-xs">{backendStatus.message}</div>}
        </div>
      </header>

      <main className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6 mt-6">
        <section>
          <UploadForm onResult={(d)=>{ console.log('Index: Analysis complete, keeping polling=true for SSE'); setAnalysisData(d); setPolling(true) }} setLoading={setLoading} onUploadStart={()=>{ console.log('Index: Upload started, setting polling=true'); setPolling(true); setAnalysisData(null) }} />

          {loading && <div className="bg-white/3 border border-white/5 rounded-xl p-4 mt-4 text-sm text-slate-300">Đang xử lý file. Vui lòng chờ (có thể mất một vài giây đến vài phút tùy dữ liệu)...</div>}

          <AnalysisResults data={analysisData} polling={polling} setPolling={setPolling} />
        </section>

        <aside>
          <div className="bg-white/3 border border-white/5 rounded-xl p-4">
            <h4 className="font-semibold">Hướng dẫn nhanh</h4>
            <ul className="text-sm text-slate-400 mt-2 list-disc list-inside">
              <li>Chuẩn bị file CSV có cột số (ví dụ PM2.5, temperature...)</li>
              <li>Tải lên và chờ backend phân tích</li>
              <li>Click vào ảnh để mở biểu đồ lớn</li>
              <li>Sử dụng form Predict để thử mô hình nếu đã có model</li>
            </ul>
          </div>

          <div className="bg-white/3 border border-white/5 rounded-xl p-4 mt-4">
            <h4 className="font-semibold">Backend info</h4>
            <div className="text-sm text-slate-400 mt-2">Proxy: <code className="text-xs">/api/* → backend</code></div>
          </div>
        </aside>
      </main>
    </div>
  )
}
