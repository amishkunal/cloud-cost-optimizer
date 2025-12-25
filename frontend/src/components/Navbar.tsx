"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Server, Activity, BrainCircuit, CheckSquare } from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();

  const navItems = [
    { href: "/", label: "Home", icon: Home },
    { href: "/instances", label: "Instances", icon: Server },
    { href: "/recommendations", label: "Recommendations", icon: Activity },
    { href: "/analytics", label: "Analytics", icon: BrainCircuit },
    { href: "/actions", label: "Actions", icon: CheckSquare },
  ];

  return (
    <nav className="sticky top-0 z-50 w-full border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-blue-500 rounded-lg flex items-center justify-center">
              <BrainCircuit className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold bg-gradient-to-r from-emerald-400 to-blue-400 bg-clip-text text-transparent">
              Cost Optimizer
            </span>
          </Link>

          {/* Navigation Links */}
          <div className="flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
              
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`
                    relative flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200
                    ${
                      isActive
                        ? "bg-slate-800/60 text-emerald-400 shadow-lg shadow-emerald-500/10 border border-emerald-500/30"
                        : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
                    }
                  `}
                >
                  <Icon className={`w-4 h-4 ${isActive ? "text-emerald-400" : ""}`} />
                  <span>{item.label}</span>
                  {isActive && (
                    <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-emerald-400 to-blue-400 rounded-full" />
                  )}
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
}





