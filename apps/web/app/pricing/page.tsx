"use client";

import Link from "next/link";
import { Mic2, Check, ArrowRight } from "lucide-react";

export default function PricingPage() {
  const tiers = [
    {
      name: "Free",
      price: "$0",
      description: "For personal experimentation and testing speech synthesis.",
      characters: "10,000 chars/mo",
      cloning: false,
      premium: false,
      api: false,
      cta: "Get Started Free",
      href: "/signup",
    },
    {
      name: "Starter",
      price: "$9",
      description: "Ideal for solo creators and hobby projects.",
      characters: "50,000 chars/mo",
      cloning: false,
      premium: false,
      api: true,
      cta: "Choose Starter",
      href: "/signup",
    },
    {
      name: "Creator",
      price: "$29",
      popular: true,
      description: "For podcasters, YouTubers, and content studios.",
      characters: "250,000 chars/mo",
      cloning: true,
      premium: true,
      api: true,
      cta: "Choose Creator",
      href: "/signup",
    },
    {
      name: "Pro",
      price: "$79",
      description: "Higher throughput and Ultra neural voices.",
      characters: "1,000,000 chars/mo",
      cloning: true,
      premium: true,
      api: true,
      cta: "Choose Pro",
      href: "/signup",
    },
    {
      name: "Unlimited",
      price: "$149",
      description: "Fair-use unlimited compute for power studios.",
      characters: "5,000,000 fair-use chars",
      cloning: true,
      premium: true,
      api: true,
      cta: "Choose Unlimited",
      href: "/signup",
    },
  ];

  return (
    <div className="min-h-screen bg-[#090A0F] text-gray-100 flex flex-col">
      {/* Header */}
      <header className="border-b border-[#1E2235] bg-[#0E101A]/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/25">
              <Mic2 className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-gray-200 to-indigo-300 bg-clip-text text-transparent">
              HK Speaks
            </span>
          </Link>

          <div className="flex items-center space-x-4">
            <Link href="/login" className="text-sm text-gray-400 hover:text-white transition-colors">
              Sign In
            </Link>
            <Link
              href="/signup"
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition-all"
            >
              Get Started
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl w-full mx-auto px-6 py-16 space-y-12 flex-1">
        <div className="text-center max-w-2xl mx-auto space-y-3">
          <h1 className="text-4xl sm:text-5xl font-extrabold text-white tracking-tight">
            Transparent, Predictable Pricing
          </h1>
          <p className="text-sm text-gray-400">
            Select a tier designed for your scale. Every plan includes studio access and MP3/WAV export.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-5">
          {tiers.map((t) => (
            <div
              key={t.name}
              className={`p-6 rounded-2xl bg-[#12141F] border flex flex-col justify-between space-y-6 ${
                t.popular
                  ? "border-indigo-500 shadow-xl shadow-indigo-600/20"
                  : "border-[#202436]"
              }`}
            >
              <div>
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-lg text-white">{t.name}</h3>
                  {t.popular && (
                    <span className="px-2 py-0.5 text-[10px] font-bold bg-indigo-600 text-white rounded-full">
                      Popular
                    </span>
                  )}
                </div>

                <div className="mt-3 text-3xl font-extrabold text-white">
                  {t.price}
                  <span className="text-xs font-normal text-gray-400">/mo</span>
                </div>

                <p className="text-xs text-gray-400 mt-2 leading-relaxed">{t.description}</p>

                <ul className="mt-6 space-y-2.5 text-xs text-gray-300">
                  <li className="flex items-center space-x-2">
                    <Check className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>{t.characters}</span>
                  </li>
                  <li className="flex items-center space-x-2">
                    <Check className={`w-4 h-4 ${t.premium ? "text-emerald-400" : "text-gray-600"} shrink-0`} />
                    <span className={t.premium ? "" : "text-gray-500"}>Premium Voices</span>
                  </li>
                  <li className="flex items-center space-x-2">
                    <Check className={`w-4 h-4 ${t.cloning ? "text-emerald-400" : "text-gray-600"} shrink-0`} />
                    <span className={t.cloning ? "" : "text-gray-500"}>Voice Cloning</span>
                  </li>
                  <li className="flex items-center space-x-2">
                    <Check className={`w-4 h-4 ${t.api ? "text-emerald-400" : "text-gray-600"} shrink-0`} />
                    <span className={t.api ? "" : "text-gray-500"}>Developer API</span>
                  </li>
                </ul>
              </div>

              <Link
                href={t.href}
                className={`w-full py-2.5 rounded-xl text-center text-xs font-semibold transition-all ${
                  t.popular
                    ? "bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30"
                    : "bg-[#181B2B] hover:bg-[#22273D] text-gray-200 border border-[#2A304C]"
                }`}
              >
                {t.cta}
              </Link>
            </div>
          ))}
        </div>
      </main>

      <footer className="border-t border-[#1E2235] py-8 text-center text-xs text-gray-500">
        <p>© 2026 HK Speaks. All rights reserved.</p>
      </footer>
    </div>
  );
}
