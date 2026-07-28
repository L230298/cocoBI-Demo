// SQL 编辑 modal - 用户编辑后重新执行
import { useState } from 'react';
import { X, Save, AlertCircle } from 'lucide-react';

interface Props {
  initialSql: string;
  onCancel: () => void;
  onSave: (newSql: string) => Promise<{ ok: boolean; error?: string; rows?: any[]; columns?: string[] }>;
}

export function EditSqlModal({ initialSql, onCancel, onSave }: Props) {
  const [sql, setSql] = useState(initialSql);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    setBusy(true);
    setError(null);
    const result = await onSave(sql);
    setBusy(false);
    if (!result.ok) {
      setError(result.error || '执行失败');
    }
  };

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal-content edit-sql-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>编辑 SQL</h3>
          <button className="modal-close" onClick={onCancel} aria-label="关闭">
            <X size={18} />
          </button>
        </div>
        <div className="modal-body">
          <p className="modal-hint">
            <AlertCircle size={14} /> 只能 SELECT(只读);修改后我会重新执行并刷新结果。
          </p>
          <textarea
            className="sql-editor"
            value={sql}
            onChange={(e) => setSql(e.target.value)}
            spellCheck={false}
          />
          {error && <div className="error-display" style={{ marginTop: 12 }}>{error}</div>}
        </div>
        <div className="modal-footer">
          <button className="action-btn" onClick={onCancel} disabled={busy}>取消</button>
          <button
            className="action-btn primary"
            onClick={handleSave}
            disabled={busy}
          >
            <Save size={14} /> {busy ? '执行中...' : '保存并执行'}
          </button>
        </div>
      </div>
    </div>
  );
}
