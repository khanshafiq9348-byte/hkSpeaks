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
  CreditCard,
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

  // Billing usage state for Upgrade card
  const [usage, setUsage] = useState<any>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("hk_sidebar_collapsed");
      if (stored !== null) {
        setIsCollapsed(stored === "true");
      }
    }
    loadUsage();
  }, []);

  const toggleCollapsed = () => {
    const next = !isCollapsed;
    setIsCollapsed(next);
    if (typeof window !== "undefined") {
      localStorage.setItem("hk_sidebar_collapsed", String(next));
    }
  };

  const loadUsage = async () => {
    try {
      const data = await apiClient<any>("/billing/usage");
      setUsage(data);
    } catch {
      // ignore
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
  const isBilling = pathname.startsWith("/app/billing");
  const isPricing = pathname.startsWith("/pricing");

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

        {/* Billing */}
        <Link
          href="/app/billing"
          title="Billing"
          className={`flex items-center rounded-xl transition-all ${
            isCollapsed
              ? "justify-center p-3"
              : "space-x-3 px-3.5 py-2.5"
          } ${
            isBilling
              ? "bg-indigo-600 text-white font-semibold shadow-md shadow-indigo-600/30"
              : "text-gray-300 hover:text-white hover:bg-[#141726]"
          }`}
        >
          <CreditCard className="w-4 h-4 flex-shrink-0" />
          {!isCollapsed && <span className="text-sm font-medium">Billing</span>}
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

      {/* 4. Bottom Section: Upgrade Plan & User Info */}
      <div className="p-3 border-t border-[#1C2033] space-y-2">
        {/* Upgrade Plan Card */}
        {!isCollapsed ? (
          <div className="p-3 rounded-xl bg-gradient-to-br from-[#181B2E] to-[#121422] border border-[#262C47] shadow-inner space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-1.5 text-xs font-semibold text-white">
                <Crown className="w-3.5 h-3.5 text-amber-400" />
                <span>{usage?.plan_name || "Free Tier"}</span>
              </div>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-semibold">
                Active
              </span>
            </div>

            {/* Characters info */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[11px] text-gray-400">
                <span>Credits remaining</span>
                <span className="text-gray-200 font-medium">
                  {usage ? (usage.characters_remaining ?? usage.characters_limit).toLocaleString() : "10,000"}
                </span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-[#20253D] overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-indigo-500 to-purple-500"
                  style={{
                    width: usage && usage.characters_limit > 0
                      ? `${Math.max(5, Math.min(100, ((usage.characters_limit - usage.characters_used) / usage.characters_limit) * 100))}%`
                      : "80%"
                  }}
                />
              </div>
            </div>

            {/* Upgrade CTA Button */}
            <Link
              href="/pricing"
              className="w-full flex items-center justify-center space-x-1.5 py-1.5 rounded-lg text-xs font-bold bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 text-white shadow-md shadow-indigo-600/25 hover:opacity-95 transition-opacity"
            >
              <Crown className="w-3 h-3 text-amber-300" />
              <span>Upgrade Plan</span>
            </Link>
          </div>
        ) : (
          <div className="flex justify-center">
            <Link
              href="/pricing"
              title="Upgrade Plan"
              className="p-2.5 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-600/30 hover:scale-105 transition-transform"
            >
              <Crown className="w-4 h-4 text-amber-300" />
            </Link>
          </div>
        )}

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
