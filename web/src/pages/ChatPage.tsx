import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { ConversationDetail, MessageItem } from "../api/types";
import ChunkDrawer from "../components/chat/ChunkDrawer";
import MarkdownMessage from "../components/chat/MarkdownMessage";
import SourceList from "../components/chat/SourceList";
import TracePanel from "../components/chat/TracePanel";

export default function ChatPage() {
  const qc = useQueryClient();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [chunkId, setChunkId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: conversations = [] } = useQuery({
    queryKey: ["conversations"],
    queryFn: api.listConversations,
  });

  const { data: conversation } = useQuery({
    queryKey: ["conversation", activeId],
    queryFn: () => api.getConversation(activeId!),
    enabled: !!activeId,
  });

  useEffect(() => {
    if (!activeId && conversations.length) setActiveId(conversations[0].id);
  }, [conversations, activeId]);

  const createMut = useMutation({
    mutationFn: () => api.createConversation(),
    onSuccess: (c) => {
      qc.invalidateQueries({ queryKey: ["conversations"] });
      setActiveId(c.id);
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.deleteConversation(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["conversations"] });
      setActiveId(null);
    },
  });

  const sendMut = useMutation({
    mutationFn: (payload: { content: string; regenerate?: boolean; target_message_id?: string }) =>
      api.sendMessage(activeId!, payload),
    onMutate: async (payload) => {
      const convId = activeId;
      if (!convId) return;

      await qc.cancelQueries({ queryKey: ["conversation", convId] });
      const previous = qc.getQueryData<ConversationDetail>(["conversation", convId]);

      if (!payload.regenerate && payload.content.trim()) {
        const optimisticUser: MessageItem = {
          id: `optimistic-user-${Date.now()}`,
          role: "user",
          content: payload.content.trim(),
          sources: [],
          created_at: new Date().toISOString(),
        };
        qc.setQueryData<ConversationDetail>(["conversation", convId], (old) => {
          if (!old) {
            return {
              id: convId,
              title: "新对话",
              created_at: optimisticUser.created_at,
              updated_at: optimisticUser.created_at,
              messages: [optimisticUser],
            };
          }
          return { ...old, messages: [...old.messages, optimisticUser] };
        });
      }

      return { previous, convId };
    },
    onError: (_err, _payload, context) => {
      if (context?.previous !== undefined && context.convId) {
        qc.setQueryData(["conversation", context.convId], context.previous);
      }
    },
    onSettled: (_data, _err, _payload, context) => {
      if (context?.convId) {
        qc.invalidateQueries({ queryKey: ["conversation", context.convId] });
      }
      qc.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversation?.messages, sendMut.isPending]);

  const handleSend = () => {
    if (!activeId || !input.trim() || sendMut.isPending) return;
    const content = input.trim();
    setInput("");
    sendMut.mutate({ content });
  };

  const handleRegenerate = (msg: MessageItem) => {
    if (!activeId || sendMut.isPending) return;
    sendMut.mutate({ content: "", regenerate: true, target_message_id: msg.id });
  };

  const copyText = (text: string) => navigator.clipboard.writeText(text);

  return (
    <div className="flex h-[calc(100vh-57px)]">
      <aside className="w-60 border-r border-slate-200 bg-white flex flex-col">
        <div className="p-3 border-b">
          <button
            type="button"
            onClick={() => createMut.mutate()}
            className="w-full rounded-lg bg-indigo-600 text-white text-sm py-2 hover:bg-indigo-700"
          >
            + New chat
          </button>
        </div>
        <ul className="flex-1 overflow-y-auto p-2 space-y-1">
          {conversations.map((c) => (
            <li key={c.id} className="group flex items-center gap-1">
              <button
                type="button"
                onClick={() => setActiveId(c.id)}
                className={`flex-1 text-left text-sm px-3 py-2 rounded-lg truncate ${
                  activeId === c.id ? "bg-indigo-50 text-indigo-700" : "hover:bg-slate-100"
                }`}
              >
                {c.title}
              </button>
              <button
                type="button"
                className="opacity-0 group-hover:opacity-100 text-slate-400 text-xs px-1"
                onClick={() => {
                  if (confirm("Delete this conversation?")) deleteMut.mutate(c.id);
                }}
              >
                x
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <section className="flex-1 flex flex-col min-w-0">
        {!activeId ? (
          <div className="flex-1 flex items-center justify-center text-slate-500">
            Select or create a conversation
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {conversation?.messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                      msg.role === "user"
                        ? "bg-indigo-600 text-white"
                        : "bg-white border border-slate-200 shadow-sm"
                    }`}
                  >
                    {msg.role === "user" ? (
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    ) : (
                      <>
                        <MarkdownMessage content={msg.content} />
                        <SourceList sources={msg.sources} onSelect={setChunkId} />
                        {msg.trace && <TracePanel trace={msg.trace} />}
                        <div className="mt-3 flex gap-2">
                          <button
                            type="button"
                            className="text-xs text-slate-500 hover:text-indigo-600"
                            onClick={() => copyText(msg.content)}
                          >
                            Copy
                          </button>
                          <button
                            type="button"
                            className="text-xs text-slate-500 hover:text-indigo-600"
                            onClick={() => handleRegenerate(msg)}
                            disabled={sendMut.isPending}
                          >
                            Regenerate
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              ))}
              {sendMut.isPending && (
                <div className="flex justify-start">
                  <div className="max-w-[85%] rounded-2xl px-4 py-3 bg-white border border-slate-200 shadow-sm">
                    <p className="text-sm text-slate-500 animate-pulse">正在检索并生成…</p>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
            <div className="border-t border-slate-200 bg-white p-4 flex gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                rows={2}
                placeholder="Ask a question. Enter to send"
                className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button
                type="button"
                onClick={handleSend}
                disabled={sendMut.isPending || !input.trim()}
                className="self-end px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm disabled:opacity-50"
              >
                Send
              </button>
            </div>
          </>
        )}
      </section>

      <ChunkDrawer chunkId={chunkId} onClose={() => setChunkId(null)} />
    </div>
  );
}
