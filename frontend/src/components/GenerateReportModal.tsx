// 生成数据报告确认 modal
import { useState } from 'react';
import { X, FileText, AlertCircle } from 'lucide-react';

interface Props {
  mode: 'single' | 'batch';
  selectedCount?: number;
  totalCount?: number;
  onCancel: () => void;
  onConfirm: () => Promise<void>;
}

export function GenerateReportModal({ mode, selectedCount, totalCount, onCancel, onConfirm }: Props) {
  const [busy, setBusy] = useState(false);

  const handleConfirm = async () => {
    setBusy(true);
    await onConfirm();
    setBusy(false);
  };

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal-content generate-report-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>
            <FileText size={18} style={{ verticalAlign: 'middle', marginRight: 6 }} />
            生成数据报告
          </h3>
          <button className="modal-close" onClick={onCancel} aria-label="关闭">
            <X size={18} />
          </button>
        </div>
        <div className="modal-body">
          {mode === 'batch' && (
            <p className="batch-info">
              将基于 <strong>{selectedCount}</strong> / {totalCount} 个历史 query 生成报告
            </p>
          )}
          <p className="modal-hint">
            <AlertCircle size={14} /> 报告包含各 query 的 SQL + 数据表(每个一张)。继续?
          </p>
        </div>
        <div className="modal-footer">
          <button className="action-btn" onClick={onCancel} disabled={busy}>取消</button>
          <button
            className="action-btn primary"
            onClick={handleConfirm}
            disabled={busy}
          >
            {busy ? '生成中...' : '确认生成'}
          </button>
        </div>
      </div>
    </div>
  );
}
