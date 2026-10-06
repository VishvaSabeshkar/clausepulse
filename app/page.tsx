"use client";

import { useEffect, useState } from "react";

type HealthResponse = { status: string; python: string };

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<HealthResponse>;
      })
      .then(setHealth)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : String(err)),
      );
  }, []);

  return (
    <main style={{ padding: 32, fontFamily: "sans-serif" }}>
      <h1>ClausePulse — walking skeleton</h1>
      {error && <p>Backend unreachable: {error}</p>}
      {!error && !health && <p>Checking backend…</p>}
      {health && <p>Backend: {health.status} (Python {health.python})</p>}
    </main>
  );
}