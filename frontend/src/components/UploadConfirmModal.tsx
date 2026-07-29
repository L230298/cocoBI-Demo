// 文件上传确认弹窗 - PRD §1.1 数据导入确认
import { useState } from 'react';
import { X, FileSpreadsheet, CheckCircle2 } from 'lucide-react';

interface Props {
  fileName: string;
  sheetName: string;
  rowCount: number;
  columnCount: number;
  onCancel: () => void;
  onConfirm: () => Promise<void>;
}

export function UploadConfirmModal({
  fileName,
  sheetName,
  rowCount,
  columnCount,
  onCancel,
  onConfirm,
}: Props) {
  const [busy, setBusy] = useState(false);

  const handleConfirm = async () => {
    setBusy(true);
    try {
      await onConfirm();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal-content upload-confirm-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header upload-confirm-header">
          <span className="upload-confirm-filename">{fileName}</span>
          <button className="modal-close" onClick={onCancel} aria-label="关闭">
            <X size={18} />
          </button>
        </div>
        <div className="modal-body upload-confirm-body">
          <div className="upload-confirm-row">
            <CheckCircle2 size={18} className="upload-confirm-icon" />
            <div className="upload-confirm-info">
              <div className="upload-confirm-sheet">{sheetName}</div>
              <div className="upload-confirm-dim">
                {rowCount} 行 × {columnCount} 列
              </div>
            </div>
          </div>
        </div>
        <div className="modal-footer upload-confirm-footer">
          <button className="action-btn" onClick={onCancel} disabled={busy}>
            取消
          </button>
          <button
            className="action-btn primary"
            onClick={handleConfirm}
            disabled={busy}
          >
            {busy ? '导入中...' : '确认导入'}
          </button>
        </div>
      </div>
    </div>
  );
}
