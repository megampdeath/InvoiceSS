import clsx from "clsx";

const styles: Record<string, string> = {
  uploaded: "border-slate-300 bg-slate-100 text-slate-700",
  processing: "border-blue-200 bg-blue-50 text-blue-800",
  needs_review: "border-amber-200 bg-amber-50 text-amber-800",
  approved: "border-teal-200 bg-teal-50 text-teal-800",
  failed: "border-rose-200 bg-rose-50 text-rose-800",
  archived: "border-slate-200 bg-white text-slate-500"
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={clsx("inline-flex rounded-md border px-2 py-1 text-xs font-semibold", styles[status] || styles.uploaded)}>
      {status.replace("_", " ")}
    </span>
  );
}
