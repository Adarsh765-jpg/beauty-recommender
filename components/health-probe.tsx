"use client";

import { useEffect, useState } from "react";

type Health = {
  status: string;
  service: string;
  version: string;
  python: string;
  region: string;
};

type Probe =
  | { state: "loading" }
  | { state: "ok"; data: Health; ms: number }
  | { state: "error"; message: string };

export function HealthProbe() {
  const [probe, setProbe] = useState<Probe>({ state: "loading" });

  useEffect(() => {
    const started = performance.now();

    fetch("/api/health")
      .then(async (res) => {
        if (!res.ok) throw new Error(`API returned ${res.status}`);
        return (await res.json()) as Health;
      })
      .then((data) =>
        setProbe({ state: "ok", data, ms: Math.round(performance.now() - started) }),
      )
      .catch((err: unknown) =>
        setProbe({
          state: "error",
          message: err instanceof Error ? err.message : "Unknown error",
        }),
      );
  }, []);

  return (
    <div className="rounded-2xl border border-[#e6ded4] bg-white p-6">
      <h2 className="mb-4 text-sm font-medium tracking-wide text-[#8a7f76] uppercase">
        API connectivity
      </h2>

      {probe.state === "loading" && (
        <p className="text-sm text-[#5c534c]">Contacting /api/health&hellip;</p>
      )}

      {probe.state === "error" && (
        <div className="flex flex-col gap-1">
          <p className="text-sm font-medium text-[#a3402f]">Unreachable</p>
          <p className="text-sm text-[#5c534c]">{probe.message}</p>
        </div>
      )}

      {probe.state === "ok" && (
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 text-sm">
          <dt className="text-[#8a7f76]">Status</dt>
          <dd className="font-medium text-[#2f6b4f]">{probe.data.status}</dd>
          <dt className="text-[#8a7f76]">Python</dt>
          <dd>{probe.data.python}</dd>
          <dt className="text-[#8a7f76]">Region</dt>
          <dd>{probe.data.region}</dd>
          <dt className="text-[#8a7f76]">Round trip</dt>
          <dd>{probe.ms} ms</dd>
        </dl>
      )}
    </div>
  );
}
