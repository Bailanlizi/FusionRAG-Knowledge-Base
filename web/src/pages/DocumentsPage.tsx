import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState } from "react";
import { api } from "../api/client";
import type { ChunkItem, DocumentItem } from "../api/types";

export default function DocumentsPage() {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [sourceType, setSourceType] = useState("");
  const [sort, setSort] = useState("updated_at");
  const [order, setOrder] = useState("desc");
  const [previewDoc, setPreviewDoc] = useState<DocumentItem | null>(null);
  const [uploadPct, setUploadPct] = useState<number | null>(null);

  const { data: stats } = useQuery({
    queryKey: ["kb-stats"],
    queryFn: api.kbStats,
  });

  const { data: list, isLoading } = useQuery({
    queryKey: ["documents", q, sourceType, sort, order],
    queryFn: () =>
      api.listDocuments({
        q,
        source_type: sourceType,
        sort,
        order,
        page: "1",
        page_size: "50",
      }),
  });

  const { data: previewChunks } = useQuery({
    queryKey: ["doc-chunks", previewDoc?.doc_id],
    queryFn: () => api.listDocChunks(previewDoc!.doc_id),
    enabled: !!previewDoc,
  });

  const deleteMut = useMutation({
    mutationFn: api.deleteDocument,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents"] });
      qc.invalidateQueries({ queryKey: ["kb-stats"] });
    },
  });

  const onDrop = useCallback(
    async (files: FileList | null) => {
      if (!files?.length) return;
      for (const file of Array.from(files)) {
        setUploadPct(0);
        try {
          await api.uploadDocument(file, setUploadPct);
        } finally {
          setUploadPct(null);
        }
      }
      qc.invalidateQueries({ queryKey: ["documents"] });
      qc.invalidateQueries({ queryKey: ["kb-stats"] });
    },
    [qc]
  );

  const formatDate = (s: string) => new Date(s).toLocaleString("zh-CN");

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Docs" value={stats?.document_count ?? "-"} />
        <StatCard label="Chunks" value={stats?.chunk_count ?? "-"} />
        <StatCard
          label="Updated"
          value={stats?.last_updated_at ? formatDate(stats.last_updated_at) : "-"}
        />
      </div>

      <div
        className="border-2 border-dashed border-slate-300 rounded-xl p-8 text-center bg-white hover:border-indigo-400 transition-colors"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          onDrop(e.dataTransfer.files);
        }}
      >
        <p className="text-slate-600 text-sm mb-2">Drop PDF / Markdown here, or</p>
        <label className="inline-block cursor-pointer rounded-lg bg-indigo-600 text-white text-sm px-4 py-2 hover:bg-indigo-700">
          Choose files
          <input
            type="file"
            className="hidden"
            accept=".pdf,.md,.markdown,.txt"
            multiple
            onChange={(e) => onDrop(e.target.files)}
          />
        </label>
        {uploadPct != null && (
          <div className="mt-4 max-w-xs mx-auto">
            <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-600 transition-all"
                style={{ width: `${uploadPct}%` }}
              />
            </div>
            <p className="text-xs text-slate-500 mt-1">{uploadPct}%</p>
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-3 items-center bg-white rounded-xl border p-4">
        <input
          type="search"
          placeholder="Search filename..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="rounded-lg border px-3 py-2 text-sm flex-1 min-w-[200px]"
        />
        <select
          value={sourceType}
          onChange={(e) => setSourceType(e.target.value)}
          className="rounded-lg border px-3 py-2 text-sm"
        >
          <option value="">All sources</option>
          <option value="confluence">confluence</option>
          <option value="upload">upload</option>
        </select>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="rounded-lg border px-3 py-2 text-sm"
        >
          <option value="updated_at">updated_at</option>
          <option value="created_at">created_at</option>
          <option value="file_name">file_name</option>
        </select>
        <select
          value={order}
          onChange={(e) => setOrder(e.target.value)}
          className="rounded-lg border px-3 py-2 text-sm"
        >
          <option value="desc">desc</option>
          <option value="asc">asc</option>
        </select>
      </div>

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="text-left px-4 py-3">Name</th>
              <th className="text-left px-4 py-3">Source</th>
              <th className="text-right px-4 py-3">Chunks</th>
              <th className="text-left px-4 py-3">Created</th>
              <th className="text-left px-4 py-3">Updated</th>
              <th className="text-right px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                  Loading...
                </td>
              </tr>
            )}
            {list?.items.map((doc) => (
              <tr key={doc.doc_id} className="border-t hover:bg-slate-50">
                <td className="px-4 py-3 font-medium truncate max-w-xs">{doc.file_name}</td>
                <td className="px-4 py-3 text-slate-500">{doc.source_type}</td>
                <td className="px-4 py-3 text-right">{doc.chunk_count}</td>
                <td className="px-4 py-3 text-slate-500">{formatDate(doc.created_at)}</td>
                <td className="px-4 py-3 text-slate-500">{formatDate(doc.updated_at)}</td>
                <td className="px-4 py-3 text-right space-x-2">
                  <button
                    type="button"
                    className="text-indigo-600 hover:underline"
                    onClick={() => setPreviewDoc(doc)}
                  >
                    Preview
                  </button>
                  <button
                    type="button"
                    className="text-red-600 hover:underline"
                    onClick={() => {
                      if (confirm(`Delete ${doc.file_name}?`)) deleteMut.mutate(doc.doc_id);
                    }}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {previewDoc && (
        <PreviewModal
          doc={previewDoc}
          chunks={previewChunks ?? []}
          onClose={() => setPreviewDoc(null)}
        />
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white rounded-xl border p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-2xl font-semibold mt-1 text-indigo-700">{value}</p>
    </div>
  );
}

function PreviewModal({
  doc,
  chunks,
  onClose,
}: {
  doc: DocumentItem;
  chunks: ChunkItem[];
  onClose: () => void;
}) {
  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-40" onClick={onClose} />
      <div className="fixed inset-4 md:inset-10 bg-white rounded-xl shadow-xl z-50 flex flex-col">
        <div className="flex justify-between items-center border-b px-4 py-3">
          <h3 className="font-medium">{doc.file_name}</h3>
          <button type="button" onClick={onClose}>
            X
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {chunks.length === 0 ? (
            <p className="text-slate-500 text-sm">No chunks</p>
          ) : (
            chunks.map((c) => (
              <div key={c.chunk_id} className="border rounded-lg p-3">
                <p className="text-xs text-slate-500 mb-2">
                  {c.title_path} p.{c.page} {c.chunk_id}
                </p>
                <pre className="text-xs whitespace-pre-wrap text-slate-700">{c.content}</pre>
              </div>
            ))
          )}
        </div>
      </div>
    </>
  );
}
