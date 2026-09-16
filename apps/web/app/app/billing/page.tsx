"use client";

import React, { useState, useEffect } from "react";
import { apiClient } from "@/lib/api";
import { CreditCard, Check, Sparkles, Crown, Zap, AlertTriangle, ShieldCheck } from "lucide-react";

interface Plan {
  id: string;
  name: string;
  slug: string;
  description: string;
  monthly_price: number;
  included_characters: number;
  allow_cloning: boolean;
  allow_premium_voices: boolean;
  allow_api: boolean;
  fair_use_limit: number;
}

interface UsageSummary {
  plan_name: string;
  plan_slug: string;
  characters_used: number;
  characters_limit: number;
  characters_remaining: number;
  seconds_used: number;
  generations_count: number;
  fair_use_status: "healthy" | "warning" | "throttled" | string;
  can_clone: boolean;
  can_use_premium: boolean;
  can_use_api: boolean;
}

export default function BillingPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [isUpgrading, setIsUpgrading] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [pData, uData] = await Promise.all([
        apiClient<Plan[]>("/billing/plans"),
        apiClient<UsageSummary>("/billing/usage"),
      ]);
      setPlans(pData);
      setUsage(uData);
    } catch {
      // ignore
    }
  };

  const handleUpgrade = async (slug: string) => {
    if (usage?.plan_slug === slug) return;
    setIsUpgrading(true);
    try {
      await apiClient(`/billing/upgrade?plan_slug=${slug}`, { method: "POST" });
      await loadData();
      alert(`Plan successfully updated to ${slug.toUpperCase()}!`);
    } catch (err: any) {
      alert(err.message || "Failed to upgrade plan.");
    } finally {
      setIsUpgrading(false);
    }
  };

  const pctUsed = usage
    ? Math.min(100, Math.round((usage.characters_used / (usage.characters_limit || 1)) * 100))
    : 0;

  return (
    <div className="flex-1 flex flex-col min-w-0 h-full overflow-y-auto bg-[#090A0F] text-gray-100">
      <main className="max-w-7xl w-full mx-auto p-6 space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-2.5">
            <CreditCard className="w-6 h-6 text-indigo-400" />
            <span>Subscription & Usage</span>
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            Manage your subscription tier, track character consumption, and view fair-use allocations
          </p>
        </div>

        {/* Current Usage Metrics Card */}
        {usage && (
          <div className="p-6 rounded-2xl bg-[#12141F] border border-[#202436] shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-[#1E2235]">
              <div>
                <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">
                  Active Plan
                </span>
                <h3 className="text-xl font-bold text-white flex items-center space-x-2 mt-0.5">
                  <span>{usage.plan_name}</span>
                  {usage.plan_slug === "unlimited" && (
                    <span className="px-2 py-0.5 text-xs bg-purple-500/10 text-purple-400 border border-purple-500/20 rounded-full">
                      Fair-Use Unlimited
                    </span>
                  )}
                </h3>
              </div>

              <div className="flex items-center space-x-4 text-xs font-mono text-gray-300">
                <div>
                  <span className="text-gray-500 block">Total Generations</span>
                  <span className="text-sm font-semibold">{usage.generations_count}</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Audio Generated</span>
                  <span className="text-sm font-semibold">{usage.seconds_used}s</span>
                </div>
                <div>
                  <span className="text-gray-500 block">Fair-Use Status</span>
                  <span
                    className={`text-sm font-semibold capitalize ${
                      usage.fair_use_status === "healthy"
                        ? "text-emerald-400"
                        : usage.fair_use_status === "warning"
                        ? "text-amber-400"
                        : "text-red-400"
                    }`}
                  >
                    {usage.fair_use_status}
                  </span>
                </div>
              </div>
            </div>

            {/* Progress bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-gray-400 font-mono">
                <span>
                  {usage.characters_used.toLocaleString()} / {usage.characters_limit.toLocaleString()} characters used
                </span>
                <span>{usage.characters_remaining.toLocaleString()} remaining ({100 - pctUsed}%)</span>
              </div>
              <div className="w-full h-2.5 bg-[#0B0C14] rounded-full overflow-hidden border border-[#1E2235]">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${
                    pctUsed > 90 ? "bg-red-500" : pctUsed > 75 ? "bg-amber-500" : "bg-indigo-500"
                  }`}
                  style={{ width: `${pctUsed}%` }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Available Plans Grid */}
        <div className="space-y-4">
          <h2 className="text-lg font-bold text-white">Choose a Plan</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {plans.map((p) => {
              const isCurrent = usage?.plan_slug === p.slug;
              return (
                <div
                  key={p.id}
                  className={`p-5 rounded-2xl bg-[#12141F] border flex flex-col justify-between space-y-4 transition-all ${
                    isCurrent
                      ? "border-indigo-500/60 shadow-lg shadow-indigo-600/10"
                      : "border-[#202436] hover:border-[#2C3048]"
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold text-base text-white">{p.name}</h4>
                      {p.slug === "creator" && (
                        <span className="px-2 py-0.5 text-[10px] font-semibold bg-indigo-500/20 text-indigo-300 rounded-full">
                          Popular
                        </span>
                      )}
                    </div>
                    <div className="mt-2 text-2xl font-extrabold text-white">
                      ${p.monthly_price}
                      <span className="text-xs font-normal text-gray-400">/mo</span>
                    </div>
                    <p className="text-xs text-gray-400 mt-2 leading-relaxed">{p.description}</p>

                    <ul className="mt-4 space-y-2 text-xs text-gray-300">
                      <li className="flex items-center space-x-2">
                        <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                        <span>{p.included_characters.toLocaleString()} chars/mo</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <Check className={`w-3.5 h-3.5 ${p.allow_premium_voices ? "text-emerald-400" : "text-gray-600"} shrink-0`} />
                        <span className={p.allow_premium_voices ? "" : "text-gray-500"}>Premium Voices</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <Check className={`w-3.5 h-3.5 ${p.allow_cloning ? "text-emerald-400" : "text-gray-600"} shrink-0`} />
                        <span className={p.allow_cloning ? "" : "text-gray-500"}>Custom Voice Cloning</span>
                      </li>
                      <li className="flex items-center space-x-2">
                        <Check className={`w-3.5 h-3.5 ${p.allow_api ? "text-emerald-400" : "text-gray-600"} shrink-0`} />
                        <span className={p.allow_api ? "" : "text-gray-500"}>Developer API</span>
                      </li>
                    </ul>
                  </div>

                  <button
                    onClick={() => handleUpgrade(p.slug)}
                    disabled={isCurrent || isUpgrading}
                    className={`w-full py-2 rounded-xl text-xs font-semibold transition-all ${
                      isCurrent
                        ? "bg-[#181B2B] text-indigo-400 border border-indigo-500/30 cursor-default"
                        : "bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/20"
                    }`}
                  >
                    {isCurrent ? "Current Plan" : `Upgrade to ${p.name}`}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </main>
    </div>
  );
}
