import type { SortDir } from "@/hooks/useSort";

interface SortableHeaderProps {
  /** Column key to pass back to onSort */
  col: string;
  /** Display label */
  label: string;
  /** Currently active sort column */
  activeCol: string | null;
  /** Current sort direction */
  dir: SortDir;
  /** Called when this header is clicked */
  onSort: (col: string) => void;
  /** Extra Tailwind classes forwarded to <th> (e.g. "px-3 py-2 text-xs font-medium text-left") */
  className?: string;
  /** Text alignment — controls inline-flex justify */
  align?: "left" | "right";
}

/**
 * Reusable sortable <th> cell.
 * Renders the column label + a directional arrow indicator.
 * Active column shows ↑/↓; inactive columns show a dimmed ⇅.
 */
export function SortableHeader({
  col,
  label,
  activeCol,
  dir,
  onSort,
  className = "",
  align = "left",
}: SortableHeaderProps) {
  const active = activeCol === col;
  const arrow = active ? (dir === "asc" ? "↑" : "↓") : "⇅";

  return (
    <th
      onClick={() => onSort(col)}
      className={`cursor-pointer select-none hover:bg-black/5 transition-colors ${className}`}
    >
      <span
        className={`inline-flex items-center gap-1 ${
          align === "right" ? "flex-row-reverse w-full justify-start" : ""
        }`}
      >
        <span>{label}</span>
        <span
          className={`text-[10px] leading-none ${
            active ? "opacity-70" : "opacity-25"
          }`}
        >
          {arrow}
        </span>
      </span>
    </th>
  );
}
