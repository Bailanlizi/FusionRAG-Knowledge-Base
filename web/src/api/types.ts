export interface KbStats {
  document_count: number;
  chunk_count: number;
  last_updated_at: string | null;
}

export interface DocumentItem {
  doc_id: string;
  file_name: string;
  file_path: string;
  source_type: string;
  chunk_count: number;
  page_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: DocumentItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface ChunkItem {
  chunk_id: string;
  doc_id: string;
  title_path: string;
  page: number;
  chunk_type: string;
  content: string;
  token_count: number;
}

export interface ChunkDetail {
  chunk_id: string;
  doc_id: string;
  file_name: string;
  file_path: string;
  title_path: string;
  page: number;
  chunk_type: string;
  content: string;
}

export interface SourceItem {
  index: number;
  chunk_id: string;
  doc_id: string;
  file_name: string;
  file_path: string;
  title_path: string;
  page: number;
  score?: number | null;
}

export interface TraceInfo {
  complexity: string;
  queries: string[];
  original_question?: string;
  standalone_query?: string;
  is_follow_up?: boolean;
  rewrite_ms?: number;
  retrieval_ms: number;
  rerank_ms: number;
  llm_ms: number;
  chunk_count: number;
}

export interface MessageItem {
  id: string;
  role: string;
  content: string;
  sources: SourceItem[];
  trace?: TraceInfo | null;
  created_at: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: MessageItem[];
}

export interface AssistantMessageResponse {
  message_id: string;
  role: string;
  content: string;
  sources: SourceItem[];
  trace: TraceInfo;
  user_message_id?: string | null;
}
