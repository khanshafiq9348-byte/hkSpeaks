"use client";

import React, { useState, useEffect } from "react";
import { apiClient } from "@/lib/api";
import { KeyRound, Plus, Trash2, Copy, Check, Code, ShieldAlert } from "lucide-react";

interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  last_used_at?: string;
}

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [keyName, setKeyName] = useState("");
  const [rawKeyReturned, setRawKeyReturned] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadKeys();
  }, []);

  const loadKeys = async () => {
    try {
      const data = await apiClient<ApiKey[]>("/api-keys");
      setKeys(data);
    } catch {
      // ignore
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyName) return;
    try {
      const res = await apiClient<any>("/api-keys", {
        method: "POST",
        body: JSON.stringify({ name: keyName }),
      });
      setRawKeyReturned(res.raw_key);
      setKeyName("");
      loadKeys();
    } catch (err: any) {
      alert(err.message || "Failed to create key. Ensure your plan includes Developer API access.");
    }
  };

  const handleRevoke = async (id: string) => {
    if (!confirm("Revoking this API key will immediately block any active applications using it. Proceed?")) return;
    try {
      await apiClient(`/api-keys/${id}`, { method: "DELETE" });
      loadKeys();
    } catch {
      // ignore
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex-1 flex flex-col min-w-0 h-full overflow-y-auto bg-[#090A0F] text-gray-100">
      <main className="max-w-6xl w-full mx-auto p-6 space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight flex items-center space-x-2.5">
              <KeyRound className="w-6 h-6 text-indigo-400" />
              <span>Developer API Keys</span>
            </h1>
            <p className="text-xs text-gray-400 mt-1">
              Securely authenticate your applications with high-throughput programmatic TTS
            </p>
          </div>

          <button
            onClick={() => {
              setIsCreating(true);
              setRawKeyReturned(null);
            }}
            className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 flex items-center space-x-2 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Generate New Key</span>
          </button>
        </div>

        {/* New Key Alert (Shown only once) */}
        {rawKeyReturned && (
          <div className="p-5 rounded-2xl bg-amber-500/10 border border-amber-500/30 space-y-2">
            <div className="flex items-center space-x-2 text-amber-400 font-semibold text-xs">
              <ShieldAlert className="w-4 h-4" />
              <span>Copy your secret API key now. It will not be shown again!</span>
            </div>
            <div className="flex items-center space-x-2 bg-[#0B0C14] p-3 rounded-xl border border-amber-500/20">
              <code className="text-xs font-mono text-gray-200 flex-1 overflow-x-auto select-all">
                {rawKeyReturned}
              </code>
              <button
                onClick={() => copyToClipboard(rawKeyReturned)}
                className="p-2 rounded-lg bg-[#181B2B] hover:bg-indigo-600 text-gray-200 text-xs flex items-center space-x-1"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? "Copied" : "Copy"}</span>
              </button>
            </div>
          </div>
        )}

        {/* Keys Table */}
        <div className="bg-[#12141F] border border-[#202436] rounded-2xl overflow-hidden shadow-xl">
          <table className="w-full text-left text-xs text-gray-300">
            <thead className="bg-[#0B0C14] text-gray-400 font-semibold border-b border-[#202436]">
              <tr>
                <th className="px-5 py-3.5">Name</th>
                <th className="px-5 py-3.5">Key Prefix</th>
                <th className="px-5 py-3.5">Created</th>
                <th className="px-5 py-3.5">Last Used</th>
                <th className="px-5 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1A1D2E]">
              {keys.map((k) => (
                <tr key={k.id} className="hover:bg-[#151726] transition-colors">
                  <td className="px-5 py-4 font-semibold text-white">{k.name}</td>
                  <td className="px-5 py-4 font-mono text-gray-400">{k.key_prefix}••••••••</td>
                  <td className="px-5 py-4 text-gray-400">
                    {new Date(k.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-5 py-4 text-gray-400">
                    {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : "Never"}
                  </td>
                  <td className="px-5 py-4 text-right">
                    <button
                      onClick={() => handleRevoke(k.id)}
                      className="p-1.5 rounded-lg bg-[#1A1D2E] hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition-colors"
                      title="Revoke Key"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}

              {keys.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-6 py-10 text-center text-gray-500">
                    No active API keys found. Generate a key to integrate programmatically.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* API Integration Documentation & Curl Example */}
        <div className="p-6 rounded-2xl bg-[#12141F] border border-[#202436] space-y-4 shadow-xl">
          <div className="flex items-center space-x-2 text-white font-bold text-base">
            <Code className="w-5 h-5 text-indigo-400" />
            <span>Developer Quickstart</span>
          </div>
          <p className="text-xs text-gray-400">
            Submit generation jobs with your API key. Generations are processed asynchronously in the background.
          </p>

          <div className="bg-[#0B0C14] p-4 rounded-xl border border-[#1E2235] relative">
            <pre className="text-xs font-mono text-gray-300 overflow-x-auto leading-relaxed">
{`curl -X POST "http://localhost:8000/v1/text-to-speech" \\
  -H "Authorization: Bearer hk_live_YOUR_KEY" \\
  -H "Idempotency-Key: job_9981" \\
  -H "Content-Type: application/json" \\
  -d '{
    "text": "Hello world from the HK Speaks Developer API.",
    "voice_id": "VOICE_UUID_HERE",
    "format": "mp3",
    "speed": 1.0
  }'`}
            </pre>
          </div>
        </div>
      </main>

      {/* Modal for creating key */}
      {isCreating && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="w-full max-w-md bg-[#0F111C] border border-[#23273D] rounded-2xl p-5 shadow-2xl space-y-4">
            <h3 className="font-bold text-base text-white">Generate API Key</h3>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Key Description</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Production Backend Bot"
                  value={keyName}
                  onChange={(e) => setKeyName(e.target.value)}
                  className="w-full px-3.5 py-2 bg-[#141624] border border-[#23273D] rounded-xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreating(false)}
                  className="px-4 py-2 text-xs font-semibold text-gray-400 hover:text-gray-200 rounded-xl bg-[#141624]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl shadow-md shadow-indigo-600/30"
                >
                  Generate
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
