export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 lg:py-12">
        <div className="mb-10">
          <p className="text-xs uppercase tracking-[0.3em] text-cyan-400">PatternGenesis</p>
          <h1 className="mt-2 text-2xl font-semibold sm:text-3xl">Computational design grammar studio</h1>
        </div>

        <section className="mt-10 grid gap-6 md:grid-cols-3">
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
            <p className="text-sm text-slate-400">Pipeline</p>
            <h2 className="mt-2 text-xl font-medium">Image → Geometry → Grammar</h2>
            <p className="mt-3 text-sm text-slate-300">
              Upload a Kolam image, analyze geometry, and reconstruct a deterministic parametric pattern.
            </p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
            <p className="text-sm text-slate-400">Core</p>
            <h2 className="mt-2 text-xl font-medium">Symmetry and repetition</h2>
            <p className="mt-3 text-sm text-slate-300">
              Identify dot arrangements, symmetry order, and repeated motifs across a design grammar.
            </p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
            <p className="text-sm text-slate-400">Export</p>
            <h2 className="mt-2 text-xl font-medium">SVG, JSON, and 3D</h2>
            <p className="mt-3 text-sm text-slate-300">
              Save exported patterns and open them in the reconstruction and 3D viewer flows.
            </p>
          </div>
        </section>

        <section className="mt-10 rounded-xl border border-slate-800 bg-slate-900 p-6">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm text-slate-400">Current status</p>
              <h2 className="mt-1 text-2xl font-semibold">Project foundation online</h2>
            </div>
            <button className="rounded-md border border-cyan-500 bg-cyan-500/10 px-4 py-2 text-sm text-cyan-300">
              Analyze sample pattern
            </button>
          </div>
          <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[
              ["Tradition", "Kolam"],
              ["Grammar", "Universal JSON"],
              ["Storage", "SQLite"],
              ["Backend", "FastAPI"],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg border border-slate-800 bg-slate-950 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{label}</p>
                <p className="mt-2 text-lg font-medium">{value}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
