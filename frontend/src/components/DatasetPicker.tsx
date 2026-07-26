// 数据集选择
import type { DatasetInfo } from '../types';

interface Props {
  datasets: DatasetInfo[];
  active: DatasetInfo | null;
  onSelect: (ds: DatasetInfo) => void;
  uploading: boolean;
}

export function DatasetPicker({ datasets = [], active, onSelect, uploading }: Props) {
  return (
    <div className="dataset-picker">
      <label className="dataset-label">📂 数据集</label>
      <div className="dataset-row">
        <select
          value={active?.dataset_id || ''}
          onChange={(e) => {
            const ds = datasets.find((d) => d.dataset_id === e.target.value);
            if (ds) onSelect(ds);
          }}
          disabled={uploading}
        >
          {datasets.length === 0 && <option value="">暂无数据集,点 + 上传</option>}
          {datasets.map((ds) => (
            <option key={ds.dataset_id} value={ds.dataset_id}>
              {ds.name} ({ds.row_count} 行)
            </option>
          ))}
        </select>
      </div>

      {active && (
        <details className="dataset-info">
          <summary>查看 Schema</summary>
          <table className="schema-table">
            <thead>
              <tr><th>字段</th><th>类型</th><th>示例</th></tr>
            </thead>
            <tbody>
              {(active.fields || []).map((f) => (
                <tr key={f.name}>
                  <td>{f.name}</td>
                  <td><code>{f.type}</code></td>
                  <td>{String(f.sample ?? '')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </div>
  );
}
