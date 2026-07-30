// 用户管理弹窗 - 增删改查 + 角色 (admin/user)
import { useEffect, useState } from 'react';
import { X, Plus, Edit2, Trash2, User as UserIcon } from 'lucide-react';
import { api } from '../api/client';

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
            <button className="action-btn primary" onClick={openAdd}>
              <Plus size={14} /> 新增用户
            </button>
          </div>

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