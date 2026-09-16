"use client";

import React, { useState, useEffect } from "react";
import Navbar from "@/components/Navbar";
import { apiClient } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { 
  ShieldAlert, 
  Users, 
  Mic2, 
  DollarSign, 
  Activity, 
  Server, 
  AlertCircle,
  CheckCircle2,
  XCircle,
  RefreshCw
} from "lucide-react";
import { useRouter } from "next/navigation";

interface AdminStats {
  total_users: number;
  total_generations: number;
  total_characters_generated: number;
  total_audio_seconds: number;
  active_subscriptions: number;
  total_revenue_estimate: number;
  provider_cost_estimate: number;
  failed_jobs_count: number;
}

interface ProviderHealth {
  name: string;
  status: "healthy" | "unavailable";
  is_fallback: boolean;
}

export default function AdminPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [providers, setProviders] = useState<ProviderHealth[]>([]);
  const [generations, setGenerations] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (user && user.role !== "admin") {
      router.push("/app/studio");
    } else {
      loadAdminData();
    }
  }, [user]);

  const loadAdminData = async () => {
    setIsLoading(true);
    try {
      const [sData, pData, gData] = await Promise.all([
        apiClient<AdminStats>("/admin/stats"),
        apiClient<{ providers: ProviderHealth[] }>("/admin/providers"),
        apiClient<any[]>("/admin/generations"),
      ]);
      setStats(sData);
      setProviders(pData.providers || []);
      setGenerations(gData || []);
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#090A0F] text-gray-100 flex flex-col">
      <Navbar />

      <main className="max-w-7xl w-full mx-auto p-6 space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-2.5">
              <ShieldAlert className="w-6 h-6 text-purple-400" />
              <span>Admin Monitoring Portal</span>
            </h1>
            <p className="text-xs text-gray-400 mt-1">
              Live platform metrics, provider health diagnostics, and system job throughput
            </p>
          </div>

          <button
            onClick={loadAdminData}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-[#141624] hover:bg-[#1A1D2E] text-xs font-semibold text-gray-300 border border-[#23273D] transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Metrics Grid */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-5 rounded-2xl bg-[#12141F] border border-[#202436] space-y-1">
              <div className="flex items-center justify-between text-xs text-gray-400">
                <span>Total Users</span>
                <Users className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="text-2xl font-extrabold text-white">{stats.total_users}</div>
              <div className="text-[11px] text-gray-500">{stats.active_subscriptions} active subscriptions</div>
            </div>

            <div className="p-5 rounded-2xl bg-[#12141F] border border-[#202436] space-y-1">
              <div className="flex items-center justify-between text-xs text-gray-400">
                <span>Generations</span>
                <Mic2 className="w-4 h-4 text-purple-400" />
              </div>
              <div className="text-2xl font-extrabold text-white">{stats.total_generations}</div>
              <div className="text-[11px] text-gray-500">{stats.total_audio_seconds}s total audio</div>
            </div>

            <div className="p-5 rounded-2xl bg-[#12141F] border border-[#202436] space-y-1">
              <div className="flex items-center justify-between text-xs text-gray-400">
                <span>Characters Synthesized</span>
                <Activity className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="text-2xl font-extrabold text-white">
                {stats.total_characters_generated.toLocaleString()}
              </div>
              <div className="text-[11px] text-gray-500">Across all providers</div>
            </div>

            <div className="p-5 rounded-2xl bg-[#12141F] border border-[#202436] space-y-1">
              <div className="flex items-center justify-between text-xs text-gray-400">
                <span>Estimated Margin</span>
                <DollarSign className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-2xl font-extrabold text-emerald-400">
                ${(stats.total_revenue_estimate - stats.provider_cost_estimate).toFixed(2)}
              </div>
              <div className="text-[11px] text-gray-500">
                Rev: ${stats.total_revenue_estimate} | Cost: ${stats.provider_cost_estimate}
              </div>
            </div>
          </div>
        )}

        {/* Provider Health Section */}
        <div className="p-6 rounded-2xl bg-[#12141F] border border-[#202436] shadow-xl space-y-4">
          <div className="flex items-center space-x-2 text-white font-bold text-base">
            <Server className="w-5 h-5 text-indigo-400" />
            <span>TTS Provider Adapter Health</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {providers.map((p) => (
              <div
                key={p.name}
                className="p-4 rounded-xl bg-[#0B0C14] border border-[#1E2235] flex items-center justify-between"
              >
                <div>
                  <h4 className="font-semibold text-sm text-gray-100 capitalize">{p.name}</h4>
                  <span className="text-[11px] text-gray-500">
                    {p.is_fallback ? "Local Fallback Provider" : "External Provider"}
                  </span>
                </div>
                <div className="flex items-center space-x-1.5 text-xs font-medium">
                  {p.status === "healthy" ? (
                    <span className="flex items-center space-x-1 text-emerald-400">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Online</span>
                    </span>
                  ) : (
                    <span className="flex items-center space-x-1 text-amber-400">
                      <AlertCircle className="w-3.5 h-3.5" />
                      <span>Standby</span>
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent System Generations */}
        <div className="bg-[#12141F] border border-[#202436] rounded-2xl overflow-hidden shadow-xl">
          <div className="p-5 border-b border-[#1E2235] font-bold text-sm text-white">
            System Generations Feed
          </div>
          <table className="w-full text-left text-xs text-gray-300">
            <thead className="bg-[#0B0C14] text-gray-400 font-semibold border-b border-[#202436]">
              <tr>
                <th className="px-5 py-3">Gen ID</th>
                <th className="px-5 py-3">Voice</th>
                <th className="px-5 py-3">Characters</th>
                <th className="px-5 py-3">Est. Cost</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1A1D2E]">
              {generations.map((g) => (
                <tr key={g.id} className="hover:bg-[#151726]">
                  <td className="px-5 py-3.5 font-mono text-gray-400">{g.id.slice(0, 8)}...</td>
                  <td className="px-5 py-3.5 font-semibold text-white">{g.voice_name}</td>
                  <td className="px-5 py-3.5 font-mono">{g.input_characters}</td>
                  <td className="px-5 py-3.5 font-mono text-emerald-400">${g.estimated_cost}</td>
                  <td className="px-5 py-3.5 capitalize">{g.status}</td>
                  <td className="px-5 py-3.5 text-gray-400">
                    {new Date(g.created_at).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
