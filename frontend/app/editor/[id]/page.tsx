export default function EditorPage({ params }: { params: { id: string } }) {
  return (
    <main className="mx-auto max-w-7xl px-6 py-10 text-slate-100">
      <p className="text-xs uppercase tracking-[0.3em] text-cyan-400">Editor</p>
      <h1 className="mt-3 text-3xl font-semibold">Parametric editor for design {params.id}</h1>
      <div className="mt-8 grid gap-6 lg:grid-cols-[240px_1fr_320px]">
        <aside className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <p className="text-sm text-slate-400">Tools</p>
          <ul className="mt-4 space-y-2 text-sm text-slate-300">
            <li>Point</li>
            <li>Line</li>
            <li>Curve</li>
            <li>Mirror</li>
            <li>Rotate</li>
            <li>Repeat</li>
          </ul>
        </aside>
        <section className="min-h-[420px] rounded-xl border border-slate-800 bg-slate-900 p-4">
          <div className="flex h-full items-center justify-center text-slate-500">Interactive canvas placeholder</div>
        </section>
        <aside className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <p className="text-sm text-slate-400">Properties</p>
          <div className="mt-4 space-y-4 text-sm text-slate-300">
            <div><label>Symmetry order</label><input className="mt-2 block w-full rounded bg-slate-950 px-2 py-2" defaultValue={4} /></div>
            <div><label>Spacing</label><input className="mt-2 block w-full rounded bg-slate-950 px-2 py-2" defaultValue={42} /></div>
            <div><label>Rotation</label><input className="mt-2 block w-full rounded bg-slate-950 px-2 py-2" defaultValue={0} /></div>
          </div>
        </aside>
      </div>
    </main>
  );
}
