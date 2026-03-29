"use client";

import { useState } from "react";

export default function Home() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/process`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ youtube_url: url }),
        }
      );
      const data = await res.json();
      // TODO: redirect to /results/[job_id] page
      console.log("Job created:", data.job_id);
    } catch {
      setError("Failed to connect to the server. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-white flex flex-col items-center justify-center px-4">
      <main className="w-full max-w-2xl flex flex-col items-center gap-8 text-center">
        <h1 className="text-5xl font-bold tracking-tight">
          YT<span className="text-blue-500">Sage</span>
        </h1>
        <p className="text-lg text-zinc-400 max-w-md">
          Turn any YouTube lecture into 2 AI-generated 30-second explainer
          shorts — with timestamp citations back to the source.
        </p>

        <form onSubmit={handleSubmit} className="w-full flex flex-col gap-4">
          <input
            type="text"
            placeholder="Paste a YouTube URL..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="w-full px-4 py-3 rounded-lg bg-zinc-800 border border-zinc-700 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-3 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 font-medium transition-colors"
          >
            {loading ? "Processing..." : "Generate Shorts"}
          </button>
          {error && <p className="text-red-400 text-sm">{error}</p>}
        </form>

        <p className="text-xs text-zinc-600 mt-12">
          This product is entirely derived from work conducted as part of the
          NUS CS5260 course.
        </p>
      </main>
    </div>
  );
}
