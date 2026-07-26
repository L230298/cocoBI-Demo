// 历史记录面板 - 显示用户的提问历史
import type { DatasetInfo } from '../types';

export interface HistoryItem {
  id: string;
  query: string;
  dataset_id: string;
  created_at: string;
}

interface Props {
  items: HistoryItem[];
  activeDataset?: DatasetInfo | null;
  onSelect: (query: string) => void;
  onClear: () => void;
}

export function HistoryPanel({ items, activeDataset, onSelect, onClear }: Props) {
  const filtered = activeDataset
    ? items.filter((item) => item.dataset_id === activeDataset.dataset_id)
    : items;

  return (
    <div className="history-panel">
      <div className="history-header">
        <h4>🕘 历史记录</h4>
        {filtered.length > 0 && (
          <button className="history-clear-btn" onClick={onClear} title="清空历史">
            清空
          </button>
        )}
      </div>
      {filtered.length === 0 ? (
        <p className="history-empty">暂无历史提问</p>
      ) : (
        <ul className="history-list">
          {filtered.slice(0, 10).map((item) => (
            <li key={item.id} className="history-item">
              <button
                className="history-item-btn"
                onClick={() => onSelect(item.query)}
                title={item.query}
              >
                <span className="history-query">{item.query}</span>
                <span className="history-time">
                  {new Date(item.created_at).toLocaleTimeString('zh-CN', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
