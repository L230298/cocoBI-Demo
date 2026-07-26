// 状态机实现 - PRD §3.4.6
import type { AppState } from '../types';

export interface StateDefinition {
  uiView: 'chat' | 'loading' | 'skeleton' | 'result' | 'error';
  allowedTransitions: AppState[];
  message: string;
}

export const STATE_MACHINE: Record<AppState, StateDefinition> = {
  idle: {
    uiView: 'chat',
    allowedTransitions: ['uploading', 'requesting', 'abnormal'],
    message: '',
  },
  uploading: {
    uiView: 'loading',
    allowedTransitions: ['validating', 'abnormal'],
    message: '正在上传文件...',
  },
  validating: {
    uiView: 'loading',
    allowedTransitions: ['idle', 'abnormal'],
    message: '正在校验数据...',
  },
  requesting: {
    uiView: 'skeleton',
    allowedTransitions: ['receiving', 'generating', 'abnormal'],
    message: '正在理解您的问题...',
  },
  receiving: {
    uiView: 'skeleton',
    allowedTransitions: ['generating', 'abnormal'],
    message: '正在映射数据表...',
  },
  generating: {
    uiView: 'skeleton',
    allowedTransitions: ['completed', 'abnormal'],
    message: '正在生成分析...',
  },
  completed: {
    uiView: 'result',
    allowedTransitions: ['idle', 'requesting', 'exporting'],
    message: '分析完成',
  },
  exporting: {
    uiView: 'loading',
    allowedTransitions: ['completed', 'abnormal'],
    message: '正在导出...',
  },
  abnormal: {
    uiView: 'error',
    allowedTransitions: ['idle', 'requesting'],
    message: '出错了',
  },
};

export function canTransition(from: AppState, to: AppState): boolean {
  return STATE_MACHINE[from].allowedTransitions.includes(to);
}
