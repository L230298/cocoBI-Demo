// TypeScript 类型 - 对应后端 Pydantic schemas

// ==================== 意图 ====================
export type IntentName =
  | 'QueryBasicMetrics'
  | 'QueryCompareAndTopN'
  | 'ThresholdAlert'
  | 'AttributeAnalysis'
  | 'SmartInterpretation'
  | 'Unknown';

export interface IntentResult {
  intent: IntentName;
  confidence: number;
  slots: Record<string, any>;
  alternatives: IntentName[];
  fallback_message?: string;
}

// ==================== 状态机 (PRD §3.4.6) ====================
export type AppState =
  | 'idle'
  | 'uploading'
  | 'validating'
  | 'requesting'
  | 'receiving'
  | 'generating'
  | 'completed'
  | 'exporting'
  | 'abnormal';

// ==================== 数据故事 ====================
export interface ChartConfig {
  chart_type: 'bar' | 'line' | 'pie' | 'funnel' | 'table';
  config?: any;
  title?: string;
}

export interface Observation {
  text: string;
  severity: 'info' | 'warning' | 'success';
}

export interface NextStep {
  text: string;
  type: 'compare' | 'drill' | 'share' | 'export' | 'explore';
}

export interface FollowupQuestion {
  text: string;
  intent_hint?: IntentName;
}

export interface DataStory {
  story_id: string;
  title: string;
  summary: string | string[];
  sections: Array<{ id: number; title: string; description: string }>;
  charts: ChartConfig[];
  observations: Observation[];
  next_steps: NextStep[];
  recommended_followups: FollowupQuestion[];
  copy_insight_text: string;
  share_url?: string;
  confidence_overall: number;
}

// ==================== SSE 事件 ====================
export type SSEEventType =
  | 'state_change'
  | 'intent'
  | 'schema'
  | 'sql'
  | 'sql_result'
  | 'chart'
  | 'story_chunk'
  | 'observation'
  | 'next_step'
  | 'followup'
  | 'complete'
  | 'error'
  | 'fallback';

export interface SSEEvent {
  event: SSEEventType;
  state?: AppState;
  data?: any;
  message?: string;
  query_id?: string;  // 后端给每条 query 生成的 ID(报告功能用)
}

// ==================== 数据集 ====================
export interface DatasetInfo {
  dataset_id: string;
  name: string;
  industry_template: string;
  row_count: number;
  column_count: number;
  size_bytes: number;
  fields: Array<{ name: string; type: string; sample: any }>;
  business_glossary: Record<string, string>;
  uploaded_at: string;
}

// ==================== 反馈 ====================
export interface FeedbackPayload {
  query_id: string;
  feedback_type: 'up' | 'down' | 'correction';
  comment?: string;
}
