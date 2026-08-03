// 用户管理弹窗 - 增删改查 + 角色 (admin/user) + 日志下载
import { useEffect, useState } from 'react';
import { X, Plus, Edit2, Trash2, User as UserIcon, Download, FileText, RefreshCw } from 'lucide-react';
import { api, API_BASE_URL } from '../api/client';

interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  created_at: string;
}

interface Props {
  onCancel: () => void;
}

export function UserManagementModal({ onCancel }: Props) {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', email: '', role: 'user' });
  const [error, setError] = useState('');

  const loadUsers = async () => {
    setLoading(true);
    try {
      const list = await api.listUsers();
      setUsers(list);
    } catch (e: any) {
      setError(e.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const openAdd = () => {
    setEditing(null);
    setForm({ name: '', email: '', role: 'user' });
    setError('');
    setShowForm(true);
  };

  const openEdit = (u: User) => {
    setEditing(u);
    setForm({ name: u.name, email: u.email, role: u.role });
    setError('');
    setShowForm(true);
  };

  const handleSubmit = async () => {
    setError('');
    try {
      if (editing) {
        await api.updateUser(editing.id, form);
      } else {
        await api.addUser(form);
      }
      setShowForm(false);
      await loadUsers();
    } catch (e: any) {
      setError(e.message || '保存失败');
    }
  };

  const handleDelete = async (u: User) => {
    if (!confirm(`确定删除用户「${u.name}」?`)) return;
    try {
      await api.deleteUser(u.id);
      await loadUsers();
    } catch (e: any) {
      alert('删除失败: ' + (e.message || ''));
    }
  };

  // 日志导出格式: text (原始) / csv (Excel 友好)
  const [logFormat, setLogFormat] = useState<'text' | 'csv'>('text');

  const handleDownloadLog = async () => {
    try {
      const blob = await api.downloadLog(logFormat);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const date = new Date().toISOString().slice(0, 10);
      const ext = logFormat === 'csv' ? 'csv' : 'log';
      a.download = `cocoBI-app-${date}.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      alert('日志下载失败: ' + (e.message || ''));
    }
  };

  // 日志列表(轮转的也能选)
  const [logFiles, setLogFiles] = useState<{ name: string; size_bytes: number; modified: string }[]>([]);
  const [logLoading, setLogLoading] = useState(false);

  const loadLogs = async () => {
    setLogLoading(true);
    try {
      const data = await api.listLogs();
      setLogFiles(data.files);
    } catch (e: any) {
      console.warn('加载日志列表失败:', e.message);
    } finally {
      setLogLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  const handleDownloadLogFile = (filename: string) => {
    // 单文件下载遵循当前格式选择
    const params = new URLSearchParams({ file: filename });
    if (logFormat === 'csv') params.set('format', 'csv');
    window.open(`${API_BASE_URL}/log/download?${params.toString()}`, '_blank');
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal-content user-manage-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>
            <UserIcon size={16} style={{ verticalAlign: 'middle', marginRight: 6 }} />
            用户管理
          </h3>
          <button className="modal-close" onClick={onCancel} aria-label="关闭">
            <X size={18} />
          </button>
        </div>

        <div className="modal-body user-manage-body">
          <div className="user-manage-toolbar">
            <span className="user-manage-count">共 {users.length} 个用户</span>
            <div className="user-manage-actions">
              <select
                className="log-format-select"
                value={logFormat}
                onChange={(e) => setLogFormat(e.target.value as 'text' | 'csv')}
                title="选择日志导出格式"
                aria-label="日志格式"
              >
                <option value="text">📄 原始 (.log)</option>
                <option value="csv">📊 CSV (.csv, Excel)</option>
              </select>
              <button className="action-btn" onClick={handleDownloadLog} title={`下载当前日志 (app.${logFormat === 'csv' ? 'csv' : 'log'})`}>
                <Download size={14} /> 下载当前日志
              </button>
              <button className="action-btn primary" onClick={openAdd}>
                <Plus size={14} /> 新增用户
              </button>
            </div>
          </div>

          {/* 日志文件列表 (含轮转历史) */}
          <details className="log-files-section">
            <summary>
              <FileText size={13} style={{ verticalAlign: 'middle', marginRight: 4 }} />
              日志文件 ({logFiles.length} 个, 累计 {formatSize(logFiles.reduce((s, f) => s + f.size_bytes, 0))})
              <button
                className="user-icon-btn"
                style={{ marginLeft: 8 }}
                onClick={(e) => { e.preventDefault(); loadLogs(); }}
                title="刷新"
              >
                <RefreshCw size={12} className={logLoading ? 'spin' : ''} />
              </button>
            </summary>
            {logFiles.length === 0 ? (
              <div className="log-files-empty">暂无日志文件</div>
            ) : (
              <table className="log-files-table">
                <thead>
                  <tr>
                    <th>文件名</th>
                    <th>大小</th>
                    <th>更新时间</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {logFiles.map((f) => (
                    <tr key={f.name}>
                      <td><code>{f.name}</code></td>
                      <td>{formatSize(f.size_bytes)}</td>
                      <td className="user-time">{f.modified.replace('T', ' ').slice(0, 16)}</td>
                      <td>
                        <button
                          className="user-icon-btn"
                          onClick={() => handleDownloadLogFile(f.name)}
                          title={`下载 ${f.name}`}
                          aria-label="下载"
                        >
                          <Download size={12} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </details>

          {showForm && (
            <div className="user-form">
              <div className="user-form-title">
                {editing ? `编辑用户 #${editing.id}` : '新增用户'}
              </div>
              <div className="user-form-row">
                <label>
                  用户名
                  <input
                    type="text"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="请输入用户名"
                  />
                </label>
                <label>
                  邮箱
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    placeholder="user@example.com"
                  />
                </label>
                <label>
                  角色
                  <select
                    value={form.role}
                    onChange={(e) => setForm({ ...form, role: e.target.value })}
                  >
                    <option value="user">普通用户</option>
                    <option value="admin">管理员</option>
                  </select>
                </label>
              </div>
              {error && <div className="user-form-error">⚠ {error}</div>}
              <div className="user-form-actions">
                <button className="action-btn" onClick={() => setShowForm(false)}>
                  取消
                </button>
                <button className="action-btn primary" onClick={handleSubmit}>
                  {editing ? '保存修改' : '创建'}
                </button>
              </div>
            </div>
          )}

          {loading ? (
            <div className="user-manage-loading">加载中...</div>
          ) : users.length === 0 ? (
            <div className="user-manage-empty">暂无用户, 点"新增用户"开始</div>
          ) : (
            <table className="user-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>用户名</th>
                  <th>邮箱</th>
                  <th>角色</th>
                  <th>创建时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td><code>{u.id}</code></td>
                    <td>{u.name}</td>
                    <td>{u.email}</td>
                    <td>
                      <span className={`role-badge role-${u.role}`}>
                        {u.role === 'admin' ? '管理员' : '普通用户'}
                      </span>
                    </td>
                    <td className="user-time">{u.created_at.replace('T', ' ').slice(0, 16)}</td>
                    <td className="user-actions">
                      <button
                        className="user-icon-btn"
                        onClick={() => openEdit(u)}
                        title="编辑"
                        aria-label="编辑"
                      >
                        <Edit2 size={14} />
                      </button>
                      <button
                        className="user-icon-btn danger"
                        onClick={() => handleDelete(u)}
                        title="删除"
                        aria-label="删除"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="modal-footer">
          <button className="action-btn" onClick={onCancel}>
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}