import { NavLink, Outlet } from "react-router-dom";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `px-4 py-2 rounded-lg text-sm font-medium ${
    isActive ? "bg-indigo-600 text-white" : "text-slate-600 hover:bg-slate-200"
  }`;

export default function AppShell() {
  return (
    <div className="flex flex-col min-h-screen">
      <header className="border-b border-slate-200 bg-white px-6 py-3 flex items-center justify-between">
        <h1 className="text-lg font-semibold text-indigo-700">FusionRAG Knowledge Base</h1>
        <nav className="flex gap-2">
          <NavLink to="/chat" className={linkClass}>
            对话
          </NavLink>
          <NavLink to="/documents" className={linkClass}>
            文档管理
          </NavLink>
        </nav>
      </header>
      <main className="flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}
