// 反馈弹窗 - 用户点"踩"时弹出, 收集问题分类 + 文字说明
import { useState } from 'react';
import { X, ThumbsDown } from 'lucide-react';

const FEEDBACK_TAGS = [
  { value: 'harmful', label: '有害/不安全' },
  { value: 'misleading', label: '虚假信息' },
  { value: 'unhelpful', label: '没有帮助' },
  { value: 'other', label: '其他' },
];

interface Props {
  onCancel: () => void;
  onSubmit: (data: { tags: string[]; comment: string }) => Promise<void>;
}

export function FeedbackModal({ onCancel, onSubmit }: Props) {
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);

  const toggleTag = (v: string) => {
    setSelectedTags((prev) =>
      prev.includes(v) ? prev.filter((x) => x !== v) : [...prev, v]
    );
  };

  const handleSubmit = async () => {
    if (selectedTags.length === 0 && !comment.trim()) {
      alert('请选择至少一个分类或填写说明');
      return;
    }
    setBusy(true);
    try {
      await onSubmit({ tags: selectedTags, comment: comment.trim() });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal-content feedback-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>
            <ThumbsDown size={16} style={{ verticalAlign: 'middle', marginRight: 6 }} />
            反馈
          </h3>
          <button className="modal-close" onClick={onCancel} aria-label="关闭">
            <X size={18} />
          </button>
        </div>
        <div className="modal-body">
          <div className="feedback-tags">
            {FEEDBACK_TAGS.map((t) => (
              <button
                key={t.value}
                type="button"
                className={`feedback-tag${selectedTags.includes(t.value) ? ' selected' : ''}`}
                onClick={() => toggleTag(t.value)}
              >
                {t.label}
              </button>
            ))}
          </div>
          <textarea
            className="feedback-textarea"
            placeholder="我们想知道你对此回答不满意的原因, 你认为更好的回答是什么?"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={4}
            maxLength={500}
          />
        </div>
        <div className="modal-footer">
          <button className="action-btn" onClick={onCancel} disabled={busy}>
            取消
          </button>
          <button
            className="action-btn primary"
            onClick={handleSubmit}
            disabled={busy}
          >
            {busy ? '提交中...' : '提交'}
          </button>
        </div>
      </div>
    </div>
  );
}
