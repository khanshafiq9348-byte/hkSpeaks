"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiClient } from "@/lib/api";
import {
  Mic2,
  Sparkles,
  FolderKanban,
  History,
  KeyRound,
  Crown,
  ChevronDown,
  ChevronRight,
  PanelLeftClose,
  PanelLeft,
  Volume2,
  UserCheck,
  Film,
  LogOut,
  Zap,
  Globe,
  ShieldAlert
} from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { user, logout } = useAuth();

  // Collapsed state
  const [isCollapsed, setIsCollapsed] = useState(false);
  // Voices submenu accordion state
  const [isVoicesOpen, setIsVoicesOpen] = useState(true);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("hk_sidebar_collapsed");
      if (stored !== null) {
        setIsCollapsed(stored === "true");
      }
    }
  }, []);

  const toggleCollapsed = () => {
    const next = !isCollapsed;
    setIsCollapsed(next);
    if (typeof window !== "undefined") {
      localStorage.setItem("hk_sidebar_collapsed", String(next));
    }
  };

  const isStudio = pathname === "/app/studio";
  const currentCategory = searchParams.get("category");
  const isLibraryActive = isStudio && currentCategory === "library";
  const isPremiumActive = isStudio && currentCategory === "premium";
  const isEdgeActive = isStudio && (currentCategory === "edge" || (!currentCategory && !pathname.startsWith("/app/clone") && !pathname.startsWith("/app/voices")));
  const isElevenLabsActive = isStudio && currentCategory === "elevenlabs";
  const isCloneActive = (isStudio && currentCategory === "clone") || pathname === "/app/clone";
  const isVoicesSectionActive = isStudio || pathname.startsWith("/app/voices") || pathname === "/app/clone";
  const isProjects = pathname.startsWith("/app/projects");
  const isHistory = pathname.startsWith("/app/history");
  const isApi = pathname.startsWith("/app/api");

  return (
    <aside
      className={`relative flex flex-col h-screen bg-[#0C0E17] border-r border-[#1C2033] transition-all duration-300 z-30 select-none ${
        isCollapsed ? "w-20" : "w-64"
      }`}
    >
      {/* 1. Header & Brand */}
      <div className="h-16 px-4 flex items-center justify-between border-b border-[#1C2033]">
        {!isCollapsed ? (
          <Link href="/" className="flex items-center space-x-3 group min-w-0" title="Return to HK Speaks">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/25 group-hover:scale-105 transition-transform flex-shrink-0">
              <Mic2 className="w-5 h-5 text-white" />
            </div>
            <div className="flex flex-col min-w-0">
              <span className="font-bold text-base tracking-tight bg-gradient-to-r from-white via-gray-200 to-indigo-300 bg-clip-text text-transparent truncate">
                HK Speaks
              </span>
              <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-400">
                AI Voice Studio
              </span>
            </div>
          </Link>
        ) : (
          <Link href="/" className="mx-auto" title="Return to HK Speaks">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/25">
              <Mic2 className="w-5 h-5 text-white" />
            </div>
          </Link>
        )}

        {/* Corner Toggle Button */}
        <button
          onClick={toggleCollapsed}
          title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          className={`p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-[#181C2E] border border-transparent hover:border-[#272D45] transition-all ${
            isCollapsed ? "hidden" : "block"
          }`}
        >
          <PanelLeftClose className="w-4 h-4" />
        </button>
      </div>

      {/* When collapsed, toggle button placed underneath header */}
      {isCollapsed && (
        <div className="flex justify-center py-2 border-b border-[#1C2033]">
          <button
            onClick={toggleCollapsed}
            title="Expand sidebar"
            className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-[#181C2E] border border-transparent hover:border-[#272D45] transition-all"
          >
            <PanelLeft className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* 2. Navigation List */}
      <nav className="flex-1 px-3 py-3 space-y-1.5 overflow-y-auto overflow-x-hidden">
        {/* Studio (Main Workspace) */}
        <Link
          href="/app/studio"
          title="Studio (Script Editor)"
          className={`flex items-center rounded-xl transition-all ${
            isCollapsed
              ? "justify-center p-3"
              : "space-x-3 px-3.5 py-2.5"
          } ${
            isStudio
              ? "bg-indigo-600 text-white font-semibold shadow-md shadow-indigo-600/30"
              : "text-gray-300 hover:text-white hover:bg-[#141726]"
          }`}
        >
          <Mic2 className="w-4 h-4 flex-shrink-0" />
          {!isCollapsed && <span className="text-sm font-medium">Studio</span>}
        </Link>

        {/* Voices Category Group */}
        <div>
          <button
            onClick={() => {
              if (isCollapsed) {
                setIsCollapsed(false);
                setIsVoicesOpen(true);
              } else {
                setIsVoicesOpen(!isVoicesOpen);
              }
            }}
            title="Voices"
            className={`w-full flex items-center justify-between rounded-xl transition-all ${
              isCollapsed
                ? "justify-center p-3"
                : "px-3.5 py-2.5"
            } ${
              isVoicesSectionActive
                ? "bg-indigo-600/15 text-indigo-300 border border-indigo-500/30 font-semibold"
                : "text-gray-300 hover:text-white hover:bg-[#141726]"
            }`}
          >
            <div className={`flex items-center ${isCollapsed ? "" : "space-x-3"}`}>
              <Sparkles className="w-4 h-4 flex-shrink-0 text-indigo-400" />
              {!isCollapsed && <span className="text-sm font-medium">Voices</span>}
            </div>
            {!isCollapsed && (
              isVoicesOpen ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />
            )}
          </button>

          {/* Voices Sub-items */}
          {!isCollapsed && isVoicesOpen && (
            <div className="mt-1 pl-4 space-y-1 border-l-2 border-[#1E2338] ml-5">
              <Link
                href="/app/studio?category=library"
                className={`flex items-center space-x-2.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  isLibraryActive
                    ? "bg-indigo-600 text-white shadow-sm font-semibold"
                    : "text-gray-400 hover:text-gray-200 hover:bg-[#161929]"
                }`}
              >
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                <span>Voice Library</span>
              </Link>

              <Link
                href="/app/studio?category=premium"
                className={`flex items-center space-x-2.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  isPremiumActive
                    ? "bg-indigo-600 text-white shadow-sm font-semibold"
                    : "text-amber-400/90 hover:text-amber-300 hover:bg-[#161929]"
                }`}
              >
                <Crown className="w-3.5 h-3.5 text-amber-400" />
                <span>Premium Voices</span>
              </Link>

              <Link
                href="/app/studio?category=edge"
                className={`flex items-center space-x-2.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  isEdgeActive
                    ? "bg-indigo-600 text-white shadow-sm font-semibold"
                    : "text-gray-400 hover:text-gray-200 hover:bg-[#161929]"
                }`}
              >
                <Volume2 className="w-3.5 h-3.5 text-indigo-400" />
                <span>Edge TTS</span>
              </Link>

              <Link
                href="/app/studio?category=elevenlabs"
                className={`flex items-center space-x-2.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  isElevenLabsActive
                    ? "bg-indigo-600 text-white shadow-sm font-semibold"
                    : "text-cyan-400/90 hover:text-cyan-300 hover:bg-[#161929]"
                }`}
              >
                <Zap className="w-3.5 h-3.5 text-cyan-400" />
                <span>ElevenLabs</span>
              </Link>

              <Link
                href="/app/studio?category=clone"
                className={`flex items-center space-x-2.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  isCloneActive
                    ? "bg-teal-600 text-white shadow-sm font-semibold"
                    : "text-teal-400/90 hover:text-teal-300 hover:bg-[#161929]"
                }`}
              >
                <UserCheck className="w-3.5 h-3.5 text-teal-400" />
                <span>Voice Cloning / Your Clone</span>
              </Link>

              <Link
                href="/app/voices"
                className={`flex items-center space-x-2.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  pathname.startsWith("/app/voices")
                    ? "bg-indigo-600 text-white shadow-sm font-semibold"
                    : "text-gray-500 hover:text-gray-300 hover:bg-[#161929]"
                }`}
              >
                <Globe className="w-3.5 h-3.5 text-indigo-400" />
                <span>Full Voice Catalog</span>
              </Link>
            </div>
          )}
        </div>

        {/* Projects */}
        <Link
          href="/app/projects"
          title="Projects"
          className={`flex items-center rounded-xl transition-all ${
            isCollapsed
              ? "justify-center p-3"
              : "space-x-3 px-3.5 py-2.5"
          } ${
            isProjects
              ? "bg-indigo-600 text-white font-semibold shadow-md shadow-indigo-600/30"
              : "text-gray-300 hover:text-white hover:bg-[#141726]"
          }`}
        >
          <FolderKanban className="w-4 h-4 flex-shrink-0" />
          {!isCollapsed && <span className="text-sm font-medium">Projects</span>}
        </Link>

        {/* History */}
        <Link
          href="/app/history"
          title="History"
          className={`flex items-center rounded-xl transition-all ${
            isCollapsed
              ? "justify-center p-3"
              : "space-x-3 px-3.5 py-2.5"
          } ${
            isHistory
              ? "bg-indigo-600 text-white font-semibold shadow-md shadow-indigo-600/30"
              : "text-gray-300 hover:text-white hover:bg-[#141726]"
          }`}
        >
          <History className="w-4 h-4 flex-shrink-0" />
          {!isCollapsed && <span className="text-sm font-medium">History</span>}
        </Link>

        {/* API / Developer API */}
        <Link
          href="/app/api"
          title="API / Developer API"
          className={`flex items-center rounded-xl transition-all ${
            isCollapsed
              ? "justify-center p-3"
              : "space-x-3 px-3.5 py-2.5"
          } ${
            isApi
              ? "bg-indigo-600 text-white font-semibold shadow-md shadow-indigo-600/30"
              : "text-gray-300 hover:text-white hover:bg-[#141726]"
          }`}
        >
          <KeyRound className="w-4 h-4 flex-shrink-0" />
          {!isCollapsed && <span className="text-sm font-medium">API / Developer API</span>}
        </Link>

        {/* Admin Link if admin */}
        {user?.role === "admin" && (
          <Link
            href="/admin"
            title="Admin Dashboard"
            className={`flex items-center rounded-xl transition-all ${
              isCollapsed
                ? "justify-center p-3"
                : "space-x-3 px-3.5 py-2.5"
            } ${
              pathname.startsWith("/admin")
                ? "bg-rose-600 text-white font-semibold"
                : "text-rose-400 hover:text-rose-300 hover:bg-rose-950/20"
            }`}
          >
            <ShieldAlert className="w-4 h-4 flex-shrink-0" />
            {!isCollapsed && <span className="text-sm font-medium">Admin</span>}
          </Link>
        )}
      </nav>

      {/* 4. Bottom Section: User Info & Logout */}
      <div className="p-3 border-t border-[#1C2033]">
        {/* User profile & Logout */}
        {user ? (
          <div className={`flex items-center ${isCollapsed ? "justify-center" : "justify-between"} pt-1`}>
            {!isCollapsed && (
              <div className="flex items-center space-x-2.5 min-w-0">
                <div className="w-8 h-8 rounded-lg bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 flex items-center justify-center text-xs font-bold flex-shrink-0">
                  {user.display_name ? user.display_name[0].toUpperCase() : "U"}
                </div>
                <div className="flex flex-col min-w-0">
                  <span className="text-xs font-semibold text-gray-200 truncate">{user.display_name}</span>
                  <span className="text-[10px] text-gray-500 truncate">{user.email}</span>
                </div>
              </div>
            )}
            <button
              onClick={logout}
              title="Sign Out"
              className="p-2 rounded-lg text-gray-400 hover:text-rose-400 hover:bg-rose-950/20 border border-transparent hover:border-rose-900/30 transition-all flex-shrink-0"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : null}
      </div>
    </aside>
  );
}
