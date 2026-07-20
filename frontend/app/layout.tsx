// frontend/app/layout.tsx
import "./globals.css";
import Sidebar from "@/components/layout/sidebar";
import BackendHealthGuard from "@/components/BackendHealthGuard";
import GlobalJobProgressWidget from "@/components/GlobalJobProgressWidget";

export const metadata = {
  title: "Project VyaparAI: An End-to-End Autonomous Sales Funnel and Collaborative Multi-Agent Pipeline for Micro-Businesses",
  description: "Autonomous SEO trends, copy, translation, TTS, video rendering, and lead qualification for Indian micro-businesses.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var theme = localStorage.getItem('vyapar_theme');
                  // Default to light mode (Ivory) unless explicitly set to dark
                  if (theme === 'dark') {
                    document.documentElement.classList.add('dark');
                  } else {
                    document.documentElement.classList.remove('dark');
                  }
                } catch (e) {}
              })();
            `,
          }}
        />
      </head>
      <body className="bg-slate-950 text-slate-100 flex min-h-screen relative font-sans antialiased overflow-x-hidden">
        {/* Subtle noise grain texture overlay */}
        <div className="fixed inset-0 pointer-events-none z-50 premium-grain" />

        {/* Animated holographic background grid */}
        <div className="holo-grid" />

        {/* Animated moving aurora background */}
        <div className="holo-aurora">
          <div className="holo-aurora-blob holo-blob-1" />
          <div className="holo-aurora-blob holo-blob-2" />
          <div className="holo-aurora-blob holo-blob-3" />
        </div>

        {/* Floating holographic particles */}
        <div className="holo-particles-container">
          <div className="holo-particle" style={{ top: '15%', left: '8%', animationDelay: '0s', width: '4px', height: '4px' }} />
          <div className="holo-particle" style={{ top: '45%', left: '22%', animationDelay: '3s', width: '6px', height: '6px' }} />
          <div className="holo-particle" style={{ top: '75%', left: '12%', animationDelay: '6s', width: '5px', height: '5px' }} />
          <div className="holo-particle" style={{ top: '25%', left: '82%', animationDelay: '1.5s', width: '7px', height: '7px' }} />
          <div className="holo-particle" style={{ top: '55%', left: '72%', animationDelay: '4.5s', width: '4px', height: '4px' }} />
          <div className="holo-particle" style={{ top: '85%', left: '88%', animationDelay: '2.5s', width: '6px', height: '6px' }} />
        </div>

        <BackendHealthGuard>
          {/* Sidebar Navigation */}
          <Sidebar />

          {/* Main Content Area */}
          <main className="flex-1 min-h-screen ml-64 p-10 z-10 relative overflow-y-auto transition-all duration-300">
            {children}
          </main>

          {/* Floating Global Progress Widget */}
          <GlobalJobProgressWidget />
        </BackendHealthGuard>
      </body>
    </html>
  );
}
