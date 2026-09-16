"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function PricingRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/app/studio");
  }, [router]);

  return null;
}
