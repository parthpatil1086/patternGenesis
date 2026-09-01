"use client";

import { useEffect, useState } from "react";

type Parameters = {
  symmetry_order: number;
  complexity: number;
  density: number;
  repetition_count: number;
  scale: number;
  curve_variation: number;
  spacing: number;
};

type GenerationResult = {
  svg?: string;
  geometry?: Record<string, unknown>;
  generatedGeometry?: Record<string, unknown>;
  referenceGeometry?: Record<string, unknown>;
  grammar?: Record<string, unknown>;
  parameters?: Record<string, unknown>;
  metrics?: Record<string, unknown>;
  error?: string;
  message?: string;
};

const DEFAULT_PARAMETERS: Parameters = {
  symmetry_order: 4,
  complexity: 0.65,
  density: 0.6,
  repetition_count: 6,
  scale: 1,
  curve_variation: 0.4,
  spacing: 42,
};

export function GenerateWorkspace() {
  const [reference, setReference] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [instructions, setInstructions] = useState("");
  const [parameters, setParameters] = useState<Parameters>(DEFAULT_PARAMETERS);
  const [result, setResult] = useState<GenerationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  const chooseReference = (file: File | null) => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    if (!file) {
      setReference(null);
      setPreviewUrl(null);
      return;
    }
    if (!file.type.match(/^image\/(png|jpeg|webp)$/) || file.size > 10 * 1024 * 1024) {
      setError("Choose a PNG, JPG, JPEG, or WEBP image smaller than 10 MB.");
      return;
    }
    setError("");
    setReference(file);
    setPreviewUrl(URL.createObjectURL(file));
  };

  const generate = async () => {
    setLoading(true);
    setError("");
    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
      let body: BodyInit;
      let endpoint = "/api/generate";
      const requestParameters = JSON.stringify(parameters);
      if (reference) {
        const form = new FormData();
        form.append("file", reference);
        form.append("instructions", instructions);
        form.append("parameters", requestParameters);
        body = form;
        endpoint = "/api/generate/image";
      } else {
        body = JSON.stringify({ grammar: { grammar_version: "2.0" }, parameters, instructions });
      }
      const response = await fetch(`${apiBaseUrl}${endpoint}`, {
        method: "POST",
        headers: reference ? undefined : { "Content-Type": "application/json" },
        body,
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload?.detail?.message || "Generation could not be completed.");
      setResult(payload);
    } catch (generationError) {
      setResult(null);
      setError(generationError instanceof Error ? generationError.message : "Generation could not be completed.");
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setReference(null);
    setPreviewUrl(null);
    setInstructions("");
    setParameters(DEFAULT_PARAMETERS);
    setResult(null);
    setError("");
  };

  const downloadSvg = () => {
    if (!result?.svg) return;
    const url = URL.createObjectURL(new Blob([result.svg], { type: "image/svg+xml" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "patterngenesis-generated.svg";
    link.click();
    URL.revokeObjectURL(url);
  };

  const updateParameter = (key: keyof Parameters, value: number) => {
    setParameters((current) => ({ ...current, [key]: value }));
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
      <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="text-lg font-medium">Reference image</h2>
        <label className="mt-4 block text-sm text-slate-300" htmlFor="reference-image">Upload a design</label>
        <input id="reference-image" type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => chooseReference(event.target.files?.[0] ?? null)} className="mt-2 block w-full rounded-md border border-slate-700 bg-slate-950 p-3 text-sm" />
        {previewUrl ? <div className="mt-4 rounded border border-slate-800 bg-slate-950 p-2"><img src={previewUrl} alt="Uploaded reference design" className="max-h-56 w-full object-contain" /></div> : <div className="mt-4 flex h-32 items-center justify-center rounded border border-dashed border-slate-700 text-sm text-slate-500">Optional for text-only generation</div>}
        <label className="mt-5 block text-sm text-slate-300" htmlFor="generation-instructions">Generation instructions</label>
        <textarea id="generation-instructions" value={instructions} onChange={(event) => setInstructions(event.target.value)} className="mt-2 block min-h-24 w-full rounded-md border border-slate-700 bg-slate-950 p-3 text-sm" placeholder="Describe how you want the pattern generated or modified..." />

        <h2 className="mt-6 text-lg font-medium">Parameters</h2>
        <div className="mt-3 space-y-4 text-sm text-slate-300">
          {([ ["symmetry_order", "Symmetry", 1, 12, 1], ["complexity", "Complexity", 0.1, 1, 0.05], ["density", "Density", 0.1, 1, 0.05], ["repetition_count", "Repetition", 1, 24, 1], ["scale", "Scale", 0.6, 1.6, 0.05], ["curve_variation", "Curve variation", 0, 1, 0.05], ["spacing", "Spacing", 20, 100, 1] ] as const).map(([key, label, min, max, step]) => (
            <label key={key} className="block">{label}<input aria-label={label} type="range" min={min} max={max} step={step} value={parameters[key]} onChange={(event) => updateParameter(key, Number(event.target.value))} className="mt-1 w-full accent-emerald-400" /><span className="text-xs text-slate-500">{parameters[key]}</span></label>
          ))}
        </div>
        {error ? <p role="alert" className="mt-5 rounded border border-red-900 bg-red-950/40 p-3 text-sm text-red-300">{error}</p> : null}
        <div className="mt-6 flex flex-wrap gap-3">
          <button type="button" onClick={generate} disabled={loading} className="rounded-md bg-emerald-500 px-4 py-2 font-medium text-slate-950 disabled:cursor-wait disabled:opacity-60">{loading ? "Generating..." : result ? "Regenerate pattern" : "Generate pattern"}</button>
          <button type="button" onClick={reset} className="rounded-md border border-slate-700 px-4 py-2 text-sm">Reset</button>
        </div>
        {loading ? <p className="mt-3 text-sm text-slate-400">Analyzing reference, building grammar, and rendering geometry...</p> : null}
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-xl font-medium">Generated pattern</h2>{result?.svg ? <button type="button" onClick={downloadSvg} className="rounded border border-slate-700 px-3 py-1.5 text-sm">Download SVG</button> : null}</div>
        <div className="mt-4 flex min-h-[360px] items-center justify-center rounded border border-slate-800 bg-slate-950 p-4">{result?.svg ? <div className="h-[340px] w-full" dangerouslySetInnerHTML={{ __html: result.svg }} /> : <p className="text-sm text-slate-500">Your generated vector pattern will appear here.</p>}</div>
        {result ? <div className="mt-5 grid gap-3 text-sm text-slate-300 sm:grid-cols-3"><div className="rounded bg-slate-950 p-3">Paths<br /><strong>{String(result.metrics?.generated_path_count ?? result.generatedGeometry?.paths ? (result.generatedGeometry?.paths as unknown[]).length : "N/A")}</strong></div><div className="rounded bg-slate-950 p-3">Complexity<br /><strong>{String(result.parameters?.complexity ?? "N/A")}</strong></div><div className="rounded bg-slate-950 p-3">Instructions<br /><strong>{instructions ? "Applied" : "None"}</strong></div></div> : null}
        <details className="mt-5 rounded border border-slate-800 bg-slate-950 p-4"><summary className="cursor-pointer text-sm text-slate-300">Analysis and grammar</summary><pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap text-xs text-emerald-200">{result ? JSON.stringify({ grammar: result.grammar, parameters: result.parameters, metrics: result.metrics }, null, 2) : "No generated result yet."}</pre></details>
      </section>
    </div>
  );
}
