export default function ThreeDPage({ params }: { params: { id: string } }) {
  return (
    <main className="mx-auto max-w-6xl px-6 py-10 text-slate-100">
      <p className="text-xs uppercase tracking-[0.3em] text-emerald-400">3D</p>
      <h1 className="mt-3 text-3xl font-semibold">3D viewer for design {params.id}</h1>
      <div className="mt-8 rounded-xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex min-h-[420px] items-center justify-center rounded border border-dashed border-slate-700 text-slate-500">
          3D mesh viewer placeholder
        </div>
      </div>
    </main>
  );
}
