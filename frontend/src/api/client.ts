// API 客户端封装
import type { DatasetInfo, SSEEvent, FeedbackPayload } from '../types';

// API 基础地址:
// - 开发:`/api`(配合 Vite proxy)
// - 生产:从 VITE_API_BASE_URL 读取,例如 `https://cocobi-backend.onrender.com`
const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || '/api';
const ABSOLUTE_BASE = BASE_URL.startsWith('http');

async function jsonFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
  });
  if (!res.ok) {
    throw new Error(await extractErrorMessage(res));
  }
  return res.json();
}

async function extractErrorMessage(res: Response): Promise<string> {
  // 尝试从 JSON 响应提取错误信息,兼容多种后端格式
  try {
    const text = await res.text();
    if (!text) return `HTTP ${res.status} ${res.statusText}`;
    try {
      const data = JSON.parse(text);
      return (
        data.detail?.error_msg ||
        data.detail?.message ||
        data.error_msg ||
        data.message ||
        text ||
        `HTTP ${res.status}`
      );
    } catch {
      return text || `HTTP ${res.status} ${res.statusText}`;
    }
  } catch {
    return `HTTP ${res.status} ${res.statusText}`;
  }
}

export const api = {
  // 数据集
  listDatasets: () => jsonFetch<{ success: boolean; data: DatasetInfo[] }>('/dataset/list'),
  uploadDataset: async (file: File, name: string, industryTemplate = '通用', dryRun = false): Promise<DatasetInfo> => {
    const form = new FormData();
    form.append('file', file);
    form.append('dataset_name', name);
    form.append('industry_template', industryTemplate);
    if (dryRun) form.append('dry_run', 'true');
    const res = await fetch(`${BASE_URL}/dataset/upload`, { method: 'POST', body: form });
    if (!res.ok) {
      throw new Error(await extractErrorMessage(res));
    }
    const json = await res.json();
    return json.data;
  },
  deleteDataset: (id: string) => jsonFetch<{ success: boolean }>(`/dataset/${id}`, { method: 'DELETE' }),

  // SQL 编辑 - 用户修改后重新执行
  editSql: async (sql: string, datasetId: string): Promise<{
    ok: boolean; error?: string; rows?: any[]; columns?: string[]; row_count?: number;
  }> => {
    try {
      const res = await fetch(`${BASE_URL}/sql/edit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sql, dataset_id: datasetId }),
      });
      if (!res.ok) {
        const err = await extractErrorMessage(res);
        return { ok: false, error: err };
      }
      const json = await res.json();
      return {
        ok: true,
        rows: json.rows || [],
        columns: json.columns || [],
        row_count: json.row_count || 0,
      };
    } catch (e: any) {
      return { ok: false, error: e.message };
    }
  },

  // 生成数据报告(单 query 或多 query)
  generateReport: async (
    queryIds: string[],
    datasetId: string,
    format: 'json' | 'markdown' | 'docx' = 'docx'
  ): Promise<any> => {
    const res = await fetch(`${BASE_URL}/report/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query_ids: queryIds, dataset_id: datasetId, format }),
    });
    if (!res.ok) {
      throw new Error(await extractErrorMessage(res));
    }
    // docx 是二进制, 其他是 JSON
    if (format === 'docx') {
      return await res.blob();
    }
    return res.json();
  },

  // 对话 - 流式 NDJSON
  chat: async function* (
    userInput: string,
    datasetId: string,
    sessionId: string,
    conversationHistory: Array<{intent: string; slots: Record<string, unknown>; dataset_id?: string}> = []
  ): AsyncGenerator<SSEEvent> {
    const res = await fetch(`${BASE_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_input: userInput,
        dataset_id: datasetId,
        session_id: sessionId,
        conversation_history: conversationHistory,
      }),
    });
    if (!res.ok || !res.body) {
      yield { event: 'error', message: '服务连接失败' };
      return;
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          yield JSON.parse(line) as SSEEvent;
        } catch {
          console.warn('Failed to parse SSE line:', line);
        }
      }
    }
  },

  // 反馈
  feedback: (payload: FeedbackPayload) =>
    jsonFetch<{ success: boolean; feedback_id: string }>('/feedback', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // 工具列表(调试)
  listTools: () => jsonFetch<{ success: boolean; data: any[] }>('/tools'),
};

// 在生产环境方便调试 —— 暴露 BASE_URL 到 window
if (ABSOLUTE_BASE && typeof window !== 'undefined') {
  (window as any).__API_BASE__ = BASE_URL;
}
