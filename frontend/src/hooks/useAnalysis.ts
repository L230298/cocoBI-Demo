// 核心 hook - 编排整个对话流程
import { useState, useCallback, useRef } from 'react';
import { api } from '../api/client';
import type { AppState, DataStory, DatasetInfo, IntentResult } from '../types';
import type { HistoryItem } from '../components/HistoryPanel';

const SESSION_ID = `session-${Date.now()}`;

export interface AnalysisState {
  appState: AppState;
  statusMessage: string;
  intent?: IntentResult;
  sql?: string;
  sqlExplanation?: string;
  sqlRows?: any[];
  story?: DataStory;
  observations: any[];
  nextSteps: any[];
  followups: any[];
  errorMessage?: string;
  fallbackMessage?: string;
}

const INITIAL: AnalysisState = {
  appState: 'idle',
  statusMessage: '',
  observations: [],
  nextSteps: [],
  followups: [],
};

export function useAnalysis() {
  const [state, setState] = useState<AnalysisState>(INITIAL);
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [activeDataset, setActiveDataset] = useState<DatasetInfo | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const refreshDatasets = useCallback(async () => {
    try {
      const res = await api.listDatasets();
      setDatasets(res.data);
      if (res.data.length > 0 && !activeDataset) {
        setActiveDataset(res.data[0]);
      }
    } catch (e) {
      console.error('Failed to load datasets:', e);
    }
  }, [activeDataset]);

  const uploadFile = useCallback(
    async (file: File, name: string) => {
      setState((s) => ({ ...s, appState: 'uploading', statusMessage: '正在上传文件...' }));
      try {
        const ds = await api.uploadDataset(file, name);
        await refreshDatasets();
        setActiveDataset(ds);
        setState({ ...INITIAL });
      } catch (e: any) {
        setState({
          ...INITIAL,
          appState: 'abnormal',
          errorMessage: e.message || '上传失败',
        });
      }
    },
    [refreshDatasets]
  );

  const submitQuery = useCallback(
    async (userInput: string) => {
      if (!activeDataset) {
        setState((s) => ({
          ...s,
          appState: 'abnormal',
          errorMessage: '请先上传或选择数据集',
        }));
        return;
      }

      // 记录历史
      const newItem: HistoryItem = {
        id: `h-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        query: userInput,
        dataset_id: activeDataset.dataset_id,
        created_at: new Date().toISOString(),
      };
      setHistory((prev) => [newItem, ...prev].slice(0, 50));

      // 重置 + 进入请求中
      setState({
        ...INITIAL,
        appState: 'requesting',
        statusMessage: '正在理解您的问题...',
      });

      // 多轮对话:把最近 3 条历史(去掉当前)传给后端
      const prevHistory = history
        .filter((h) => h.query !== userInput)
        .slice(0, 3)
        .map((h) => ({
          query: h.query,
          intent: 'inherited',  // 后端不需要
          slots: { 时间范围: undefined },
          dataset_id: h.dataset_id,
        }));

      try {
        for await (const event of api.chat(
          userInput,
          activeDataset.dataset_id,
          SESSION_ID,
          prevHistory
        )) {
          switch (event.event) {
            case 'state_change':
              setState((s) => ({
                ...s,
                appState: (event.state as AppState) || s.appState,
                statusMessage: event.message || s.statusMessage,
              }));
              break;
            case 'intent':
              setState((s) => ({ ...s, intent: event.data }));
              // 后端给这条 query 生成了 id,用它替换本地临时 id
              // 这样报告端点能匹配上 (record_query 返回的 id)
              if (event.query_id) {
                setHistory((prev) => {
                  if (prev.length === 0) return prev;
                  const next = [...prev];
                  next[0] = { ...next[0], id: event.query_id as string };
                  return next;
                });
              }
              break;
            case 'schema':
              break;
            case 'sql':
              setState((s) => ({ ...s, sql: event.data?.sql, sqlExplanation: event.data?.explanation }));
              break;
            case 'sql_result':
              setState((s) => ({ ...s, sqlRows: event.data?.rows || [] }));
              break;
            case 'observation':
              setState((s) => ({ ...s, observations: [...s.observations, event.data] }));
              break;
            case 'next_step':
              setState((s) => ({ ...s, nextSteps: [...s.nextSteps, event.data] }));
              break;
            case 'followup':
              setState((s) => ({ ...s, followups: [...s.followups, event.data] }));
              break;
            case 'complete':
              setState((s) => ({
                ...s,
                appState: 'completed',
                statusMessage: '分析完成',
                story: event.data as DataStory,
              }));
              break;
            case 'fallback':
              setState((s) => ({
                ...s,
                appState: 'abnormal',
                fallbackMessage: event.message,
              }));
              return;
            case 'error':
              setState((s) => ({
                ...s,
                appState: 'abnormal',
                errorMessage: event.message,
              }));
              return;
          }
        }
      } catch (e: any) {
        setState((s) => ({
          ...s,
          appState: 'abnormal',
          errorMessage: e.message || '网络错误',
        }));
      }
    },
    [activeDataset]
  );

  const reset = useCallback(() => {
    setState(INITIAL);
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
  }, []);

  const editSql = useCallback(
    async (newSql: string) => {
      if (!activeDataset) return { ok: false, error: '请先选择数据集' };
      try {
        const r = await api.editSql(newSql, activeDataset.dataset_id);
        if (r.ok) {
          // 重新执行成功,更新 sql 和 sqlRows
          setState((s) => ({ ...s, sql: newSql, sqlRows: r.rows }));
        }
        return { ok: r.ok, error: r.error };
      } catch (e: any) {
        return { ok: false, error: e.message };
      }
    },
    [activeDataset]
  );

  const generateReport = useCallback(async (queryIds?: string[]) => {
    if (!activeDataset) return;
    const ids = queryIds && queryIds.length > 0
      ? queryIds
      : history.slice(0, 50).map((h) => h.id);
    if (ids.length === 0) {
      alert('没有可生成报告的 query');
      return;
    }
    try {
      const blob = await api.generateReport(ids, activeDataset.dataset_id, 'docx');
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `数据分析报告-${new Date().toISOString().slice(0, 10)}.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      alert('生成失败: ' + e.message);
    }
  }, [activeDataset, history]);

  const submitFeedback = useCallback(async (feedback_type: 'up' | 'down') => {
    if (!state.story) return;
    try {
      await api.feedback({
        query_id: state.story.story_id,
        feedback_type,
      });
    } catch (e) {
      console.error('Feedback failed:', e);
    }
  }, [state.story]);

  return {
    state,
    datasets,
    activeDataset,
    setActiveDataset,
    refreshDatasets,
    uploadFile,
    submitQuery,
    submitFeedback,
    reset,
    history,
    clearHistory,
    editSql,
    generateReport,
  };
}
