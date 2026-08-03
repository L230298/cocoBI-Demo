// 历史记录面板 - 显示用户的提问历史
import type { DatasetInfo } from '../types';

export interface HistoryItem {
  id: string;
  query: string;
  dataset_id: string;
  dataset_name?: string;  // 提交时的数据集名(便于跨刷新显示)
  created_at: string;
}

interface Props {
  items: HistoryItem[];
  activeDataset?: DatasetInfo | null;
  onSelect: (query: string) => void;
  onClear: () => void;
  onDelete?: (id: string) => void;
}

// 智能时间显示: 今天 -> HH:MM; 跨天 -> MM/DD HH:MM; 更早 -> YYYY/MM/DD
function formatHistoryTime(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  if (sameDay) return `${hh}:${mm}`;
  const sameYear = d.getFullYear() === now.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, '0');
  const da = String(d.getDate()).padStart(2, '0');
  return sameYear ? `${mo}/${da} ${hh}:${mm}` : `${d.getFullYear()}/${mo}/${da} ${hh}:${mm}`;
}

export function HistoryPanel({ items, activeDataset, onSelect, onClear, onDelete }: Props) {
  const filtered = activeDataset
    ? items.filter((item) => item.dataset_id === activeDataset.dataset_id)
    : items;

  return (
    <div className="history-panel">
      <div className="history-header">
        <h4>🕘 历史记录 ({filtered.length})</h4>
        {filtered.length > 0 && (
          <button className="history-clear-btn" onClick={onClear} title="清空全部历史">
            清空
          </button>
        )}
      </div>
      {filtered.length === 0 ? (
        <p className="history-empty">暂无历史提问</p>
      ) : (
        <ul className="history-list">
          {filtered.map((item) => (
            <li key={item.id} className="history-item">
              <button
                className="history-item-btn"
                onClick={() => onSelect(item.query)}
                title={item.query}
              >
                <div className="history-content">
                  <span className="history-query">{item.query}</span>
                  {item.dataset_name && (
                    <span className="history-dataset-tag" title={`数据集: ${item.dataset_name}`}>
                      📁 {item.dataset_name}
                    </span>
                  )}
                </div>
                <span className="history-time" title={new Date(item.created_at).toLocaleString('zh-CN')}>
                  {formatHistoryTime(item.created_at)}
                </span>
              </button>
              {onDelete && (
                <button
                  className="history-delete-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDelete(item.id);
                  }}
                  title="删除这条"
                  aria-label="删除历史项"
                >
                  ×
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
