export default function SettingsPage() {
  return (
    <main className="mx-auto max-w-5xl px-6 py-10 text-slate-100">
      <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Settings</p>
      <h1 className="mt-3 text-3xl font-semibold">Application settings</h1>
      <div className="mt-8 grid gap-6 md:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-xl font-medium">Backend</h2>
          <div className="mt-4 space-y-4 text-sm text-slate-300">
            <div><label>API base URL</label><input className="mt-2 block w-full rounded bg-slate-950 px-2 py-2" defaultValue="http://localhost:8000" /></div>
          </div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-xl font-medium">AI</h2>
          <div className="mt-4 space-y-4 text-sm text-slate-300">
            <div className="flex items-center justify-between rounded bg-slate-950 p-3"><span>AI enabled</span><span className="text-emerald-400">Off</span></div>
            <div><label>API key</label><input className="mt-2 block w-full rounded bg-slate-950 px-2 py-2" type="password" placeholder="optional" /></div>
          </div>
        </div>
      </div>
    </main>
  );
}
