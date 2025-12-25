"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

type RightSizingAction = {
  id: number;
  instance_id: number;
  cloud_provider: string;
  cloud_instance_id: string;
  region?: string | null;
  old_instance_type?: string | null;
  new_instance_type?: string | null;
  status: "pending" | "verified" | "mismatch" | "error" | string;
  error_message?: string | null;
  requested_at: string;
  verified_at?: string | null;
};

function StatusPill({ status }: { status: RightSizingAction["status"] }) {
  const cls = useMemo(() => {
    switch (status) {
      case "verified":
        return "bg-emerald-900/30 text-emerald-300 border-emerald-500/30";
      case "mismatch":
        return "bg-amber-900/30 text-amber-300 border-amber-500/30";
      case "error":
        return "bg-red-900/30 text-red-300 border-red-500/30";
      case "pending":
      default:
        return "bg-slate-800/50 text-slate-200 border-slate-600/40";
    }
  }, [status]);

  return (
    <span className={`inline-flex px-2 py-1 rounded border text-xs ${cls}`}>
      {status}
    </span>
  );
}

export default function ActionsPage() {
  const searchParams = useSearchParams();
  const initialInstanceId = searchParams.get("instance_id") ?? "";

  const [actions, setActions] = useState<RightSizingAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [instanceId, setInstanceId] = useState(initialInstanceId);
  const [newType, setNewType] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [refreshTick, setRefreshTick] = useState(0);

  const apiBase = "http://localhost:8000";

  const fetchActions = async () => {
    setLoading(true);
    setError(null);
    try {
      const qs = instanceId ? `?instance_id=${encodeURIComponent(instanceId)}` : "";
      const res = await fetch(`${apiBase}/actions${qs}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`Failed to fetch actions: ${res.status}`);
      const data = (await res.json()) as RightSizingAction[];
      setActions(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch actions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchActions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshTick]);

  useEffect(() => {
    // If instance_id query param is present on load, keep the input in sync
    if (initialInstanceId && initialInstanceId !== instanceId) {
      setInstanceId(initialInstanceId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialInstanceId]);

  const createAction = async () => {
    const parsedId = Number(instanceId);
    if (!Number.isFinite(parsedId) || parsedId <= 0) {
      setError("Instance ID must be a positive integer.");
      return;
    }
    if (!newType.trim()) {
      setError("New instance type is required.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/actions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instance_id: parsedId, new_instance_type: newType.trim() }),
      });
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(`Create failed: ${res.status} ${msg}`);
      }
      setNewType("");
      setRefreshTick((x) => x + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create action");
    } finally {
      setSubmitting(false);
    }
  };

  const verifyAction = async (actionId: number) => {
    setError(null);
    try {
      const res = await fetch(`${apiBase}/actions/${actionId}/verify`, { method: "POST" });
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(`Verify failed: ${res.status} ${msg}`);
      }
      setRefreshTick((x) => x + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to verify action");
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-start justify-between gap-4 mb-6">
          <div>
            <h1 className="text-3xl font-bold">Actions</h1>
            <p className="text-slate-400 text-sm mt-1">
              Track applied right-sizing and verify instance type against live AWS.
            </p>
          </div>
          <button
            onClick={() => setRefreshTick((x) => x + 1)}
            className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-sm transition-colors"
          >
            Refresh
          </button>
        </div>

        {/* Create */}
        <div className="bg-slate-900 rounded-lg border border-slate-700 p-5 mb-6">
          <h2 className="text-lg font-semibold mb-3">Create action</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-slate-400">Instance ID</label>
              <input
                value={instanceId}
                onChange={(e) => setInstanceId(e.target.value)}
                placeholder="e.g., 89"
                className="mt-1 w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-sm"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400">New instance type</label>
              <input
                value={newType}
                onChange={(e) => setNewType(e.target.value)}
                placeholder="e.g., t3.small"
                className="mt-1 w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-sm"
              />
            </div>
            <div className="flex items-end">
              <button
                disabled={submitting}
                onClick={createAction}
                className="w-full px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60 transition-colors text-sm font-medium"
              >
                {submitting ? "Creating..." : "Create"}
              </button>
            </div>
          </div>
          {error && <p className="text-red-300 text-sm mt-3">{error}</p>}
        </div>

        {/* List */}
        <div className="bg-slate-900 rounded-lg border border-slate-700 overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Recent actions</h2>
            <div className="text-xs text-slate-400">
              Showing {actions.length} {instanceId ? `for instance ${instanceId}` : "total"}
            </div>
          </div>

          {loading ? (
            <div className="p-6 text-slate-400">Loading...</div>
          ) : actions.length === 0 ? (
            <div className="p-6 text-slate-400">No actions found.</div>
          ) : (
            <table className="min-w-full text-sm">
              <thead className="bg-slate-950/40">
                <tr className="text-slate-300">
                  <th className="px-4 py-3 text-left">ID</th>
                  <th className="px-4 py-3 text-left">Instance</th>
                  <th className="px-4 py-3 text-left">Region</th>
                  <th className="px-4 py-3 text-left">Old → New</th>
                  <th className="px-4 py-3 text-left">Status</th>
                  <th className="px-4 py-3 text-left">Verified</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {actions.map((a) => (
                  <tr
                    key={a.id}
                    className="border-t border-slate-800 hover:bg-slate-950/30"
                    title={a.error_message ?? undefined}
                  >
                    <td className="px-4 py-3">{a.id}</td>
                    <td className="px-4 py-3">
                      <div className="text-slate-100">{a.cloud_instance_id}</div>
                      <div className="text-xs text-slate-500">db id: {a.instance_id}</div>
                    </td>
                    <td className="px-4 py-3">{a.region ?? "-"}</td>
                    <td className="px-4 py-3">
                      <span className="text-slate-300">
                        {a.old_instance_type ?? "?"} → {a.new_instance_type ?? "?"}
                      </span>
                      {a.error_message && (
                        <div className="text-xs text-slate-500 mt-1 truncate max-w-[36ch]">
                          {a.error_message}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <StatusPill status={a.status} />
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      {a.verified_at ? new Date(a.verified_at).toLocaleString() : "-"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => verifyAction(a.id)}
                        className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs transition-colors"
                      >
                        Verify
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </main>
  );
}


