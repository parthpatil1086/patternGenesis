"use client";

import { useMemo, useState } from "react";

export default function ReconstructPage() {
  const [result, setResult] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setPreviewUrl(URL.createObjectURL(file));
    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
      const response = await fetch(`${apiBaseUrl}/api/reconstruct`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail?.detail?.message || detail?.message || "Request failed");
      }

      const payload = await response.json();
      setResult(payload);
    } catch (error) {
      setResult({ error: "RECONSTRUCTION_FAILED", message: error instanceof Error ? error.message : String(error) });
    } finally {
      setLoading(false);
    }
  };

  const reconstructedSvg = useMemo(() => {
    if (!result || typeof result !== "object") return null;
    const payload = result as { reconstructed_svg?: string };
    return payload.reconstructed_svg || null;
  }, [result]);

  const payloadPreview = useMemo(() => (result ? JSON.stringify(result, null, 2) : "No reconstruction result yet."), [result]);

  return (
    <main className="mx-auto max-w-6xl px-4 py-6 text-slate-100 sm:px-6 lg:px-8">
      <div className="mb-8 flex flex-col gap-4 border-b border-slate-800 pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-violet-400">Reconstruct</p>
          <h1 className="mt-2 text-2xl font-semibold sm:text-3xl">Pattern reconstruction</h1>
        </div>
        <a href="/" className="rounded border border-slate-700 px-4 py-2 text-sm">Dashboard</a>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        <section className="rounded-xl border border-slate-800 bg-slate-900 p-4 sm:p-6">
          <label className="block text-sm text-slate-300">Upload source pattern</label>
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={handleUpload}
            className="mt-3 block w-full rounded-md border border-slate-700 bg-slate-950 p-3"
          />

          {previewUrl ? (
            <div className="mt-6 rounded border border-slate-800 bg-slate-950 p-2">
              <img src={previewUrl} alt="Original kolam source" className="max-h-72 w-full object-contain" />
            </div>
          ) : null}

          <div className="mt-6 rounded border border-slate-800 bg-slate-950 p-4 text-sm text-slate-300">
            {loading ? "Reconstructing geometry..." : "Awaiting image upload"}
          </div>
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-xl font-medium">Comparison view</h2>
          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <div className="rounded border border-slate-800 bg-slate-950 p-3">
              <p className="mb-2 text-xs uppercase tracking-[0.2em] text-slate-500">Original</p>
              {previewUrl ? <img src={previewUrl} alt="Original pattern preview" className="h-52 w-full object-contain" /> : <div className="h-52 flex items-center justify-center text-slate-500">No image</div>}
            </div>
            <div className="rounded border border-slate-800 bg-slate-950 p-3">
              <p className="mb-2 text-xs uppercase tracking-[0.2em] text-slate-500">Reconstructed</p>
              {reconstructedSvg ? <div className="h-52 w-full" dangerouslySetInnerHTML={{ __html: reconstructedSvg }} /> : <div className="flex h-52 items-center justify-center text-slate-500">No reconstruction</div>}
            </div>
          </div>

          <pre className="mt-6 max-h-[420px] overflow-auto whitespace-pre-wrap rounded bg-slate-950 p-4 text-xs text-violet-200">
            {payloadPreview}
          </pre>
        </section>
      </div>
    </main>
  );
}
