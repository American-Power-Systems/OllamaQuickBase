import { Link, useLocation } from "wouter";
import { LayoutDashboard, FileInput, Settings, Code, Database, Bot } from "lucide-react";
import { cn } from "@/lib/utils";

export default function Layout({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();

  const navigation = [
    { name: "Queue Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Submit PO", href: "/submit", icon: FileInput },
    { name: "System Settings", href: "/settings", icon: Settings },
  ];

  return (
    <div className="min-h-screen flex bg-background font-sans text-foreground">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-border flex flex-col sticky top-0 h-screen">
        <div className="p-6 border-b border-border">
          <div className="flex items-center gap-2 text-primary font-bold text-xl">
            <Bot className="w-6 h-6" />
            <span>PO Intel</span>
          </div>
          <p className="text-xs text-muted-foreground mt-1">Azure AI Processing Unit</p>
        </div>

        <nav className="flex-1 p-4 space-y-1">
          {navigation.map((item) => {
            const isActive = location === item.href;
            return (
              <Link key={item.name} href={item.href}>
                <div
                  className={cn(
                    "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer",
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  )}
                >
                  <item.icon className="w-4 h-4" />
                  {item.name}
                </div>
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-border space-y-4">
           <div className="bg-slate-50 p-3 rounded-md border border-border">
              <h4 className="text-xs font-semibold text-slate-900 flex items-center gap-2 mb-2">
                <Code className="w-3 h-3" /> Backend Assets
              </h4>
              <p className="text-xs text-muted-foreground mb-2">
                Python source files generated for Azure deployment.
              </p>
              <div className="text-[10px] font-mono bg-white p-2 rounded border border-border text-slate-600">
                generated_backend/<br/>
                ├── app.py<br/>
                ├── worker.py<br/>
                └── requirements.txt
              </div>
           </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <header className="h-16 bg-white border-b border-border flex items-center justify-between px-8 sticky top-0 z-10">
          <h2 className="font-semibold text-lg">
            {navigation.find(n => n.href === location)?.name || "PO Processing"}
          </h2>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                <span>Redis: Connected</span>
            </div>
            <div className="h-4 w-px bg-border"></div>
            <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                <span>Ollama: Idle</span>
            </div>
          </div>
        </header>
        <div className="p-8 max-w-6xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  );
}
