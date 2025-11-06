import { useEffect, useState } from 'react'
import { approvalsAPI, api } from '../../utils/api'

export default function AdminApprovals() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [type, setType] = useState('all')
  const [status, setStatus] = useState('pending')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [previewVideo, setPreviewVideo] = useState(null)

  useEffect(() => {
    load()
  }, [type, status, page])

  const load = async () => {
    setLoading(true)
    try {
      const t = type === 'all' ? null : type
      const s = status === 'all' ? null : status
      const res = await approvalsAPI.getPending(t, s, page, 20)
      setItems(res.data.items)
      setTotal(res.data.total)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const approve = async (id) => {
    try {
      await approvalsAPI.approve(id)
      load()
    } catch (e) {
      alert(e.response?.data?.detail || 'خطا در تایید')
    }
  }

  const reject = async (id) => {
    const reason = prompt('دلیل رد: (اختیاری)') || null
    try {
      await approvalsAPI.reject(id, reason)
      load()
    } catch (e) {
      alert(e.response?.data?.detail || 'خطا در رد')
    }
  }

  const getStatusColor = (status) => {
    if (status === 'pending') return 'bg-yellow-100 text-yellow-700'
    if (status === 'approved') return 'bg-green-100 text-green-700'
    if (status === 'rejected') return 'bg-red-100 text-red-700'
    return 'bg-gray-100 text-gray-700'
  }

  const getStatusText = (status) => {
    if (status === 'pending') return 'در انتظار'
    if (status === 'approved') return 'تایید شده'
    if (status === 'rejected') return 'رد شده'
    return status
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">درخواست‌ها</h1>
        <div className="flex gap-2">
          <select value={type} onChange={(e) => { setPage(1); setType(e.target.value) }} className="input">
            <option value="all">همه نوع</option>
            <option value="video">ویدیو</option>
            <option value="channel">کانال</option>
          </select>
          <select value={status} onChange={(e) => { setPage(1); setStatus(e.target.value) }} className="input">
            <option value="all">همه وضعیت</option>
            <option value="pending">در انتظار</option>
            <option value="approved">تایید شده</option>
            <option value="rejected">رد شده</option>
          </select>
        </div>
      </div>

      {previewVideo && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50" onClick={() => setPreviewVideo(null)}>
          <div className="bg-white rounded-lg p-6 max-w-4xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">پیش‌نمایش ویدیو</h2>
              <button onClick={() => setPreviewVideo(null)} className="text-gray-500 hover:text-gray-700 text-2xl font-bold">×</button>
            </div>
            <div className="p-4">
              <video
                controls
                className="w-full rounded"
                style={{ maxHeight: '70vh' }}
                src={approvalsAPI.getVideoUrl(previewVideo)}
              >
                مرورگر شما از پخش ویدیو پشتیبانی نمی‌کند
              </video>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        {loading ? (
          <div className="p-6">در حال بارگذاری...</div>
        ) : items.length === 0 ? (
          <div className="p-6 text-gray-500">هیچ درخواستی نیست</div>
        ) : (
          <div className="divide-y">
            {items.map((it) => (
              <div key={it.id} className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="font-medium">{it.type === 'video' ? 'ویدیو' : 'کانال'} #{it.entity_id}</span>
                      <span className={`px-2 py-1 rounded text-xs ${getStatusColor(it.status)}`}>
                        {getStatusText(it.status)}
                      </span>
                    </div>
                    {it.user && (
                      <div className="text-sm text-gray-700 mb-2 p-2 bg-gray-50 rounded">
                        <div className="font-medium">👤 کاربر: {it.user.name || it.user.email || it.user.phone || 'نامشخص'}</div>
                        {it.user.email && <div className="text-xs text-gray-500">📧 {it.user.email}</div>}
                        {it.user.phone && <div className="text-xs text-gray-500">📱 {it.user.phone}</div>}
                      </div>
                    )}
                    {it.entity && (
                      <div className="text-sm text-gray-600 mb-2">
                        {it.type === 'video' && (
                          <>
                            <div className="font-medium">📹 عنوان: {it.entity.title}</div>
                            <div>حجم: {it.entity.file_size ? Math.round(it.entity.file_size / 1024 / 1024) : '-'} MB</div>
                            {it.entity.duration && (
                              <div>مدت زمان: {Math.floor(it.entity.duration / 60)}:{String(it.entity.duration % 60).padStart(2, '0')}</div>
                            )}
                          </>
                        )}
                        {it.type === 'channel' && (
                          <>
                            <div className="font-medium">📺 نام: {it.entity.name}</div>
                            {it.entity.aparat_link && (
                              <div className="mt-1">
                                <a 
                                  href={it.entity.aparat_link} 
                                  target="_blank" 
                                  rel="noopener noreferrer"
                                  className="text-blue-600 hover:text-blue-800 underline"
                                >
                                  🔗 {it.entity.aparat_link}
                                </a>
                              </div>
                            )}
                            {it.entity.rtmp_url && (
                              <div className="text-xs text-gray-500 mt-1">
                                RTMP: {it.entity.rtmp_url}
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    )}
                    <div className="text-xs text-gray-400 space-y-1">
                      <div>درخواست: {new Date(it.requested_at).toLocaleString('fa-IR')}</div>
                      {it.approved_at && (
                        <div>
                          {it.status === 'approved' ? 'تایید' : 'رد'} شده در: {new Date(it.approved_at).toLocaleString('fa-IR')}
                        </div>
                      )}
                      {it.reason && it.status === 'rejected' && (
                        <div className="text-red-600">دلیل رد: {it.reason}</div>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {it.type === 'video' && it.status === 'pending' && (
                      <button 
                        onClick={() => setPreviewVideo(it.id)} 
                        className="btn-secondary text-sm"
                      >
                        مشاهده
                      </button>
                    )}
                    {it.status === 'pending' && (
                      <>
                        <button onClick={() => approve(it.id)} className="btn-primary text-sm">تایید</button>
                        <button onClick={() => reject(it.id)} className="btn-secondary text-sm">رد</button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="flex justify-center gap-2 p-4">
          <button disabled={page===1} onClick={() => setPage(p=>Math.max(1,p-1))} className="btn-secondary disabled:opacity-50">قبلی</button>
          <span className="px-2 py-1">صفحه {page}</span>
          <button disabled={page*20>=total} onClick={() => setPage(p=>p+1)} className="btn-secondary disabled:opacity-50">بعدی</button>
        </div>
      </div>
    </div>
  )
}


