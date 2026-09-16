"use client";

import React, { Suspense } from "react";
import Sidebar from "@/components/Sidebar";
import { usePathname } from "next/navigation";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isImagePrompts = pathname?.startsWith("/app/image-prompts");

  if (isImagePrompts) {
    return (
      <div className="min-h-screen w-full bg-[#07080D] overflow-x-hidden text-gray-100 flex flex-col">
        {children}
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#07080D]">
      <Suspense fallback={<div className="w-64 bg-[#0A0B10] border-r border-[#1E2333]/80 shrink-0 hidden md:block" />}>
        <Sidebar />
      </Suspense>
      <main className="flex-1 flex flex-col min-w-0 h-full overflow-y-auto relative bg-[#07080D]">
        {children}
      </main>
    </div>
  );
}
