"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function BillingRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/app/studio");
  }, [router]);

  return null;
}
