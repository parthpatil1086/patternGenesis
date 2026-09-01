import { GenerateWorkspace } from "../../components/generate/GenerateWorkspace";

export default function GeneratePage() {
  return (
    <main className="min-h-screen bg-slate-950 px-4 py-6 text-slate-100 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl">
        <header className="mb-8 flex flex-col gap-4 border-b border-slate-800 pb-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-emerald-400">Generate</p>
            <h1 className="mt-2 text-2xl font-semibold sm:text-3xl">Grammar-based pattern generation</h1>
          </div>
          <a href="/" className="rounded border border-slate-700 px-4 py-2 text-sm">Back to dashboard</a>
        </header>
        <GenerateWorkspace />
      </div>
    </main>
  );
}
