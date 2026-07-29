import { useEffect, useState, useRef } from 'react';
import { useAnalysis } from './hooks/useAnalysis';
import { ChatInput } from './components/ChatInput';
import { StoryCard } from './components/StoryCard';
import { StatusBar } from './components/StatusBar';
import { ErrorDisplay } from './components/ErrorDisplay';
import { Skeleton } from './components/Skeleton';
import { HistoryPanel } from './components/HistoryPanel';
import { UploadConfirmModal } from './components/UploadConfirmModal';
import { ReportPreviewModal } from './components/ReportPreviewModal';
import { STATE_MACHINE } from './utils/stateMachine';

// 移到欢迎区的示例问题
const SAMPLE_QUERIES = [
  '上周 GMV 是多少?',
  '最近什么卖得好?TOP 10',
  '为什么这个月订单掉了?',
  '库存低于 100 的 SKU 有哪些?',
  '近 30 天 GMV 趋势',
];

function App() {
  const {
    state,
    activeDataset,
    refreshDatasets,
    uploadFile,
    submitQuery,
    submitFeedback,
    reset,
    history,
    clearHistory,
    editSql,
    generateReport,
    downloadReport,
  } = useAnalysis();

  useEffect(() => {
    refreshDatasets();
  }, []);

  // 文件上传确认弹窗
  const [pendingUpload, setPendingUpload] = useState<{
    file: File;
    name: string;
    preview: any;
  } | null>(null);

  const handleUpload = async (file: File, name: string) => {
    uploadFile(file, name, async (preview) => {
      // 把文件暂存, 显示确认弹窗
      setPendingUpload({ file, name, preview });
      // 返回 Promise, 用户点确认才 resolve
      return new Promise<boolean>((resolve) => {
        pendingUploadRef.current = { resolve };
      });
    });
  };

  // 用 ref 持有 resolve 回调, 因为 setState 后闭包会变
  const pendingUploadRef = useRef<{ resolve: (ok: boolean) => void } | null>(null);

  // 报告预览弹窗 state
  const [reportPreviewIds, setReportPreviewIds] = useState<string[] | null>(null);

  const handleUploadConfirm = async () => {
    if (pendingUploadRef.current) {
      pendingUploadRef.current.resolve(true);
    }
    setPendingUpload(null);
  };

  const handleUploadCancel = () => {
    if (pendingUploadRef.current) {
      pendingUploadRef.current.resolve(false);
    }
    setPendingUpload(null);
  };

  // URL 参数 ?q=xxx 自动填入 + 自动提交
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const q = params.get('q');
    if (q && state.appState === 'idle') {
      // 短暂延迟确保 UI 渲染好
      setTimeout(() => {
        submitQuery(q);
        // 清理 URL 参数(避免重复触发)
        window.history.replaceState({}, '', window.location.pathname);
      }, 500);
    }
  }, [state.appState]);

  const def = STATE_MACHINE[state.appState];
  const isLoading = def.uiView === 'loading' || def.uiView === 'skeleton';

  const handleCopy = async () => {
    if (!state.story) return;
    try {
      await navigator.clipboard.writeText(state.story.copy_insight_text);
      alert('已复制到剪贴板,可粘贴到 IM/邮件');
    } catch {
      alert('复制失败,请手动选择');
    }
  };

  const handleShare = () => {
    if (!state.story?.share_url) {
      alert('分享链接生成失败');
      return;
    }
    const url = `${window.location.origin}${state.story.share_url}`;
    // 1) 尝试复制到剪贴板(失败也不阻塞)
    let copied = false;
    if (navigator.clipboard?.writeText) {
      navigator.clipboard
        .writeText(url)
        .then(() => { copied = true; })
        .catch(() => { copied = false; });
    }
    // 2) 打开新窗口(可能被 popup blocker 拦, 后面有 fallback)
    const popup = window.open(url, '_blank');
    // 3) 兜底: 如果 popup 被拦, 用 prompt 让用户手动复制
    setTimeout(() => {
      if (!popup || popup.closed) {
        const userCopy = window.prompt(
          `分享链接(已自动复制失败,请手动复制):\n${url}`,
          url
        );
        if (userCopy !== null) {
          // 用户点了确定, 说明已经复制
        }
      } else {
        alert(
          copied
            ? '分享链接已复制 + 已在新窗口打开'
            : '已在新窗口打开分享页面(链接复制失败,请手动从地址栏复制)'
        );
      }
    }, 300);
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="logo">
          <span className="logo-icon">🌟</span>
          <h1>cocoBI</h1>
          <span className="tagline">AI 数据分析助手</span>
        </div>
        <span className="version">v1.0.1 Demo</span>
      </header>

      <div className="app-body">
        <aside className="sidebar">
          <button
            className="new-session-btn"
            onClick={reset}
            title="开始新会话"
          >
            <span className="new-session-icon">+</span>
            <span>新建会话</span>
          </button>
          <HistoryPanel
            items={history}
            activeDataset={activeDataset}
            onSelect={(q) => submitQuery(q)}
            onClear={clearHistory}
          />
        </aside>

        <main className="main-content">
          <div className="main-toolbar">
            <StatusBar state={state.appState} message={state.statusMessage} />
          </div>

          {state.intent && state.appState !== 'completed' && (
            <div className="intent-badge">
              <span className="intent-name">{state.intent.intent}</span>
              <span className="intent-confidence">
                置信度 {(state.intent.confidence * 100).toFixed(0)}%
              </span>
            </div>
          )}

          {def.uiView === 'chat' && (
            <div className="welcome">
              <h2>👋 你好,我是 cocoBI</h2>
              <p>用自然语言提问,30 秒内获得可分享的数据洞察。</p>
              <p className="welcome-hint">— 不写 SQL,不配报表,问题直达答案 —</p>
              <div className="welcome-samples">
                <span className="welcome-samples-hint">💡 试试这样问:</span>
                <div className="welcome-samples-chips">
                  {SAMPLE_QUERIES.map((q) => (
                    <button
                      key={q}
                      className="welcome-chip"
                      onClick={() => submitQuery(q)}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {def.uiView === 'skeleton' && <Skeleton />}

          {state.appState === 'abnormal' && (
            <ErrorDisplay
              errorMessage={state.errorMessage}
              fallbackMessage={state.fallbackMessage}
              onRetry={reset}
            />
          )}

          {def.uiView === 'result' && state.story && (
            <StoryCard
              story={state.story}
              observations={state.observations}
              nextSteps={state.nextSteps}
              followups={state.followups}
              sql={state.sql}
              sqlRows={state.sqlRows}
              onFollowupClick={(text) => submitQuery(text)}
              onCopy={handleCopy}
              onShare={handleShare}
              onReset={reset}
              onFeedback={submitFeedback}
              onSqlEdited={editSql}
              onGenerateReport={async () => generateReport()}
              onReportPreview={setReportPreviewIds}
            />
          )}
        </main>
      </div>

      <footer className="chat-footer">
        <ChatInput
          onSubmit={submitQuery}
          onUpload={handleUpload}
          disabled={isLoading || state.appState === 'uploading'}
        />
      </footer>

      {/* 文件上传确认弹窗 */}
      {pendingUpload && (
        <UploadConfirmModal
          fileName={pendingUpload.file.name}
          sheetName={pendingUpload.preview.sheet_name || '工作表 1'}
          rowCount={pendingUpload.preview.row_count || 0}
          columnCount={pendingUpload.preview.column_count || 0}
          onCancel={handleUploadCancel}
          onConfirm={handleUploadConfirm}
        />
      )}

      {/* 数据分析报告预览弹窗 (浏览器内直接显示, 不再自动下载) */}
      {reportPreviewIds && activeDataset && (
        <ReportPreviewModal
          queryIds={reportPreviewIds}
          datasetId={activeDataset.dataset_id}
          onClose={() => setReportPreviewIds(null)}
          onDownload={async () => downloadReport(reportPreviewIds)}
        />
      )}
    </div>
  );
}

export default App;
