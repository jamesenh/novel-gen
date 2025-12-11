import { ReactNode } from "react";
import Navbar from "./Navbar";
import Sidebar from "./Sidebar";

type Props = {
  children: ReactNode;
};

export default function Layout({ children }: Props) {
  return (
    <div className="relative min-h-screen bg-slate-50 text-slate-900">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_10%_20%,rgba(59,130,246,0.12),transparent_25%),radial-gradient(circle_at_80%_0%,rgba(99,102,241,0.1),transparent_20%)]" />
      <Navbar />
      <div className="relative mx-auto flex max-w-7xl gap-6 px-4 pb-12 pt-6 lg:px-10">
        <Sidebar className="hidden lg:block" />
        <main className="relative flex-1 space-y-6">
          <Sidebar layout="horizontal" className="lg:hidden" />
          {children}
        </main>
      </div>
    </div>
  );
}

