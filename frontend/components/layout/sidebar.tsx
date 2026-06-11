// frontend/components/layout/sidebar.tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  UploadCloud, 
  Play, 
  CheckSquare, 
  Users, 
  MessageSquare, 
  BarChart3, 
  Sparkles 
} from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();

  const navigation = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Upload Product", href: "/upload", icon: UploadCloud },
    { name: "Video Drafts", href: "/preview", icon: Play },
    { name: "Approvals", href: "/approval", icon: CheckSquare },
    { name: "Lead CRM", href: "/crm", icon: Users },
    { name: "Chat Simulator", href: "/chat", icon: MessageSquare },
    { name: "Analytics", href: "/analytics", icon: BarChart3 },
  ];

  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between h-screen fixed left-0 top-0 z-20">
      <div className="flex flex-col">
        {/* Logo brand */}
        <div className="h-16 flex items-center px-6 border-b border-slate-800 gap-2">
          <Sparkles className="w-6 h-6 text-indigo-400 animate-pulse" />
          <span className="text-xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            VyaparAI
          </span>
        </div>

        {/* Navigation Links */}
        <nav className="mt-6 px-4 space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href || (pathname === "/" && item.href === "/dashboard");
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? "bg-indigo-600/20 border-l-4 border-indigo-500 text-indigo-200 font-semibold"
                    : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
                }`}
              >
                <item.icon className={`w-5 h-5 ${isActive ? "text-indigo-400" : "text-slate-400"}`} />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer / Meta */}
      <div className="p-6 border-t border-slate-800 text-xs text-slate-500">
        <p>VyaparAI Platform v1.0</p>
        <p className="mt-1">© 2026 VyaparAI.in</p>
      </div>
    </aside>
  );
}
