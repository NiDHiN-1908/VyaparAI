// frontend/app/layout.tsx
import "./globals.css";
import Sidebar from "@/components/layout/sidebar";

export const metadata = {
  title: "VyaparAI - Agentic Sales & Marketing Automation",
  description: "Autonomous SEO trends, copy, translation, TTS, video rendering, and lead qualification for Indian micro-businesses.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-100 flex min-h-screen">
        {/* Colorful ambient background blur effects */}
        <div className="fixed top-0 left-0 w-full h-full pointer-events-none overflow-hidden z-0">
          <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[60%] rounded-full bg-indigo-900/10 blur-[150px]" />
          <div className="absolute bottom-[-10%] right-[-10%] w-[60%] h-[50%] rounded-full bg-purple-900/10 blur-[150px]" />
        </div>

        {/* Sidebar Navigation */}
        <Sidebar />

        {/* Main Content Area */}
        <main className="flex-1 min-h-screen ml-64 p-8 z-10 relative overflow-y-auto">
          {children}
        </main>
      </body>
    </html>
  );
}
