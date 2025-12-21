"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type HealthResponse = {
  status: string;
  message?: string;
};

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        const res = await fetch("http://127.0.0.1:8000/health", {
          signal: controller.signal,
        });
        
        clearTimeout(timeoutId);
        
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        
        const data = await res.json();
        setHealth(data);
      } catch (err) {
        console.error("Failed to fetch health:", err);
        setHealth({ status: "error", message: err instanceof Error ? err.message : "Unknown error" });
      }
    };

    fetchHealth();
  }, []);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="flex flex-col items-center justify-center min-h-[calc(100vh-4rem)] px-4">
        <h1 className="text-4xl font-bold mb-4 bg-gradient-to-r from-emerald-400 to-blue-400 bg-clip-text text-transparent">
          Cloud Cost Optimizer
        </h1>
        <p className="mb-6 text-slate-400">AI-powered infrastructure cost optimization</p>
        <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-6 mb-8 max-w-2xl w-full">
          <h2 className="text-lg font-semibold mb-3 text-slate-200">Backend Health Status</h2>
          <pre className="bg-slate-950 px-4 py-3 rounded-lg text-sm overflow-x-auto">
            {health ? JSON.stringify(health, null, 2) : "Loading..."}
          </pre>
        </div>
        <div className="flex gap-4 flex-wrap justify-center">
          <Link
            href="/instances"
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors font-medium"
          >
            View Instances
          </Link>
          <Link
            href="/recommendations"
            className="px-6 py-3 bg-emerald-600 hover:bg-emerald-700 rounded-lg transition-colors font-medium"
          >
            Recommendations
          </Link>
          <Link
            href="/analytics"
            className="px-6 py-3 bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors font-medium"
          >
            Analytics
          </Link>
        </div>
      </div>
    </main>
  );
}
