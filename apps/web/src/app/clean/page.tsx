"use client";

import { useCallback, useRef, useState } from "react";

import { SiteHeader } from "@/components/SiteHeader";
import { RecordsExplorer } from "@/components/explore/RecordsExplorer";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/ui/States";
import { type CleanReport, cleanDownloadUrl } from "@/lib/api";
import { useCleanUpload } from "@/lib/queries";

function Dropzone({
  file,
  onFile,
}: {
  file: File | null;
  onFile: (file: File) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      setDragging(false);
      const dropped = event.dataTransfer.files?.[0];
      if (dropped) onFile(dropped);
    },
    [onFile],
  );

  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className={`rounded-lg border border-dashed p-md text-center ${
        dragging ? "border-secondary bg-panel" : "border-hairline"
      }`}
    >
      <p className="text-sm text-muted">
        Drag an occurrence CSV here, or
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="ml-1 font-bold text-primary hover:underline"
        >
          choose a file
        </button>
      </p>
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.tsv,text/csv,text/tab-separated-values"
        className="sr-only"
        aria-label="Occurrence CSV file"
        onChange={(event) => {
          const chosen = event.target.files?.[0];
          if (chosen) onFile(chosen);
        }}
      />
      {file ? (
        <p className="mt-3 text-sm font-bold text-ink">{file.name}</p>
      ) : (
        <p className="mt-3 text-xs text-muted">
          Comma or tab separated. GBIF download columns are recognized.
        </p>
      )}
    </div>
  );
}

function Results({ report }: { report: CleanReport }) {
  return (
    <section className="mt-10" aria-label="Results">
      <div className="flex flex-wrap items-center gap-4 rounded-lg border border-hairline bg-white p-md">
        <a
          href={cleanDownloadUrl(report.download_url)}
          className="rounded-md bg-secondary px-5 py-2.5 text-sm font-bold text-white hover:opacity-90"
        >
          Download cleaned CSV
        </a>
        <p className="text-xs text-muted">
          The cleaned file keeps every original row and adds the flag, the
          suspicion score, and the reasons. Nothing is deleted. Explore the
          flagged records below.
        </p>
      </div>

      <RecordsExplorer
        records={report.flagged}
        summary={report.summary}
        truncated={report.flagged_truncated}
        showTaxon
      />
    </section>
  );
}

export default function CleanPage() {
  const [file, setFile] = useState<File | null>(null);
  const upload = useCleanUpload();

  const onCheck = useCallback(() => {
    if (file) upload.mutate(file);
  }, [file, upload]);

  const onFile = useCallback(
    (chosen: File) => {
      setFile(chosen);
      upload.reset();
    },
    [upload],
  );

  return (
    <div className="min-h-screen bg-white text-ink">
      <SiteHeader />

      <main className="mx-auto max-w-6xl px-6 pb-20">
        <section className="pt-12">
          <h1 className="text-3xl font-semibold tracking-tight text-ink">
            Clean my data
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-7 text-muted">
            Upload a file of occurrence records and TaxonGuard runs the same
            engine on it. Every record is checked for coordinate-quality
            problems, and, where the data allows, for a land or sea realm
            mismatch and climate outliers. Suspect records are flagged with a
            plain reason and a score. Nothing is deleted.
          </p>
        </section>

        <section className="mt-8 max-w-2xl">
          <Dropzone file={file} onFile={onFile} />
          <div className="mt-4 flex items-center gap-3">
            <Button onClick={onCheck} disabled={!file || upload.isPending}>
              {upload.isPending ? "Checking..." : "Check file"}
            </Button>
            {file ? (
              <button
                type="button"
                onClick={() => {
                  setFile(null);
                  upload.reset();
                }}
                className="text-sm font-bold text-muted hover:text-ink"
              >
                Clear
              </button>
            ) : null}
          </div>

          {upload.isError ? (
            <div className="mt-4">
              <ErrorState
                title="Could not check the file"
                hint={
                  upload.error instanceof Error
                    ? upload.error.message
                    : "Please check the file and try again."
                }
                onRetry={() => upload.reset()}
              />
            </div>
          ) : null}
        </section>

        {upload.data ? <Results report={upload.data} /> : null}
      </main>

      <footer className="border-t border-hairline">
        <div className="mx-auto flex h-16 max-w-6xl items-center px-6 text-sm text-muted">
          Open source under the MIT license. An entry for the GBIF Ebbe Nielsen
          Challenge.
        </div>
      </footer>
    </div>
  );
}
