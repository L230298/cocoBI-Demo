// 数据故事卡片 - PRD §3.5.2.2
import { useState } from 'react';
import type { DataStory } from '../types';
import { ChartRenderer } from './ChartRenderer';
import { Copy, RotateCcw, ThumbsUp, ThumbsDown, Share2, Edit3, FileText } from 'lucide-react';
import { EditSqlModal } from './EditSqlModal';
import { GenerateReportModal } from './GenerateReportModal';
import { FeedbackModal } from './FeedbackModal';

interface Props {
  story: DataStory;
  observations: any[];
  nextSteps: any[];
  followups: any[];
  sql?: string;
  sqlRows?: any[];
  datasetId?: string;
  onFollowupClick: (text: string) => void;
  onCopy: () => void;
  onShare: () => void;
  onReset: () => void;
  onFeedback: (type: 'up' | 'down', extra?: { comment?: string; tags?: string[] }) => void;
  onSqlEdited?: (newSql: string) => Promise<{ ok: boolean; error?: string }>;
  onGenerateReport?: () => Promise<void>;
}

export function StoryCard({
  story,
  observations,
  nextSteps,
  followups,
  sql,
  sqlRows,
  datasetId,
  onFollowupClick,
  onCopy,
  onShare,
  onReset,
  onFeedback,
  onSqlEdited,
  onGenerateReport,
}: Props) {
  const [editOpen, setEditOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [voted, setVoted] = useState<'up' | 'down' | null>(null);
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

      {/* PRD 简化:可关注观察点 与 下一步建议 不在前端页面展示,仅在数据洞察报告(复制文案 / 分享链接)中出现 */}

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
            <div className="sql-actions">
              {onSqlEdited && (
                <button
                  className="sql-action-btn"
                  onClick={(e) => { e.preventDefault(); setEditOpen(true); }}
                  title="编辑 SQL 并重新执行"
                  aria-label="编辑 SQL"
                >
                  <Edit3 size={14} /> 编辑
                </button>
              )}
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
          </div>
          <pre><code>{sql}</code></pre>
        </details>
      )}

      {onGenerateReport && (
        <div className="story-section generate-report-section">
          <button
            className="action-btn primary"
            onClick={() => setReportOpen(true)}
          >
            <FileText size={14} /> 生成数据分析报告
          </button>
        </div>
      )}

      <footer className="story-actions">
        <button
          className="action-icon-btn primary"
          onClick={onCopy}
          title="一键复制洞察"
          aria-label="一键复制洞察"
        >
          <Copy size={16} strokeWidth={1.8} />
        </button>
        <button
          className="action-icon-btn"
          onClick={onReset}
          title="再问一个"
          aria-label="再问一个"
        >
          <RotateCcw size={16} strokeWidth={1.8} />
        </button>
        <button
          className={`action-icon-btn${voted === 'up' ? ' voted' : ''}`}
          onClick={() => {
            if (voted) return;
            setVoted('up');
            onFeedback('up');
          }}
          disabled={voted !== null}
          title={voted === 'up' ? '已点赞' : '有用'}
          aria-label="有用"
        >
          <ThumbsUp size={16} strokeWidth={voted === 'up' ? 2.5 : 1.8} fill={voted === 'up' ? 'currentColor' : 'none'} />
        </button>
        <button
          className={`action-icon-btn${voted === 'down' ? ' voted' : ''}`}
          onClick={() => {
            if (voted) return;
            // 先开反馈弹窗, 用户提交后才算 voted
            setFeedbackOpen(true);
          }}
          title={voted === 'down' ? '已反馈' : '没用'}
          aria-label="没用"
        >
          <ThumbsDown size={16} strokeWidth={voted === 'down' ? 2.5 : 1.8} fill={voted === 'down' ? 'currentColor' : 'none'} />
        </button>
        <button
          className="action-icon-btn"
          onClick={onShare}
          title="生成分享链接"
          aria-label="生成分享链接"
        >
          <Share2 size={16} strokeWidth={1.8} />
        </button>
      </footer>

      {/* Modals */}
      {sql && onSqlEdited && editOpen && (
        <EditSqlModal
          initialSql={sql}
          onCancel={() => setEditOpen(false)}
          onSave={async (newSql) => {
            const r = await onSqlEdited(newSql);
            if (r.ok) setEditOpen(false);
            return r;
          }}
        />
      )}
      {onGenerateReport && reportOpen && (
        <GenerateReportModal
          mode="single"
          onCancel={() => setReportOpen(false)}
          onConfirm={async () => {
            await onGenerateReport();
            setReportOpen(false);
          }}
        />
      )}
      {feedbackOpen && (
        <FeedbackModal
          onCancel={() => setFeedbackOpen(false)}
          onSubmit={async (data) => {
            setVoted('down');
            onFeedback('down', data);
            setFeedbackOpen(false);
          }}
        />
      )}
    </div>
  );
}
