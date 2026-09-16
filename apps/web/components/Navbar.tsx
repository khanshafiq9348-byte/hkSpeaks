"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { 
  Mic2, 
  FolderKanban, 
  History, 
  KeyRound, 
  CreditCard, 
  ShieldAlert, 
  LogOut, 
  Sparkles,
  Film,
  Plus,
  ArrowLeft
} from "lucide-react";

export default function Navbar() {
  const pathname = usePathname();
  const { user, logout, loginAsDemo } = useAuth();

  const isVideoEditor = pathname.startsWith("/video-editor");

  const voiceLinks = [
    { href: "/app/studio", label: "Studio", icon: Mic2 },
    { href: "/app/voices", label: "Voices", icon: Sparkles },
    { href: "/app/history", label: "History", icon: History },
    { href: "/app/api", label: "API", icon: KeyRound },
    { href: "/app/billing", label: "Billing", icon: CreditCard },
  ];

  const videoLinks = [
    { href: "/video-editor", label: "Documentary Projects", icon: Film },
    { href: "/app/billing", label: "Billing", icon: CreditCard },
  ];

  if (user?.role === "admin") {
    voiceLinks.push({ href: "/admin", label: "Admin", icon: ShieldAlert });
    videoLinks.push({ href: "/admin", label: "Admin", icon: ShieldAlert });
  }

  const activeLinks = isVideoEditor ? videoLinks : voiceLinks;

  return (
    <header className="border-b border-[#202436] bg-[#0E101A]/90 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link
            href="/"
            className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-[#141724] hover:bg-[#1D2235] border border-[#21273C] text-xs font-semibold text-gray-300 hover:text-white transition-all shadow-sm group"
            title="Return to HK Speaks"
          >
            <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
            <span>Back to HK Speaks</span>
          </Link>

          <div className="h-4 w-px bg-[#202538] hidden sm:block" />

          <Link href="/" className="flex items-center space-x-2.5 group">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/25 group-hover:scale-105 transition-transform">
              {isVideoEditor ? <Film className="w-4 h-4 text-white" /> : <Mic2 className="w-4 h-4 text-white" />}
            </div>
            <div className="hidden sm:flex flex-col">
              <span className="font-bold text-base tracking-tight bg-gradient-to-r from-white via-gray-200 to-indigo-300 bg-clip-text text-transparent leading-none">
                HK Speaks
              </span>
              <span className="text-[10px] uppercase font-semibold tracking-wider text-indigo-400 mt-0.5">
                {isVideoEditor ? "AI Video Editor" : "AI Voice Studio"}
              </span>
            </div>
          </Link>

          {/* Module Nav Links */}
          <nav className="hidden md:flex items-center space-x-1 pl-2">
            {activeLinks.map((link) => {
              const Icon = link.icon;
              const isActive = pathname === link.href || (link.href !== "/video-editor" && pathname.startsWith(`${link.href}/`));
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? "bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 shadow-inner"
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
              <button
                onClick={() => loginAsDemo("creator")}
                className="hidden sm:flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-500/15 hover:bg-indigo-500/25 text-indigo-300 border border-indigo-500/30 transition-all"
                title="Sign in instantly with demo Creator account"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Demo Sign-In</span>
              </button>
              <Link
                href="/login"
                className="px-3 py-1.5 text-xs font-medium text-gray-300 hover:text-white"
              >
                Sign in
              </Link>
              <Link
                href="/signup"
                className="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/25 transition-colors"
              >
                Get Started
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
