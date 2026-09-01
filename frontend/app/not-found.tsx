import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 p-8 text-slate-100">
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-8 text-center">
        <p className="text-xs uppercase tracking-[0.3em] text-cyan-400">404</p>
        <h1 className="mt-3 text-3xl font-semibold">Page not found</h1>
        <p className="mt-3 text-slate-400">The requested PatternGenesis route does not exist.</p>
        <Link href="/" className="mt-6 inline-block rounded border border-slate-700 px-4 py-2 text-sm">
          Return home
        </Link>
      </div>
    </main>
  );
}
