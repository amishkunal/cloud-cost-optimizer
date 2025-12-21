"use client";

import { useEffect, useState } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Line } from "react-chartjs-2";

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

type Recommendation = {
  instance_id: number;
  cloud_instance_id: string;
  environment?: string | null;
  region?: string | null;
  instance_type?: string | null;
  hourly_cost?: number | null;
  action: "keep" | "downsize" | string;
  confidence_downsize: number;
  projected_monthly_savings: number;
  model_version: string;
  reasons: string[];
};

type CostTrendData = {
  days: string[];
  baseline_daily_cost: number[];
  optimized_daily_cost: number[];
};

type LLMExplanation = {
  instance_id: number;
  cloud_instance_id: string;
  llm_explanation: string;
};

export default function RecommendationsPage() {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [minSavings, setMinSavings] = useState(0);
  const [environment, setEnvironment] = useState<string>("");
  const [region, setRegion] = useState<string>("");
  const [instanceType, setInstanceType] = useState<string>("");
  const [trendData, setTrendData] = useState<CostTrendData | null>(null);
  const [llmExplanations, setLlmExplanations] = useState<Record<number, string>>({});
  const [loadingLLM, setLoadingLLM] = useState<Record<number, boolean>>({});

  useEffect(() => {
    const fetchRecommendations = async () => {
      try {
        setLoading(true);
        setError(null);
        const params = new URLSearchParams({
          min_savings: minSavings.toString(),
        });
        if (environment) params.append("environment", environment);
        if (region) params.append("region", region);
        if (instanceType) params.append("instance_type", instanceType);

        const url = `http://localhost:8000/recommendations?${params.toString()}`;
        const res = await fetch(url);

        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }

        const data = await res.json();
        setRecommendations(data);
      } catch (err) {
        console.error("Failed to fetch recommendations", err);
        setError(
          "Failed to load recommendations. Please check if the backend is running on http://localhost:8000."
        );
      } finally {
        setLoading(false);
      }
    };

    fetchRecommendations();
  }, [minSavings, environment, region, instanceType]);

  useEffect(() => {
    const fetchTrendData = async () => {
      try {
        const res = await fetch("http://localhost:8000/cost_trends/total?lookback_days=30");
        if (res.ok) {
          const data = await res.json();
          setTrendData(data);
        }
      } catch (err) {
        console.error("Failed to fetch trend data", err);
      }
    };

    fetchTrendData();
  }, []);

  const fetchLLMExplanation = async (instanceId: number) => {
    try {
      setLoadingLLM((prev) => ({ ...prev, [instanceId]: true }));
      const res = await fetch(`http://localhost:8000/recommendations/${instanceId}/llm_explanation`);

      if (!res.ok) {
        let errorMessage = "Failed to generate explanation.";
        
        if (res.status === 503) {
          errorMessage = "LLM explanations are not available (missing API key).";
        } else if (res.status === 404) {
          errorMessage = "Instance not found or has no metrics.";
        } else if (res.status === 500) {
          // Try to get error details from response
          try {
            const errorData = await res.json();
            const detail = errorData.detail || "";
            // Check for API key errors and simplify the message
            if (detail.includes("Invalid OpenAI API key") || detail.includes("invalid_api_key")) {
              errorMessage = "Invalid OpenAI API key. Please check your API key configuration.";
            } else if (detail.includes("Error generating LLM explanation")) {
              // Extract a cleaner error message
              errorMessage = "Failed to generate explanation. Please verify your OpenAI API key is valid.";
            } else {
              errorMessage = detail || "Server error occurred while generating explanation.";
            }
          } catch {
            errorMessage = "Server error occurred while generating explanation.";
          }
        }

        setLlmExplanations((prev) => ({
          ...prev,
          [instanceId]: errorMessage,
        }));
        return;
      }

      const data: LLMExplanation = await res.json();
      setLlmExplanations((prev) => ({
        ...prev,
        [instanceId]: data.llm_explanation,
      }));
    } catch (err) {
      console.error("Failed to fetch LLM explanation", err);
      setLlmExplanations((prev) => ({
        ...prev,
        [instanceId]: "Failed to generate explanation. Please check if the backend is running.",
      }));
    } finally {
      setLoadingLLM((prev) => ({ ...prev, [instanceId]: false }));
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">Recommendations</h1>
          <p className="text-slate-400">
            Model-driven optimization suggestions based on recent utilization.
          </p>
        </div>

        {/* Filter Controls */}
        <div className="mb-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label htmlFor="min-savings" className="block text-sm font-medium text-slate-300 mb-2">
                Minimum Savings
              </label>
              <select
                id="min-savings"
                value={minSavings}
                onChange={(e) => setMinSavings(Number(e.target.value))}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value={0}>$0 (All)</option>
                <option value={10}>$10</option>
                <option value={25}>$25</option>
                <option value={50}>$50</option>
                <option value={100}>$100</option>
              </select>
            </div>
            <div>
              <label htmlFor="environment" className="block text-sm font-medium text-slate-300 mb-2">
                Environment
              </label>
              <select
                id="environment"
                value={environment}
                onChange={(e) => setEnvironment(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">All</option>
                <option value="prod">prod</option>
                <option value="dev">dev</option>
              </select>
            </div>
            <div>
              <label htmlFor="region" className="block text-sm font-medium text-slate-300 mb-2">
                Region
              </label>
              <select
                id="region"
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">All</option>
                <option value="us-west-2">us-west-2</option>
              </select>
            </div>
            <div>
              <label htmlFor="instance-type" className="block text-sm font-medium text-slate-300 mb-2">
                Instance Type
              </label>
              <select
                id="instance-type"
                value={instanceType}
                onChange={(e) => setInstanceType(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">All</option>
                <option value="m5.large">m5.large</option>
              </select>
            </div>
          </div>
        </div>

        {/* Summary Bar */}
        {recommendations.length > 0 && (
          <div className="mb-6 text-sm text-slate-300">
            <span className="font-medium text-emerald-300">
              {recommendations.filter((r) => r.action === "downsize").length} potential downsizes
            </span>{" "}
            detected, with an estimated{" "}
            <span className="font-semibold text-emerald-300">
              ${recommendations.reduce((sum, r) => sum + (r.projected_monthly_savings || 0), 0).toFixed(2)} / month
            </span>{" "}
            in projected savings.
          </div>
        )}

        {/* Trend Chart */}
        {trendData && trendData.days.length > 0 && (
          <div className="mb-8 bg-slate-900/60 border border-slate-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Cost Trend Simulation (Last 30 Days)</h2>
            <div className="h-64">
              <Line
                data={{
                  labels: trendData.days,
                  datasets: [
                    {
                      label: "Baseline Cost",
                      data: trendData.baseline_daily_cost,
                      borderColor: "rgb(148, 163, 184)", // slate-400
                      backgroundColor: "rgba(148, 163, 184, 0.1)",
                      tension: 0.25,
                    },
                    {
                      label: "Optimized Cost",
                      data: trendData.optimized_daily_cost,
                      borderColor: "rgb(34, 197, 94)", // green-500
                      backgroundColor: "rgba(34, 197, 94, 0.1)",
                      tension: 0.25,
                    },
                  ],
                }}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: {
                      labels: {
                        color: "rgb(203, 213, 225)", // slate-300
                      },
                    },
                    tooltip: {
                      backgroundColor: "rgba(15, 23, 42, 0.9)",
                      titleColor: "rgb(203, 213, 225)",
                      bodyColor: "rgb(203, 213, 225)",
                      borderColor: "rgb(71, 85, 105)",
                      borderWidth: 1,
                    },
                  },
                  scales: {
                    x: {
                      ticks: {
                        color: "rgb(148, 163, 184)",
                      },
                      grid: {
                        color: "rgba(71, 85, 105, 0.3)",
                      },
                    },
                    y: {
                      ticks: {
                        color: "rgb(148, 163, 184)",
                        callback: function (value) {
                          return "$" + value;
                        },
                      },
                      grid: {
                        color: "rgba(71, 85, 105, 0.3)",
                      },
                    },
                  },
                }}
              />
            </div>
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <p className="text-slate-400">Loading recommendations...</p>
          </div>
        ) : error ? (
          <div className="bg-red-900/20 border border-red-500/40 rounded-lg p-4 text-red-300">
            {error}
          </div>
        ) : recommendations.length === 0 ? (
          <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-8 text-center">
            <p className="text-slate-400 mb-2">
              No recommendations found for the current filter.
            </p>
            <p className="text-sm text-slate-500">
              Try lowering the minimum savings threshold.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {recommendations.map((rec) => (
              <div
                key={rec.instance_id}
                className={`rounded-2xl p-4 border shadow-sm transition-colors flex flex-col gap-3 ${
                  rec.action === "downsize"
                    ? "border-emerald-600/60 bg-emerald-900/20 hover:border-emerald-600/80 hover:bg-emerald-900/30"
                    : "border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-900"
                }`}
              >
                {/* Top Row: Cloud ID + Action Badge */}
                <div className="flex items-start justify-between">
                  <h3 className="font-bold text-lg text-slate-100">
                    {rec.cloud_instance_id}
                  </h3>
                  {rec.action === "downsize" ? (
                    <span className="px-2 py-1 text-xs rounded-md bg-emerald-600/20 text-emerald-300 border border-emerald-500/40">
                      Downsize
                    </span>
                  ) : (
                    <span className="px-2 py-1 text-xs rounded-md bg-slate-700/60 text-slate-200 border border-slate-500/40">
                      Keep
                    </span>
                  )}
                </div>

                {/* Metadata Row */}
                <div className="space-y-1 text-xs text-slate-400">
                  {rec.instance_type && (
                    <div>
                      <span className="text-slate-500">Type:</span> {rec.instance_type}
                    </div>
                  )}
                  <div className="flex gap-4">
                    {rec.environment && (
                      <div>
                        <span className="text-slate-500">Env:</span> {rec.environment}
                      </div>
                    )}
                    {rec.region && (
                      <div>
                        <span className="text-slate-500">Region:</span> {rec.region}
                      </div>
                    )}
                  </div>
                  <div>
                    <span className="text-slate-500">Hourly cost:</span>{" "}
                    {rec.hourly_cost != null
                      ? `$${rec.hourly_cost.toFixed(3)}/hr`
                      : "—"}
                  </div>
                </div>

                {/* Savings + Confidence */}
                <div className="pt-2 border-t border-slate-800 space-y-2">
                  <div>
                    <span className="text-xs text-slate-500">Projected monthly savings:</span>
                    <div
                      className={`text-lg font-semibold ${
                        rec.projected_monthly_savings === 0
                          ? "text-slate-500"
                          : "text-emerald-400"
                      }`}
                    >
                      ${rec.projected_monthly_savings.toFixed(2)} / month
                    </div>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500">Downsize confidence:</span>
                    <div className="text-sm text-slate-300">
                      {(rec.confidence_downsize * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>

                {/* Reasons */}
                <div className="pt-2 border-t border-slate-800">
                  <div className="text-xs text-slate-500 mb-2">Reasons:</div>
                  {rec.reasons.length > 0 ? (
                    <ul className="space-y-1 text-xs text-slate-400">
                      {rec.reasons.map((reason, idx) => (
                        <li key={idx} className="flex items-start">
                          <span className="mr-2">•</span>
                          <span>{reason}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs text-slate-500 italic">
                      No specific reasons recorded.
                    </p>
                  )}
                </div>

                {/* LLM Explanation */}
                <div className="pt-2 border-t border-slate-800">
                  <button
                    onClick={() => {
                      if (llmExplanations[rec.instance_id]) {
                        setLlmExplanations((prev) => {
                          const newState = { ...prev };
                          delete newState[rec.instance_id];
                          return newState;
                        });
                      } else {
                        fetchLLMExplanation(rec.instance_id);
                      }
                    }}
                    disabled={loadingLLM[rec.instance_id]}
                    className="text-xs text-blue-400 hover:text-blue-300 disabled:text-slate-500 disabled:cursor-not-allowed transition-colors"
                  >
                    {loadingLLM[rec.instance_id]
                      ? "Generating..."
                      : llmExplanations[rec.instance_id]
                        ? "Hide explanation"
                        : "Generate detailed explanation"}
                  </button>
                  {llmExplanations[rec.instance_id] && (
                    <div className="mt-2 text-xs text-slate-400 italic bg-slate-800/50 rounded p-2">
                      {llmExplanations[rec.instance_id]}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

