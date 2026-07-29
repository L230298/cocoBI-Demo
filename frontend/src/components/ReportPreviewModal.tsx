// 报告预览弹窗 - 浏览器内直接显示, 不再自动下载 docx
import { useEffect, useState, useRef } from 'react';
import { X, FileText, Download, Loader2 } from 'lucide-react';

interface Props {
  queryIds: string[];
  datasetId: string;
  onClose: () => void;
  // 真实下载 docx 的方法 (来自 useAnalysis)
  onDownload: () => Promise<void>;
}

export function ReportPreviewModal({ queryIds, datasetId, onClose, onDownload }: Props) {
  const [html, setHtml] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    let aborted = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch('/api/report/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query_ids: queryIds,
            dataset_id: datasetId,
            format: 'html',
          }),
        });
        if (!res.ok) {
          throw new Error(`生成失败: ${res.status}`);
        }
        const text = await res.text();
        if (!aborted) {
          setHtml(text);
          setLoading(false);
        }
      } catch (e: any) {
        if (!aborted) {
          setError(e.message || '加载失败');
          setLoading(false);
        }
      }
    })();
    return () => { aborted = true; };
  }, [queryIds, datasetId]);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await onDownload();
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="modal-backdrop report-preview-backdrop" onClick={onClose}>
      <div
        className="report-preview-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="report-preview-header">
          <h3>
            <FileText size={18} style={{ verticalAlign: 'middle', marginRight: 6 }} />
            数据分析报告
          </h3>
          <button className="modal-close" onClick={onClose} aria-label="关闭">
            <X size={18} />
          </button>
        </div>
        <div className="report-preview-body">
          {loading && (
            <div className="report-preview-loading">
              <Loader2 size={32} className="spin" />
              <p>正在生成报告...</p>
            </div>
          )}
          {error && (
            <div className="report-preview-error">
              <p>❌ {error}</p>
            </div>
          )}
          {!loading && !error && (
            <iframe
              ref={iframeRef}
              srcDoc={html}
              title="数据分析报告"
              className="report-preview-iframe"
            />
          )}
        </div>
        <div className="report-preview-footer">
          <button className="action-btn" onClick={onClose}>
            关闭
          </button>
          <button
            className="action-btn primary"
            onClick={handleDownload}
            disabled={loading || downloading}
          >
            <Download size={14} />
            {downloading ? '下载中...' : '下载 .docx'}
          </button>
        </div>
      </div>
    </div>
  );
}
