import Link from "next/link";
import type { ReactNode } from "react";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-4 sm:px-6 md:flex-row md:items-center md:justify-between">
          <Link href="/" className="text-lg font-semibold tracking-wide text-cyan-400">PatternGenesis</Link>
          <nav className="flex flex-wrap items-center gap-3 text-sm text-slate-300 md:gap-5">
            <Link href="/analyze" className="transition hover:text-cyan-300">Analyze</Link>
            <Link href="/reconstruct" className="transition hover:text-cyan-300">Reconstruct</Link>
            <Link href="/generate" className="transition hover:text-cyan-300">Generate</Link>
          </nav>
        </div>
      </header>
      {children}
    </div>
  );
}
