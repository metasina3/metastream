import { useState, useEffect } from 'react'
import { adminAPI } from '../../utils/api'
import { PencilIcon, TrashIcon, UserPlusIcon } from '@heroicons/react/24/outline'

export default function AdminUsers() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [showModal, setShowModal] = useState(false)
  const [editingUser, setEditingUser] = useState(null)

  useEffect(() => {
    loadUsers()
  }, [page])

  const loadUsers = async () => {
    try {
      const response = await adminAPI.getUsers(page, 20)
      setUsers(response.data.users)
      setTotal(response.data.total)
    } catch (error) {
      console.error('Error loading users:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateUser = async (formData) => {
    try {
      await adminAPI.createUser(formData)
      setShowModal(false)
      loadUsers()
    } catch (error) {
      const d = error.response?.data
      let msg = 'خطا در ایجاد کاربر'
      if (d?.detail) {
        if (Array.isArray(d.detail)) {
          msg = d.detail.map((e) => e.msg || e.detail || JSON.stringify(e)).join(' | ')
        } else if (typeof d.detail === 'object') {
          msg = d.detail.msg || d.detail.detail || JSON.stringify(d.detail)
        } else {
          msg = d.detail
        }
      }
      alert(msg)
    }
  }

  const handleUpdateUser = async (id, formData) => {
    try {
      await adminAPI.updateUser(id, formData)
      setEditingUser(null)
      loadUsers()
    } catch (error) {
      const d = error.response?.data
      let msg = 'خطا در ویرایش کاربر'
      if (d?.detail) {
        if (Array.isArray(d.detail)) {
          msg = d.detail.map((e) => e.msg || e.detail || JSON.stringify(e)).join(' | ')
        } else if (typeof d.detail === 'object') {
          msg = d.detail.msg || d.detail.detail || JSON.stringify(d.detail)
        } else {
          msg = d.detail
        }
      }
      alert(msg)
    }
  }

  const handleDeleteUser = async (id) => {
    if (!confirm('آیا از حذف این کاربر مطمئن هستید؟')) return
    try {
      await adminAPI.deleteUser(id)
      loadUsers()
    } catch (error) {
      const d = error.response?.data
      let msg = 'خطا در حذف کاربر'
      if (d?.detail) {
        if (Array.isArray(d.detail)) {
          msg = d.detail.map((e) => e.msg || e.detail || JSON.stringify(e)).join(' | ')
        } else if (typeof d.detail === 'object') {
          msg = d.detail.msg || d.detail.detail || JSON.stringify(d.detail)
        } else {
          msg = d.detail
        }
      }
      alert(msg)
    }
  }

  if (loading) {
    return <div className="text-center py-12">در حال بارگذاری...</div>
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">مدیریت کاربران</h1>
        <button
          onClick={async () => {
            try {
              await adminAPI.revertImpersonation()
              window.location.replace('/admin')
            } catch (e) {}
          }}
          className="btn-secondary"
        >
          بازگشت به ادمین
        </button>
        <button
          onClick={() => setShowModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <UserPlusIcon className="w-5 h-5" />
          کاربر جدید
        </button>
      </div>

      <div className="card overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b">
              <th className="text-right p-4">نام</th>
              <th className="text-right p-4">شماره</th>
              <th className="text-right p-4">ایمیل</th>
              <th className="text-right p-4">نقش</th>
              <th className="text-right p-4">وضعیت</th>
              <th className="text-right p-4">انقضاء</th>
              <th className="text-right p-4">عملیات</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id} className="border-b hover:bg-gray-50">
                <td className="p-4">{user.name || 'بدون نام'}</td>
                <td className="p-4">{user.phone}</td>
                <td className="p-4">{user.email || '-'}</td>
                <td className="p-4">
                  <span className={`px-2 py-1 rounded text-sm ${
                    user.role === 'admin' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-700'
                  }`}>
                    {user.role === 'admin' ? 'مدیر' : 'کاربر'}
                  </span>
                </td>
                <td className="p-4">
                  <span className={`px-2 py-1 rounded text-sm ${
                    user.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                  }`}>
                    {user.is_active ? 'فعال' : 'غیرفعال'}
                  </span>
                </td>
                <td className="p-4">
                  {user.role === 'admin'
                    ? 'نامحدود'
                    : (user.expires_at
                        ? (() => {
                            const diffMs = new Date(user.expires_at).getTime() - Date.now()
                            const days = Math.ceil(diffMs / (1000 * 60 * 60 * 24))
                            return days > 0 ? `${new Date(user.expires_at).toLocaleDateString('fa-IR')} (مانده ${days} روز)` : 'منقضی شده'
                          })()
                        : 'نامحدود')}
                </td>
                <td className="p-4">
                  <div className="flex gap-2">
                    {user.role !== 'admin' && (
                      <RenewButton user={user} onDone={loadUsers} />
                    )}
                    <button
                      onClick={() => setEditingUser(user)}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      <PencilIcon className="w-5 h-5" />
                    </button>
                    <button
                      onClick={async () => {
                        try {
                          await adminAPI.impersonateUser(user.id)
                          window.location.replace('/dashboard')
                        } catch (e) {}
                      }}
                      className="text-emerald-600 hover:text-emerald-800"
                    >
                      ورود
                    </button>
                    <button
                      onClick={() => handleDeleteUser(user.id)}
                      className="text-red-600 hover:text-red-800"
                    >
                      <TrashIcon className="w-5 h-5" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Pagination */}
        <div className="flex justify-center gap-2 mt-4">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn-secondary disabled:opacity-50"
          >
            قبلی
          </button>
          <span className="px-4 py-2">صفحه {page}</span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={page * 20 >= total}
            className="btn-secondary disabled:opacity-50"
          >
            بعدی
          </button>
        </div>
      </div>

      {/* Create/Edit Modal */}
      {(showModal || editingUser) && (
        <UserModal
          user={editingUser}
          onClose={() => {
            setShowModal(false)
            setEditingUser(null)
          }}
          onSubmit={editingUser ? handleUpdateUser : handleCreateUser}
        />
      )}
    </div>
  )
}

function UserModal({ user, onClose, onSubmit }) {
  const [formData, setFormData] = useState({
    phone: user?.phone || '',
    email: user?.email || '',
    name: user?.name || '',
    password: '',
    role: user?.role || 'user',
    is_active: user?.is_active !== undefined ? user.is_active : true,
    unlimited: user?.role === 'admin' ? true : !user?.expires_at,
    days: 30,
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    const payload = {}
    if (formData.phone && formData.phone.trim()) payload.phone = formData.phone.trim()
    if (formData.email && formData.email.trim()) payload.email = formData.email.trim()
    payload.name = formData.name || ''
    payload.role = formData.role
    payload.is_active = formData.is_active
    if (formData.password && formData.password.trim()) payload.password = formData.password
    if (formData.role === 'user') {
      payload.days = formData.unlimited ? 0 : formData.days
    }
    if (user?.id) {
      // Update: pass id and payload
      onSubmit(user.id, payload)
    } else {
      // Create: pass only payload
      onSubmit(payload)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="card max-w-md w-full">
        <h2 className="text-2xl font-bold mb-4">
          {user ? 'ویرایش کاربر' : 'کاربر جدید'}
        </h2>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">شماره موبایل</label>
            <input
              type="tel"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              className="input w-full"
              placeholder="0912xxxxxxx"
            />
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">ایمیل</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="input w-full"
              placeholder="user@example.com"
            />
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">نام</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="input w-full"
              required
            />
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">رمز عبور</label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              className="input w-full"
              placeholder={user ? 'خالی بگذارید تا تغییر نکند' : 'رمز عبور'}
              {...(user ? {} : { required: true })}
            />
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">نقش</label>
            <select
              value={formData.role}
              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
              className="input w-full"
            >
              <option value="user">کاربر</option>
              <option value="admin">مدیر</option>
            </select>
          </div>
          {formData.role === 'user' && (
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">اشتراک</label>
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formData.unlimited}
                    onChange={(e) => setFormData({ ...formData, unlimited: e.target.checked })}
                    className="w-4 h-4"
                  />
                  <span>نامحدود</span>
                </label>
                {!formData.unlimited && (
                  <div className="flex items-center gap-2">
                    <span>روز:</span>
                    <input
                      type="number"
                      min={1}
                      value={formData.days}
                      onChange={(e) => setFormData({ ...formData, days: parseInt(e.target.value || '0', 10) })}
                      className="input w-24"
                    />
                  </div>
                )}
              </div>
            </div>
          )}
          <div className="mb-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="w-4 h-4"
              />
              <span>فعال</span>
            </label>
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">
              انصراف
            </button>
            <button type="submit" className="btn-primary flex-1">
              {user ? 'ویرایش' : 'ایجاد'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function RenewButton({ user, onDone }) {
  const [open, setOpen] = useState(false)
  const [days, setDays] = useState(30)
  const [unlimited, setUnlimited] = useState(!user.expires_at)
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await adminAPI.updateUser(user.id, { days: unlimited ? 0 : Number(days) })
      setOpen(false)
      onDone?.()
    } catch (err) {
      const d = err.response?.data
      let msg = 'خطا در تمدید'
      if (d?.detail) {
        if (Array.isArray(d.detail)) {
          msg = d.detail.map((e) => e.msg || e.detail || JSON.stringify(e)).join(' | ')
        } else if (typeof d.detail === 'object') {
          msg = d.detail.msg || d.detail.detail || JSON.stringify(d.detail)
        } else {
          msg = d.detail
        }
      }
      alert(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <button onClick={() => setOpen(true)} className="text-amber-600 hover:text-amber-800">تمدید</button>
      {open && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="card max-w-sm w-full">
            <h3 className="text-xl font-bold mb-4">تمدید اشتراک</h3>
            <form onSubmit={submit}>
              <div className="mb-4 flex items-center gap-2">
                <input type="checkbox" checked={unlimited} onChange={(e) => setUnlimited(e.target.checked)} />
                <label>نامحدود</label>
              </div>
              {!unlimited && (
                <div className="mb-4">
                  <label className="block text-sm font-medium mb-2">تعداد روز</label>
                  <input type="number" min="1" value={days} onChange={(e) => setDays(e.target.value)} className="input w-full" />
                </div>
              )}
              <div className="flex justify-end gap-2">
                <button type="button" className="btn-secondary" onClick={() => setOpen(false)}>انصراف</button>
                <button disabled={loading} className="btn-primary">{loading ? 'در حال ذخیره...' : 'ذخیره'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}

