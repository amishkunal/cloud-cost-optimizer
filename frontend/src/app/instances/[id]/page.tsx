"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
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

type Instance = {
  id: number;
  cloud_instance_id: string;
  cloud_provider: string;
  region?: string;
  instance_type?: string;
  environment?: string;
  hourly_cost?: number;
};

type Metric = {
  timestamp: string;
  cpu_utilization?: number | null;
  mem_utilization?: number | null;
  network_in_bytes?: number | null;
  network_out_bytes?: number | null;
};

export default function InstanceDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [instance, setInstance] = useState<Instance | null>(null);
  const [metrics, setMetrics] = useState<Metric[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // Fetch instance and metrics in parallel
        const [instanceRes, metricsRes] = await Promise.all([
          fetch(`http://localhost:8000/instances/${id}`),
          fetch(`http://localhost:8000/instances/${id}/metrics?days=3`),
        ]);

        if (instanceRes.status === 404) {
          setNotFound(true);
          return;
        }

        if (!instanceRes.ok) {
          throw new Error(`Failed to fetch instance: ${instanceRes.status}`);
        }

        const instanceData = await instanceRes.json();
        setInstance(instanceData);

        if (metricsRes.ok) {
          const metricsData = await metricsRes.json();
          setMetrics(metricsData);
        }
      } catch (err) {
        console.error("Failed to fetch data", err);
        if (err instanceof Error && err.message.includes("404")) {
          setNotFound(true);
        }
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchData();
    }
  }, [id]);

  // Format timestamp for display
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // Prepare chart data
  const chartData = {
    labels: metrics.map((m) => formatTimestamp(m.timestamp)),
    datasets: [
      {
        label: "CPU Utilization (%)",
        data: metrics.map((m) => Number(m.cpu_utilization ?? 0)),
        borderColor: "rgb(59, 130, 246)", // blue-500
        backgroundColor: "rgba(59, 130, 246, 0.1)",
        tension: 0.25,
        pointRadius: 3,
        pointHoverRadius: 5,
      },
      {
        label: "Memory Utilization (%)",
        data: metrics.map((m) => Number(m.mem_utilization ?? 0)),
        borderColor: "rgb(34, 197, 94)", // green-500
        backgroundColor: "rgba(34, 197, 94, 0.1)",
        tension: 0.25,
        pointRadius: 3,
        pointHoverRadius: 5,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        labels: {
          color: "rgb(203, 213, 225)", // slate-300
        },
      },
      tooltip: {
        backgroundColor: "rgba(15, 23, 42, 0.9)", // slate-900
        titleColor: "rgb(203, 213, 225)",
        bodyColor: "rgb(203, 213, 225)",
        borderColor: "rgb(71, 85, 105)", // slate-600
        borderWidth: 1,
      },
    },
    scales: {
      x: {
        ticks: {
          color: "rgb(148, 163, 184)", // slate-400
        },
        grid: {
          color: "rgba(71, 85, 105, 0.3)", // slate-600 with opacity
        },
      },
      y: {
        ticks: {
          color: "rgb(148, 163, 184)", // slate-400
        },
        grid: {
          color: "rgba(71, 85, 105, 0.3)", // slate-600 with opacity
        },
        beginAtZero: true,
        max: 100,
      },
    },
  };

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-950 text-slate-100 p-8">
        <div className="flex items-center justify-center min-h-[60vh]">
          <p className="text-slate-400">Loading instance details...</p>
        </div>
      </main>
    );
  }

  if (notFound || !instance) {
    return (
      <main className="min-h-screen bg-slate-950 text-slate-100 p-8">
        <div className="flex flex-col items-center justify-center min-h-[60vh]">
          <h1 className="text-2xl font-bold mb-4">Instance Not Found</h1>
          <p className="text-slate-400 mb-6">
            The instance with ID {id} could not be found.
          </p>
          <Link
            href="/instances"
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            Back to Instances
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Back button */}
        <Link
          href="/instances"
          className="inline-flex items-center text-blue-400 hover:text-blue-300 mb-6 transition-colors"
        >
          ← Back to Instances
        </Link>

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-4">
            Instance: {instance.cloud_instance_id}
          </h1>
          <div className="flex flex-wrap gap-4 text-sm text-slate-300">
            {instance.instance_type && (
              <div>
                <span className="text-slate-500">Type:</span>{" "}
                {instance.instance_type}
              </div>
            )}
            {instance.environment && (
              <div>
                <span className="text-slate-500">Environment:</span>{" "}
                <span
                  className={`px-2 py-1 rounded ${
                    instance.environment === "prod"
                      ? "bg-red-900/30 text-red-300"
                      : "bg-blue-900/30 text-blue-300"
                  }`}
                >
                  {instance.environment}
                </span>
              </div>
            )}
            {instance.region && (
              <div>
                <span className="text-slate-500">Region:</span> {instance.region}
              </div>
            )}
            {instance.hourly_cost != null && (
              <div>
                <span className="text-slate-500">Hourly Cost:</span> $
                {instance.hourly_cost.toFixed(3)}
              </div>
            )}
            <div>
              <Link
                href={`/actions?instance_id=${instance.id}`}
                className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs transition-colors"
              >
                View Actions →
              </Link>
            </div>
          </div>
        </div>

        {/* Metrics Chart */}
        <div className="bg-slate-900 rounded-lg border border-slate-700 p-6">
          <h2 className="text-xl font-semibold mb-4">Utilization Metrics (Last 3 Days)</h2>
          {metrics.length === 0 ? (
            <div className="flex items-center justify-center h-64">
              <p className="text-slate-400">No metrics available for this instance.</p>
            </div>
          ) : (
            <div className="h-96">
              <Line data={chartData} options={chartOptions} />
            </div>
          )}
        </div>
      </div>
    </main>
  );
}





