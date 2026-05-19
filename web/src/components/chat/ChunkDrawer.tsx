import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";

export default function ChunkDrawer({
  chunkId,
  onClose,
}: {
  chunkId: string | null;
  onClose: () => void;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["chunk", chunkId],
    queryFn: () => api.getChunk(chunkId!),
    enabled: !!chunkId,
  });

  if (!chunkId) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />
      <aside className="fixed right-0 top-0 h-full w-full max-w-lg bg-white shadow-xl z-50 flex flex-col">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h3 className="font-medium text-sm">Chunk detail</h3>
          <button type="button" onClick={onClose} className="text-slate-500 hover:text-slate-800">
            Close
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 text-sm">
          {isLoading && <p className="text-slate-500">Loading...</p>}
          {data && (
            <>
              <p className="font-medium text-indigo-700 mb-2">{data.file_name}</p>
              <p className="text-xs text-slate-500 mb-4">
                {data.title_path} - p.{data.page} - {data.chunk_id}
              </p>
              <pre className="whitespace-pre-wrap text-xs bg-slate-50 rounded-lg p-4 border">
                {data.content}
              </pre>
            </>
          )}
        </div>
      </aside>
    </>
  );
}
