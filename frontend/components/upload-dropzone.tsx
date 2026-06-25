"use client";

import clsx from "clsx";
import { UploadCloud } from "lucide-react";
import { useRef, useState } from "react";

export function UploadDropzone({
  onUpload,
  disabled
}: {
  onUpload: (file: File) => Promise<void>;
  disabled?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submitFile(file?: File) {
    if (!file || busy || disabled) {
      return;
    }
    setBusy(true);
    try {
      await onUpload(file);
    } finally {
      setBusy(false);
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    }
  }

  return (
    <button
      type="button"
      title="Upload invoice"
      disabled={disabled || busy}
      className={clsx(
        "flex min-h-28 w-full items-center justify-center rounded-lg border border-dashed px-4 text-left transition",
        dragging ? "border-signal bg-teal-50" : "border-line bg-white hover:border-signal",
        (disabled || busy) && "cursor-not-allowed opacity-60"
      )}
      onClick={() => inputRef.current?.click()}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        void submitFile(event.dataTransfer.files[0]);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept="application/pdf,image/jpeg,image/png,image/tiff"
        onChange={(event) => void submitFile(event.target.files?.[0])}
      />
      <span className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-md bg-teal-50 text-signal">
          <UploadCloud size={21} />
        </span>
        <span>
          <span className="block text-sm font-semibold text-ink">{busy ? "Uploading..." : "Upload invoice"}</span>
          <span className="block text-xs text-slate-500">PDF, JPG, PNG, or TIFF up to 25 MB</span>
        </span>
      </span>
    </button>
  );
}
