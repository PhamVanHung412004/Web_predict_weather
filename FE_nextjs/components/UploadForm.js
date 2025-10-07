import { useState } from 'react'
import axios from 'axios'
import { ArrowUpTrayIcon } from '@heroicons/react/24/outline'

export default function UploadForm({ onResult, setLoading, onUploadStart }){
  const [file, setFile] = useState(null)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) =>{
    e.preventDefault()
    setError(null)
    if(!file){ setError('Vui lòng chọn file CSV'); return }

    try{
      // notify parent that upload/processing is starting so UI can poll for images
      console.log('UploadForm: Starting upload, calling onUploadStart')
      onUploadStart && onUploadStart()
      setLoading(true)
      const formData = new FormData()
      formData.append('csv_file', file)

      const res = await axios.post(`/api/analyze_csv`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000
      })

      if(res.data){
        onResult(res.data)
        // Trigger SSE analysis after successful upload
        console.log('UploadForm: Upload successful, triggering SSE analysis')
      }
    }catch(err){
      console.error(err)
      setError(err?.response?.data?.error || err.message || 'Lỗi khi gửi file')
    }finally{
      setLoading(false)
    }
  }

  return (
    <div className="bg-white/3 border border-white/5 rounded-xl p-6">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
  <label className="flex items-center gap-3 p-4 border-2 border-dashed border-white/20 rounded-lg cursor-pointer">
          <ArrowUpTrayIcon className="w-6 h-6 text-accent" />
          <span className="text-sm text-slate-200">Chọn file CSV</span>
          <input className="sr-only" type="file" accept=".csv" onChange={(e)=>setFile(e.target.files[0])} />
        </label>

        <div className="flex items-center gap-3">
          <button className="bg-accent text-[#021124] font-semibold py-2 px-4 rounded-lg" type="submit">Tải lên & Phân tích</button>
          <div className="text-sm text-slate-400">Dung lượng tối đa: 16 MB</div>
        </div>

        {file && <div className="text-sm text-slate-200">File đã chọn: {file.name}</div>}
        {error && <div className="p-3 rounded-md bg-red-900/20 border border-red-600/20 text-red-300">{error}</div>}
      </form>
    </div>
  )
}
