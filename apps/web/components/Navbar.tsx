"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { 
  Mic2, 
  Sparkles,
  Film,
  LogOut, 
  FolderKanban,
  History,
  Wand2
} from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  const navLinks = [
    { href: "/app/studio", label: "Y Studio", icon: Mic2 },
    { href: "/video-editor", label: "Video Editor", icon: Film },
    { href: "/app/image-prompts", label: "Prompt Generator", icon: Wand2 },
    { href: "/app/projects", label: "Projects", icon: FolderKanban },
    { href: "/app/history", label: "History", icon: History },
  ];

  return (
    <header className="border-b border-[#202436] bg-[#0E101A]/90 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-6">
          <Link href="/" className="flex items-center space-x-3 group" title="HK Speaks Home">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/25 group-hover:scale-105 transition-transform">
              <Mic2 className="w-5 h-5 text-white" />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-gray-200 to-indigo-300 bg-clip-text text-transparent leading-none">
                HK Speaks
              </span>
              <span className="text-[10px] uppercase font-semibold tracking-wider text-indigo-400 mt-0.5">
                Creative Studio
              </span>
            </div>
          </Link>

          {/* Main 3 Tools Navigation */}
          <nav className="hidden md:flex items-center space-x-1 pl-2">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = pathname === link.href || (link.href !== "/" && pathname.startsWith(`${link.href}/`));
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 shadow-inner font-semibold"
                      : "text-gray-400 hover:text-gray-200 hover:bg-[#181B2B]"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center space-x-3">
          {user ? (
            <div className="flex items-center space-x-3">
              <div className="hidden sm:flex flex-col items-end text-xs">
                <span className="font-medium text-gray-200">{user.display_name}</span>
                <span className="text-gray-400">{user.email}</span>
              </div>
              <button
                onClick={logout}
                title="Log out"
                className="p-2 rounded-lg bg-[#181B2B] hover:bg-red-500/20 hover:text-red-400 text-gray-400 border border-[#262B40] transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center space-x-2">
              <Link
                href="/app/studio"
                className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/25 transition-colors"
              >
                Open Studio
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
