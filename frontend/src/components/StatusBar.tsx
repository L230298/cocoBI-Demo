// 状态指示器 - PRD §3.4.6
interface Props {
  state: string;
  message: string;
}

const STATE_LABELS: Record<string, string> = {
  idle: '就绪',
  uploading: '上传中',
  validating: '校验中',
  requesting: '请求中',
  receiving: '接收中',
  generating: '生成中',
  completed: '已完成',
  exporting: '导出中',
  abnormal: '异常',
};

export function StatusBar({ state, message }: Props) {
  const isLoading = ['uploading', 'validating', 'requesting', 'receiving', 'generating', 'exporting'].includes(state);
  return (
    <div className={`status-bar state-${state}`}>
      {isLoading && <span className="spinner" />}
      <span className="status-label">{STATE_LABELS[state] || state}</span>
      {message && <span className="status-message">{message}</span>}
    </div>
  );
}
