// 对话输入框 - PRD §3.5.2.1
import { useRef, useState } from 'react';

interface Props {
  onSubmit: (input: string) => void;
  onUpload: (file: File, name: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSubmit, onUpload, disabled }: Props) {
  const [value, setValue] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue('');
  };

  const handleFilePick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const name = file.name.replace(/\.(csv|xlsx|xls)$/i, '');
    onUpload(file, name);
    if (fileRef.current) fileRef.current.value = '';
  };

  return (
    <div className="chat-input-wrapper">
      <div className="chat-input">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSubmit();
            }
          }}
          placeholder="用自然语言提问,例如:上周 GMV 是多少?"
          maxLength={500}
          disabled={disabled}
          rows={2}
        />
        {/* 输入框内部右下角工具栏: + 上传 + 发送 */}
        <div className="chat-input-actions">
          <span className="char-count">{value.length} / 500</span>
          <button
            className="upload-btn"
            onClick={() => fileRef.current?.click()}
            disabled={disabled}
            title="上传 CSV / Excel"
            aria-label="上传文件"
          >
            <span className="upload-btn-icon" aria-hidden="true">+</span>
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={handleFilePick}
            style={{ display: 'none' }}
          />
          <button
            className="send-btn"
            onClick={handleSubmit}
            disabled={disabled || !value.trim()}
            aria-label="发送"
            title="发送"
          >
            {disabled ? (
              <span className="send-btn-loading">...</span>
            ) : (
              <>
                <span className="send-btn-label">发送</span>
                <span className="send-arrow" aria-hidden="true">↑</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
