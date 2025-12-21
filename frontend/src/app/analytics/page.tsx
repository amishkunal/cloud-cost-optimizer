"use client";

import { useEffect, useState } from "react";
import { RefreshCw, ChevronDown, ChevronUp, Sparkles } from "lucide-react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";
import { Bar } from "react-chartjs-2";

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

type EnvironmentBreakdown = {
  env: string;
  baseline: number;
  optimized: number;
};

type AnalyticsSummary = {
  instance_count: number;
  downsize_count: number;
  total_baseline_monthly_cost: number;
  total_optimized_monthly_cost: number;
  total_monthly_savings: number;
  model_version: string;
  validation_accuracy: number;
  last_trained_at: string;
  training_runtime_sec: number | null;
  recommendations_requests: number;
  env_breakdown: EnvironmentBreakdown[];
};

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [aiSummary, setAiSummary] = useState<string | null>(null);
  const [loadingAiSummary, setLoadingAiSummary] = useState(false);
  const [showAiPanel, setShowAiPanel] = useState(false);

  const fetchSummary = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch("http://localhost:8000/analytics/summary");

      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      const data = await res.json();
      setSummary(data);
    } catch (err) {
      console.error("Failed to fetch analytics", err);
      setError("Failed to load analytics. Please check if the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  const refreshMetadata = async () => {
    try {
      setRefreshing(true);
      const res = await fetch("http://localhost:8000/ml/metadata");
      if (res.ok) {
        const metadata = await res.json();
        // Update summary with new metadata
        setSummary((prev) =>
          prev
            ? {
                ...prev,
                model_version: metadata.model_version || prev.model_version,
                validation_accuracy: metadata.validation_accuracy ?? prev.validation_accuracy,
                last_trained_at: metadata.trained_at || prev.last_trained_at,
                training_runtime_sec: metadata.training_runtime_sec ?? prev.training_runtime_sec,
              }
            : prev
        );
      }
    } catch (err) {
      console.error("Failed to refresh metadata", err);
    } finally {
      setRefreshing(false);
    }
  };

  const fetchAiSummary = async () => {
    try {
      setLoadingAiSummary(true);
      const res = await fetch("http://localhost:8000/analytics/ai_summary");
      if (res.ok) {
        const data = await res.json();
        setAiSummary(data.summary);
        setShowAiPanel(true);
      } else if (res.status === 503) {
        setAiSummary("AI summaries are not available (missing API key).");
      } else {
        setAiSummary("Failed to generate AI summary.");
      }
    } catch (err) {
      console.error("Failed to fetch AI summary", err);
      setAiSummary("Failed to generate AI summary. Please try again later.");
    } finally {
      setLoadingAiSummary(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  const formatDate = (isoString: string) => {
    if (isoString === "unknown") return "Unknown";
    try {
      const date = new Date(isoString);
      return date.toLocaleString();
    } catch {
      return isoString;
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Analytics</h1>
            <p className="text-slate-400">
              System-level performance and model metrics.
            </p>
          </div>
          <button
            onClick={refreshMetadata}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
            <span>Refresh Metadata</span>
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <p className="text-slate-400">Loading analytics...</p>
          </div>
        ) : error ? (
          <div className="bg-red-900/20 border border-red-500/40 rounded-lg p-4 text-red-300">
            {error}
          </div>
        ) : summary ? (
          <>
            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4">
                <div className="text-sm text-slate-400 mb-1">Total Baseline Cost</div>
                <div className="text-2xl font-bold text-slate-100">
                  ${summary.total_baseline_monthly_cost.toFixed(2)}
                </div>
                <div className="text-xs text-slate-500 mt-1">per month</div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4">
                <div className="text-sm text-slate-400 mb-1">Total Optimized Cost</div>
                <div className="text-2xl font-bold text-emerald-400">
                  ${summary.total_optimized_monthly_cost.toFixed(2)}
                </div>
                <div className="text-xs text-slate-500 mt-1">per month</div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4">
                <div className="text-sm text-slate-400 mb-1">Total Monthly Savings</div>
                <div className="text-2xl font-bold text-emerald-300">
                  ${summary.total_monthly_savings.toFixed(2)}
                </div>
                <div className="text-xs text-slate-500 mt-1">projected</div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4">
                <div className="text-sm text-slate-400 mb-1">Downsize Rate</div>
                <div className="text-2xl font-bold text-slate-100">
                  {summary.instance_count > 0
                    ? ((summary.downsize_count / summary.instance_count) * 100).toFixed(1)
                    : "0.0"}
                  %
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  {summary.downsize_count} / {summary.instance_count} instances
                </div>
              </div>
            </div>

            {/* Model Metrics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4">
                <div className="text-sm text-slate-400 mb-1">Model Version</div>
                <div className="text-lg font-semibold text-slate-100">{summary.model_version}</div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4">
                <div className="text-sm text-slate-400 mb-1">Validation Accuracy</div>
                <div className="text-lg font-semibold text-slate-100">
                  {(summary.validation_accuracy * 100).toFixed(1)}%
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4">
                <div className="text-sm text-slate-400 mb-1">Training Runtime</div>
                <div className="text-lg font-semibold text-slate-100">
                  {summary.training_runtime_sec != null
                    ? `${summary.training_runtime_sec.toFixed(2)}s`
                    : "N/A"}
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4">
                <div className="text-sm text-slate-400 mb-1">API Requests</div>
                <div className="text-lg font-semibold text-slate-100">
                  {summary.recommendations_requests}
                </div>
                <div className="text-xs text-slate-500 mt-1">since startup</div>
              </div>
            </div>

            {/* Training Info */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 mb-8">
              <div className="text-sm text-slate-400 mb-1">Last Trained At</div>
              <div className="text-slate-100">{formatDate(summary.last_trained_at)}</div>
            </div>

            {/* Cost Comparison Chart */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Cost Comparison</h2>
              <div className="h-96">
                <Bar
                  data={{
                    labels: ["Monthly Costs"],
                    datasets: [
                      {
                        label: "Baseline Cost",
                        data: [summary.total_baseline_monthly_cost],
                        backgroundColor: "rgba(148, 163, 184, 0.6)", // slate-400
                        borderColor: "rgb(148, 163, 184)",
                        borderWidth: 1,
                      },
                      {
                        label: "Optimized Cost",
                        data: [summary.total_optimized_monthly_cost],
                        backgroundColor: "rgba(34, 197, 94, 0.6)", // green-500
                        borderColor: "rgb(34, 197, 94)",
                        borderWidth: 1,
                      },
                      {
                        label: "Savings",
                        data: [summary.total_monthly_savings],
                        backgroundColor: "rgba(34, 197, 94, 0.8)", // green-500
                        borderColor: "rgb(34, 197, 94)",
                        borderWidth: 1,
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
                        callbacks: {
                          label: function (context) {
                            return `${context.dataset.label}: $${context.parsed.y.toFixed(2)}`;
                          },
                        },
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
                        beginAtZero: true,
                      },
                    },
                  }}
                />
              </div>
            </div>

            {/* Environment Breakdown Chart */}
            {summary.env_breakdown && summary.env_breakdown.length > 0 && (
              <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-6 mt-8">
                <h2 className="text-xl font-semibold mb-4">Cost Breakdown by Environment</h2>
                <div className="h-96">
                  <Bar
                    data={{
                      labels: summary.env_breakdown.map((e) => e.env),
                      datasets: [
                        {
                          label: "Baseline Cost",
                          data: summary.env_breakdown.map((e) => e.baseline),
                          backgroundColor: "rgba(148, 163, 184, 0.6)", // slate-400
                          borderColor: "rgb(148, 163, 184)",
                          borderWidth: 1,
                        },
                        {
                          label: "Optimized Cost",
                          data: summary.env_breakdown.map((e) => e.optimized),
                          backgroundColor: "rgba(34, 197, 94, 0.6)", // green-500
                          borderColor: "rgb(34, 197, 94)",
                          borderWidth: 1,
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
                          callbacks: {
                            label: function (context) {
                              return `${context.dataset.label}: $${context.parsed.y.toFixed(2)}`;
                            },
                          },
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
                          beginAtZero: true,
                        },
                      },
                    }}
                  />
                </div>
              </div>
            )}

            {/* AI Summary Panel */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-lg mt-8 overflow-hidden">
              <button
                onClick={() => {
                  setShowAiPanel(!showAiPanel);
                  if (!showAiPanel && !aiSummary && !loadingAiSummary) {
                    fetchAiSummary();
                  }
                }}
                className="w-full flex items-center justify-between p-4 hover:bg-slate-800/40 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <Sparkles className="w-5 h-5 text-emerald-400" />
                  <h2 className="text-xl font-semibold">AI Summary</h2>
                </div>
                {showAiPanel ? (
                  <ChevronUp className="w-5 h-5 text-slate-400" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-slate-400" />
                )}
              </button>
              
              {showAiPanel && (
                <div className="p-6 border-t border-slate-800">
                  {loadingAiSummary ? (
                    <div className="flex items-center justify-center py-8">
                      <RefreshCw className="w-6 h-6 text-emerald-400 animate-spin mr-3" />
                      <span className="text-slate-400">Generating AI summary...</span>
                    </div>
                  ) : aiSummary ? (
                    <div className="text-slate-300 leading-relaxed">
                      {aiSummary}
                    </div>
                  ) : (
                    <div className="text-slate-400 text-center py-4">
                      Click to generate AI summary
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        ) : null}
      </div>
    </main>
  );
}

