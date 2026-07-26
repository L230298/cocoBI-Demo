// 错误展示 - PRD §3.4.7
interface Props {
  errorMessage?: string;
  fallbackMessage?: string;
  onRetry?: () => void;
}

export function ErrorDisplay({ errorMessage, fallbackMessage, onRetry }: Props) {
  return (
    <div className="error-display">
      <div className="error-icon">⚠️</div>
      <p className="error-message">{fallbackMessage || errorMessage || '出错了'}</p>
      {onRetry && (
        <button className="action-btn primary" onClick={onRetry}>
          再试一次
        </button>
      )}
    </div>
  );
}
