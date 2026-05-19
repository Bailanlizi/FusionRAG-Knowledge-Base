import { useState } from "react";
import type { SourceItem } from "../../api/types";

const VISIBLE = 3;

export default function SourceList({
  sources,
  onSelect,
}: {
  sources: SourceItem[];
  onSelect: (chunkId: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  if (!sources.length) return null;

  const visible = expanded ? sources : sources.slice(0, VISIBLE);

  return (
    <div className="mt-3 border-t border-slate-200 pt-3">
      <p className="text-xs font-medium text-slate-500 mb-2">引用来源</p>
      <ul className="space-y-1.5">
        {visible.map((s) => (
          <li key={s.chunk_id}>
            <button
              type="button"
              onClick={() => onSelect(s.chunk_id)}
              className="text-left w-full text-xs text-indigo-600 hover:underline"
            >
              [{s.index}] {s.file_name || s.title_path}
              {s.page ? ` · p.${s.page}` : ""}
              {s.score != null ? ` · ${s.score.toFixed(3)}` : ""}
            </button>
          </li>
        ))}
      </ul>
      {sources.length > VISIBLE && (
        <button
          type="button"
          className="mt-2 text-xs text-slate-500 hover:text-indigo-600"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? "收起" : `展开更多 (${sources.length - VISIBLE})`}
        </button>
      )}
    </div>
  );
}
