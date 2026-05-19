import { useState } from "react";
import type { TraceInfo } from "../../api/types";

export default function TracePanel({ trace }: { trace: TraceInfo }) {
  const [open, setOpen] = useState(false);
  const total =
    (trace.rewrite_ms ?? 0) + trace.retrieval_ms + trace.rerank_ms + trace.llm_ms;

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="text-xs text-slate-500 hover:text-indigo-600"
      >
        {open ? "[-]" : "[+]"} Trace - {total.toFixed(0)}ms - {trace.chunk_count} chunks
      </button>
      {open && (
        <div className="mt-2 rounded-lg bg-slate-100 p-3 text-xs text-slate-600 space-y-1">
          <p>Complexity: {trace.complexity}</p>
          {trace.is_follow_up && trace.standalone_query && (
            <p>
              Rewritten query: {trace.standalone_query}
              {trace.rewrite_ms != null ? ` (${trace.rewrite_ms}ms)` : ""}
            </p>
          )}
          <p>
            Rewrite: {trace.rewrite_ms ?? 0}ms | Retrieval: {trace.retrieval_ms}ms | Rerank:{" "}
            {trace.rerank_ms}ms | LLM: {trace.llm_ms}ms
          </p>
          <p>Queries ({trace.queries.length}):</p>
          <ul className="list-disc pl-4">
            {trace.queries.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
