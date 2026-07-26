// 数据故事卡片 - PRD §3.5.2.2
import type { DataStory } from '../types';
import { ChartRenderer } from './ChartRenderer';

interface Props {
  story: DataStory;
  observations: any[];
  nextSteps: any[];
  followups: any[];
  sql?: string;
  sqlRows?: any[];
  onFollowupClick: (text: string) => void;
  onCopy: () => void;
  onShare: () => void;
  onReset: () => void;
  onFeedback: (type: 'up' | 'down') => void;
}

export function StoryCard({
  story,
  observations,
  nextSteps,
  followups,
  sql,
  sqlRows,
  onFollowupClick,
  onCopy,
  onShare,
  onReset,
  onFeedback,
}: Props) {
  return (
    <div className="story-card">
      <header className="story-header">
        <h2>{story.title}</h2>
        <p className="story-summary">{Array.isArray(story.summary) ? story.summary[0] : story.summary}</p>
      </header>

      {story.charts?.length > 0 && (
        <section className="story-section">
          <h3>📊 数据可视化</h3>
          {story.charts.map((chart, i) => (
            <ChartRenderer key={i} chartConfig={chart} />
          ))}
        </section>
      )}

      {sqlRows && sqlRows.length > 0 && (
        <section className="story-section">
          <h3>📋 数据明细 ({sqlRows.length} 行)</h3>
          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>{Object.keys(sqlRows[0]).map((k) => <th key={k}>{k}</th>)}</tr>
              </thead>
              <tbody>
                {sqlRows.slice(0, 20).map((row, i) => (
                  <tr key={i}>
                    {Object.values(row).map((v: any, j) => (
                      <td key={j}>{typeof v === 'number' ? v.toLocaleString() : String(v)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {observations.length > 0 && (
        <section className="story-section">
          <h3>💡 可关注观察点</h3>
          <ul className="observation-list">
            {observations.map((o, i) => (
              <li key={i} className={`observation severity-${o.severity}`}>
                <span className="severity-dot" />
                {o.text}
              </li>
            ))}
          </ul>
        </section>
      )}

      {nextSteps.length > 0 && (
        <section className="story-section">
          <h3>🎯 下一步建议</h3>
          <ul className="next-step-list">
            {nextSteps.map((s, i) => (
              <li key={i} className={`next-step type-${s.type}`}>
                <span className="next-step-type">{s.type}</span>
                {s.text}
              </li>
            ))}
          </ul>
        </section>
      )}

      {followups.length > 0 && (
        <section className="story-section">
          <h3>🔍 推荐追问</h3>
          <div className="followup-chips">
            {followups.map((f, i) => (
              <button key={i} className="followup-chip" onClick={() => onFollowupClick(f.text)}>
                {f.text}
              </button>
            ))}
          </div>
        </section>
      )}

      {sql && (
        <details className="story-section sql-detail">
          <summary>🔧 查看生成的 SQL</summary>
          <div className="sql-header">
            <span className="sql-hint">💡 复制时为纯文本,无富文本格式</span>
            <button
              className="sql-copy-btn"
              onClick={() => {
                navigator.clipboard?.writeText(sql).then(
                  () => {
                    const btn = document.activeElement as HTMLButtonElement;
                    if (btn) {
                      const orig = btn.textContent;
                      btn.textContent = '✓ 已复制';
                      setTimeout(() => { btn.textContent = orig; }, 1500);
                    }
                  },
                  () => alert('复制失败,请手动选择')
                );
              }}
            >
              📋 复制 SQL
            </button>
          </div>
          <pre><code>{sql}</code></pre>
        </details>
      )}

      <footer className="story-actions">
        <button className="action-btn primary" onClick={onCopy}>📋 一键复制洞察</button>
        <button className="action-btn" onClick={onShare}>🔗 生成分享链接</button>
        <button className="action-btn" onClick={() => onFeedback('up')}>👍 有用</button>
        <button className="action-btn" onClick={() => onFeedback('down')}>👎 没用</button>
        <button className="action-btn" onClick={onReset}>↻ 再问一个</button>
      </footer>
    </div>
  );
}
