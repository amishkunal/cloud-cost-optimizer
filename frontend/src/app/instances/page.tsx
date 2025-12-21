"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type Instance = {
  id: number;
  cloud_instance_id: string;
  cloud_provider: string;
  region?: string;
  instance_type?: string;
  environment?: string;
  hourly_cost?: number;
};

export default function InstancesPage() {
  const [instances, setInstances] = useState<Instance[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchInstances = async () => {
      try {
        const res = await fetch("http://localhost:8000/instances");
        const data = await res.json();
        setInstances(data);
      } catch (err) {
        console.error("Failed to fetch instances", err);
      } finally {
        setLoading(false);
      }
    };

    fetchInstances();
  }, []);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-8">
      <h1 className="text-3xl font-bold mb-6">Instances</h1>
      {loading ? (
        <p>Loading...</p>
      ) : (
        <table className="min-w-full text-sm border border-slate-700 rounded-lg overflow-hidden">
          <thead className="bg-slate-900">
            <tr>
              <th className="px-4 py-2 text-left">ID</th>
              <th className="px-4 py-2 text-left">Cloud ID</th>
              <th className="px-4 py-2 text-left">Type</th>
              <th className="px-4 py-2 text-left">Env</th>
              <th className="px-4 py-2 text-left">Region</th>
              <th className="px-4 py-2 text-left">Hourly Cost</th>
            </tr>
          </thead>
          <tbody>
            {instances.map((inst) => (
              <tr
                key={inst.id}
                className="border-t border-slate-800 hover:bg-slate-900/60 transition-colors"
              >
                <td className="px-4 py-2">
                  <Link
                    href={`/instances/${inst.id}`}
                    className="text-blue-400 hover:underline"
                  >
                    {inst.id}
                  </Link>
                </td>
                <td className="px-4 py-2">{inst.cloud_instance_id}</td>
                <td className="px-4 py-2">{inst.instance_type}</td>
                <td className="px-4 py-2">{inst.environment}</td>
                <td className="px-4 py-2">{inst.region}</td>
                <td className="px-4 py-2">
                  {inst.hourly_cost != null
                    ? `$${inst.hourly_cost.toFixed(3)}`
                    : "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
