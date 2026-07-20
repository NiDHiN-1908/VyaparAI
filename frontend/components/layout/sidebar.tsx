// frontend/components/layout/sidebar.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  UploadCloud, 
  Play, 
  Users, 
  MessageSquare, 
  MessageCircle,
  BarChart3, 
  Sparkles,
  Sun,
  Moon,
  Settings,
  Bell,
  User,
  Info,
  HelpCircle,
  Layers,
  ChevronDown,
  ChevronUp,
  Youtube,
  Video,
  X,
  ArrowRight
} from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [isInfoExpanded, setIsInfoExpanded] = useState<boolean>(false);
  
  // Real-time live notifications state
  const [notifications, setNotifications] = useState<any[]>([]);
  const [showNotifications, setShowNotifications] = useState<boolean>(false);
  const [unreadCount, setUnreadCount] = useState<number>(0);

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  async function fetchLiveNotifications() {
    try {
      const items: any[] = [];

      // 1. Check pending YouTube comment approvals
      const replyRes = await fetch(`${API_BASE}/youtube-monitoring/comments/pending`);
      if (replyRes.ok) {
        const replyJson = await replyRes.json();
        const pendingList = replyJson.data || replyJson.pending_comments || [];
        if (pendingList.length > 0) {
          items.push({
            id: "pending-replies",
            type: "approval",
            title: "Pending Comment Approvals",
            desc: `${pendingList.length} YouTube AI replies awaiting your review before publishing`,
            link: "/reply-approval",
            time: "Just now",
            badge: `${pendingList.length}`
          });
        }
      }

      // 2. Check live lead telemetry & revenue
      const analyticsRes = await fetch(`${API_BASE}/analytics/campaigns`);
      if (analyticsRes.ok) {
        const aJson = await analyticsRes.json();
        if (aJson.qualified_leads > 0) {
          items.push({
            id: "qualified-leads",
            type: "lead",
            title: "Qualified Customer Leads",
            desc: `${aJson.qualified_leads} leads qualified & captured from social streams`,
            link: "/lead-dashboard",
            time: "Recent",
            badge: `${aJson.qualified_leads}`
          });
        }
        if (aJson.payments_completed > 0) {
          items.push({
            id: "payments",
            type: "payment",
            title: "UPI Orders Completed",
            desc: `${aJson.payments_completed} paid orders confirmed (Total Rs. ${aJson.revenue})`,
            link: "/lead-dashboard",
            time: "Today",
            badge: `Rs. ${aJson.revenue}`
          });
        }
      }

      // Default system notification if empty
      if (items.length === 0) {
        items.push({
          id: "system-ready",
          type: "system",
          title: "System Autopilot Ready",
          desc: "All 11 agents operational on CrewAI & LangGraph",
          link: "/agent-details",
          time: "Live",
          badge: "OK"
        });
      }

      setNotifications(items);
      setUnreadCount(items.filter(i => i.type !== "system").length || items.length);
    } catch (e) {
      console.warn("Notifications fetch error:", e);
    }
  }

  useEffect(() => {
    fetchLiveNotifications();
    const interval = setInterval(fetchLiveNotifications, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const isDark = document.documentElement.classList.contains("dark");
    setTheme(isDark ? "dark" : "light");
    
    // Check local storage to keep info expanded state if preferred
    const savedExpanded = localStorage.getItem("vyapar_info_expanded");
    if (savedExpanded === "true") {
      setIsInfoExpanded(true);
    }
  }, []);

  const toggleTheme = () => {
    if (theme === "light") {
      document.documentElement.classList.add("dark");
      localStorage.setItem("vyapar_theme", "dark");
      setTheme("dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("vyapar_theme", "light");
      setTheme("light");
    }
  };

  const toggleInfoExpanded = () => {
    const newState = !isInfoExpanded;
    setIsInfoExpanded(newState);
    localStorage.setItem("vyapar_info_expanded", String(newState));
  };

  const primaryNavigation = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Products", href: "/upload", icon: UploadCloud },
    { name: "Campaigns", href: "/preview", icon: Play },
    { name: "Background Jobs", href: "/jobs", icon: Layers },
    { name: "Monitored Videos", href: "/video-monitoring", icon: Video },
    { name: "Comment Inbox", href: "/comment-inbox", icon: MessageSquare },
    { name: "WhatsApp Live Chat", href: "/live-chat", icon: MessageCircle },
    { name: "Lead Dashboard", href: "/lead-dashboard", icon: Users },
    { name: "Analytics", href: "/analytics", icon: BarChart3 },
    { name: "Settings", href: "/whatsapp-settings", icon: Settings },
  ];

  const infoNavigation = [
    { name: "About", href: "/about", icon: Info },
    { name: "FAQ", href: "/faq", icon: HelpCircle },
    { name: "Agent Details", href: "/agent-details", icon: Sparkles },
    { name: "Module Details", href: "/module-details", icon: Layers },
  ];

  return (
    <aside className="w-56 m-4 h-[calc(100vh-2rem)] bg-slate-900/40 border border-slate-800/40 flex flex-col justify-between fixed left-0 top-0 z-20 rounded-2xl holo-panel transition-all duration-300">
      
      {/* Scrollable navigation area */}
      <div className="flex flex-col overflow-y-auto flex-1 pb-2 custom-scrollbar">
        {/* Holographic Brand Header */}
        <div className="h-20 flex items-center px-5 border-b border-slate-800/20 gap-3 flex-shrink-0">
          <div className="w-8 h-8 rounded-tl-xl rounded-br-xl rounded-tr-sm rounded-bl-sm bg-gradient-to-r from-accent to-purple-500 flex items-center justify-center text-white font-heading font-extrabold text-sm shadow-sm">
            V
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-heading font-bold tracking-tight text-slate-100 leading-none">
              Vyapar<span className="text-holo-iridescent font-bold">AI</span>
            </span>
            <span className="text-[9px] font-semibold text-slate-500 uppercase tracking-widest mt-1.5">
              Sales Autopilot
            </span>
          </div>
        </div>

        {/* 1. Primary Section */}
        <nav className="mt-4 px-3 space-y-0.5">
          <div className="px-3.5 mb-1.5 text-[9px] text-slate-500 font-bold uppercase tracking-widest">
            Primary Console
          </div>
          {primaryNavigation.map((item) => {
            const isActive = pathname === item.href || (pathname === "/" && item.href === "/dashboard");
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-semibold tracking-wide transition-all duration-300 relative group ${
                  isActive
                    ? "bg-indigo-500/10 text-holo-iridescent font-bold border border-indigo-500/10 shadow-sm"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/25"
                }`}
              >
                {isActive && (
                  <span className="absolute left-0 top-2.5 bottom-2.5 w-[3px] rounded-r bg-indigo-500" />
                )}
                <item.icon className={`w-4 h-4 transition-transform group-hover:scale-105 ${isActive ? "text-indigo-400" : "text-slate-500"}`} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Static bottom layout for Utilities & Info sections */}
      <div className="flex flex-col border-t border-slate-800/25 p-3.5 bg-slate-950/20 rounded-b-2xl">
        
        {/* 2. Utilities Section */}
        <div className="space-y-1.5 mb-3">
          <div className="px-2 text-[9px] text-slate-500 font-bold uppercase tracking-widest mb-1">
            Utilities
          </div>
          
          {/* Notifications Link - Real & Interactive */}
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="w-full flex items-center justify-between px-2.5 py-1.5 text-[11px] font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-900/60 rounded-xl transition relative group"
          >
            <span className="flex items-center gap-2">
              <Bell className={`w-3.5 h-3.5 ${unreadCount > 0 ? "text-indigo-400 animate-pulse" : "text-slate-500"}`} />
              <span>Notifications</span>
            </span>
            <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${unreadCount > 0 ? "bg-indigo-600 text-white shadow-sm shadow-indigo-500/30" : "bg-slate-900 border border-slate-800 text-slate-500"}`}>
              {unreadCount}
            </span>
          </button>

          {/* Profile link */}
          <div className="flex items-center justify-between px-2.5 py-1.5 text-[11px] font-semibold text-slate-400">
            <span className="flex items-center gap-2">
              <User className="w-3.5 h-3.5 text-slate-500" />
              <span>Merchant Profile</span>
            </span>
            <span className="text-[8px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-bold">
              Admin
            </span>
          </div>

          {/* Interface Theme Switcher */}
          <div className="flex items-center justify-between px-2.5 py-1.5 text-[11px] font-semibold text-slate-400">
            <span className="flex items-center gap-2">
              {theme === "light" ? (
                <Moon className="w-3.5 h-3.5 text-slate-500" />
              ) : (
                <Sun className="w-3.5 h-3.5 text-slate-500" />
              )}
              <span>Dark Theme</span>
            </span>
            <button 
              onClick={toggleTheme}
              className="p-1 rounded-md bg-slate-900 border border-slate-800 hover:border-slate-700 transition text-slate-400 hover:text-slate-100 flex items-center justify-center shadow-inner"
              title={theme === "light" ? "Switch to Dark Mode" : "Switch to Light Mode"}
            >
              {theme === "light" ? (
                <span className="w-2.5 h-2.5 bg-slate-400 rounded-full block m-0.5" />
              ) : (
                <span className="w-2.5 h-2.5 bg-indigo-500 rounded-full block m-0.5" />
              )}
            </button>
          </div>
        </div>

        {/* Divider line before collapsible resources */}
        <div className="border-t border-slate-850/60 my-2" />

        {/* 3. Information Section (Collapsible HELP / Resources) */}
        <div className="flex flex-col">
          <button 
            onClick={toggleInfoExpanded}
            className="w-full flex items-center justify-between px-2 py-1 text-[9px] text-slate-500 hover:text-slate-300 font-bold uppercase tracking-widest transition-colors"
          >
            <span>Help & Reference</span>
            {isInfoExpanded ? (
              <ChevronUp className="w-3 h-3 text-slate-500" />
            ) : (
              <ChevronDown className="w-3 h-3 text-slate-500" />
            )}
          </button>

          {isInfoExpanded && (
            <div className="mt-1 px-1.5 space-y-0.5 animate-fadeIn">
              {infoNavigation.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={`flex items-center gap-2 py-1.5 text-[11px] font-semibold tracking-wide transition-all duration-200 ${
                      isActive 
                        ? "text-indigo-400 font-bold" 
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <item.icon className="w-3.5 h-3.5 opacity-70" />
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </div>
          )}
        </div>

        <div className="mt-4 text-[8px] text-slate-600 font-bold flex items-center justify-between">
          <span>v1.0.0</span>
          <span>© VyaparAI</span>
        </div>
      </div>

      {/* Real-time Interactive Notifications Drawer Modal */}
      {showNotifications && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-fadeIn">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden space-y-4 p-6 relative">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-2 text-slate-100 font-extrabold text-base">
                <Bell className="w-4 h-4 text-indigo-400" />
                <span>Live System Notifications</span>
              </div>
              <button
                onClick={() => setShowNotifications(false)}
                className="p-1.5 rounded-xl text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2.5 max-h-80 overflow-y-auto">
              {notifications.map((n) => (
                <Link
                  key={n.id}
                  href={n.link}
                  onClick={() => setShowNotifications(false)}
                  className="p-3.5 rounded-2xl bg-slate-950/80 border border-slate-800/80 hover:border-indigo-500/50 hover:bg-slate-950 transition block space-y-1 group"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white group-hover:text-indigo-300 transition">
                      {n.title}
                    </span>
                    <span className="text-[9px] font-extrabold px-2 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                      {n.badge}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed font-medium">
                    {n.desc}
                  </p>
                  <div className="flex items-center justify-between text-[9px] text-slate-500 pt-1">
                    <span>{n.time}</span>
                    <span className="text-indigo-400 group-hover:underline flex items-center gap-1 font-semibold">
                      Action Required <ArrowRight className="w-2.5 h-2.5" />
                    </span>
                  </div>
                </Link>
              ))}
            </div>

            <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-[10px]">
              <button
                onClick={() => setUnreadCount(0)}
                className="text-slate-400 hover:text-white font-semibold transition"
              >
                Mark all as read
              </button>
              <button
                onClick={fetchLiveNotifications}
                className="text-indigo-400 hover:underline font-bold"
              >
                Refresh feed
              </button>
            </div>
          </div>
        </div>
      )}

    </aside>
  );
}
