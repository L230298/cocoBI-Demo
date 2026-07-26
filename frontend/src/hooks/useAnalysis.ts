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

      try {
        for await (const event of api.chat(userInput, activeDataset.dataset_id, SESSION_ID)) {
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
  };
}
