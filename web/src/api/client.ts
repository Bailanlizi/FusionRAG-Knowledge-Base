import type {
  AssistantMessageResponse,
  ChunkDetail,
  ChunkItem,
  ConversationDetail,
  ConversationSummary,
  DocumentItem,
  DocumentListResponse,
  KbStats,
} from "./types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/health"),

  kbStats: () => request<KbStats>("/kb/stats"),

  listDocuments: (params: Record<string, string>) => {
    const q = new URLSearchParams(params).toString();
    return request<DocumentListResponse>(`/documents?${q}`);
  },

  getDocument: (docId: string) => request<DocumentItem>(`/documents/${docId}`),

  listDocChunks: (docId: string) => request<ChunkItem[]>(`/documents/${docId}/chunks`),

  uploadDocument: async (file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData();
    form.append("file", file);
    return new Promise<{ doc_id: string; file_name: string; chunk_count: number; message: string }>(
      (resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", `${BASE}/documents/upload`);
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
        };
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(JSON.parse(xhr.responseText));
          } else {
            reject(new Error(xhr.responseText || xhr.statusText));
          }
        };
        xhr.onerror = () => reject(new Error("Upload failed"));
        xhr.send(form);
      }
    );
  },

  deleteDocument: (docId: string) =>
    request<void>(`/documents/${docId}`, { method: "DELETE" }),

  getChunk: (chunkId: string) => request<ChunkDetail>(`/chunks/${chunkId}`),

  listConversations: () => request<ConversationSummary[]>("/conversations"),

  createConversation: (title?: string) =>
    request<ConversationSummary>("/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    }),

  getConversation: (id: string) => request<ConversationDetail>(`/conversations/${id}`),

  deleteConversation: (id: string) =>
    request<void>(`/conversations/${id}`, { method: "DELETE" }),

  sendMessage: (convId: string, body: { content: string; regenerate?: boolean; target_message_id?: string }) =>
    request<AssistantMessageResponse>(`/conversations/${convId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
};
