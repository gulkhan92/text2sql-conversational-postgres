import React, { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type ChatRow = Record<string, any>;

type ChartType = "bar" | "line" | "pie" | "table";

type ChatResponse = {
  answer: string;
  sql: string;
  data: ChatRow[];
  chart_suggested: boolean;
  chart_type: ChartType;
};

async function postChat(message: string): Promise<ChatResponse> {
  const res = await fetch("http://localhost:8000/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return (await res.json()) as ChatResponse;
}

function TableView({ data }: { data: ChatRow[] }) {
  const columns = useMemo(() => {
    const set = new Set<string>();
    for (const row of data) Object.keys(row || {}).forEach((k) => set.add(k));
    return Array.from(set);
  }, [data]);

  return (
    <div style={{ overflowX: "auto", border: "1px solid rgba(15,23,42,0.08)", borderRadius: 12 }}>
      <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: 0, minWidth: 520 }}>
        <thead style={{ background: "rgba(248,250,252,0.85)" }}>
          <tr>
            {columns.map((c: string) => (
              <th
                key={c}
                style={{
                  textAlign: "left",
                  padding: "10px 12px",
                  borderBottom: "1px solid rgba(15,23,42,0.08)",
                  fontSize: 12,
                  color: "#334155",
                  fontWeight: 700,
                }}
              >
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, idx) => (
            <tr key={idx} style={{ background: idx % 2 === 1 ? "rgba(248,250,252,0.75)" : "transparent" }}>
              {columns.map((c: string) => (
                <td
                  key={c}
                  style={{
                    padding: "10px 12px",
                    borderBottom: "1px solid rgba(15,23,42,0.06)",
                    fontSize: 13,
                    color: "#0f172a",
                  }}
                >
                  {row?.[c] === null || row?.[c] === undefined ? "" : String(row[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ChartView({ data, chartType }: { data: ChatRow[]; chartType: ChartType }) {
  if (!data || data.length === 0) return null;

  const keys = Object.keys(data[0] || {});
  if (keys.length === 0) return null;

  const xKey = keys[0];
  const yKey = keys[1] ?? keys[0];

  const seriesColor = "#2563eb";

  if (chartType === "pie" && keys.length >= 2) {
    const pieData = data.slice(0, 8).map((r, i) => ({
      name: String(r[xKey] ?? i),
      value: Number(r[yKey] ?? 0),
    }));
    return (
      <ResponsiveContainer width="100%" height={320}>
        <PieChart>
          <Pie data={pieData} dataKey="value" nameKey="name" outerRadius={100} label>
            {pieData.map((_, idx) => (
              <Cell key={idx} fill={idx % 2 === 0 ? seriesColor : "#16a34a"} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  if (chartType === "line") {
    const lineData = data.slice(0, 200).map((r, i) => ({
      x: String(r[xKey] ?? i),
      y: Number(r[yKey] ?? 0),
    }));
    return (
      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={lineData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="x" />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="y" stroke={seriesColor} strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  if (chartType === "bar") {
    const barData = data.slice(0, 200).map((r, i) => ({
      x: String(r[xKey] ?? i),
      y: Number(r[yKey] ?? 0),
    }));
    return (
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={barData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="x" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="y" fill={seriesColor} radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  return <TableView data={data} />;
}

export default function Chat({
  messages,
  onMessagesChange,
}: {
  messages: { role: "user" | "assistant"; content: string }[];
  onMessagesChange: (m: { role: "user" | "assistant"; content: string }[]) => void;
}) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastSql, setLastSql] = useState("");
  const [lastData, setLastData] = useState<ChatRow[]>([]);
  const [chartSuggested, setChartSuggested] = useState(false);
  const [chartType, setChartType] = useState<ChartType>("bar");

  async function send() {
    const msg = input.trim();
    if (!msg) return;

    const nextUserMessages = [...messages, { role: "user", content: msg }] as {
      role: "user" | "assistant";
      content: string;
    }[];
    onMessagesChange(nextUserMessages);

    setInput("");
    setLoading(true);

    try {
      const resp = await postChat(msg);
      setLastSql(resp.sql || "");
      setLastData(resp.data || []);
      setChartSuggested(Boolean(resp.chart_suggested));
      setChartType(resp.chart_type || "bar");

      onMessagesChange([
        ...nextUserMessages,
        { role: "assistant", content: resp.answer || "" },
      ]);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Request failed";
      onMessagesChange([
        ...nextUserMessages,
        { role: "assistant", content: message },
      ]);
      setLastSql("");
      setLastData([]);
      setChartSuggested(false);
      setChartType("bar");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "minmax(420px, 1fr) 380px", gap: 14, alignItems: "start" }}>
      <div style={{ border: "1px solid rgba(15,23,42,0.08)", borderRadius: 16, background: "rgba(255,255,255,0.78)", boxShadow: "0 10px 30px rgba(2, 6, 23, 0.06)" }}>
        <div style={{ padding: 14, borderBottom: "1px solid rgba(15,23,42,0.08)" }}>
          <div style={{ fontSize: 13, fontWeight: 800, color: "#0f172a", letterSpacing: 0.2 }}>Conversation</div>
          <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>Ask analytics questions; the backend will generate, validate, and execute a read-only SELECT.</div>
        </div>

        <div style={{ padding: 14, minHeight: 360 }}>
          {messages.length === 0 ? (
            <div style={{ color: "#64748b", fontSize: 14, lineHeight: 1.6 }}>
              Ask a question about the customer spending dataset.
              <div style={{ marginTop: 10, fontSize: 12, color: "#94a3b8" }}>
                Examples: “average amount spent by marital status”, “top states by spending”, “spending trend by age”.
              </div>
            </div>
          ) : (
            <div style={{ display: "grid", gap: 10 }}>
              {messages.map((m, idx) => (
                <div
                  key={idx}
                  style={{
                    background: m.role === "user" ? "rgba(37,99,235,0.09)" : "rgba(248,250,252,0.9)",
                    border: "1px solid rgba(15,23,42,0.08)",
                    borderRadius: 14,
                    padding: 12,
                  }}
                >
                  <div style={{ fontSize: 12, color: "#475569", fontWeight: 800, marginBottom: 6 }}>
                    {m.role === "user" ? "USER" : "ASSISTANT"}
                  </div>
                  <div style={{ whiteSpace: "pre-wrap", fontSize: 14, color: "#0f172a", lineHeight: 1.55 }}>
                    {m.content}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ padding: 14, borderTop: "1px solid rgba(15,23,42,0.08)" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 10 }}>
            <input
              value={input}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setInput(e.target.value)}
              placeholder="e.g., average amount spent by marital status"
              style={{
                padding: "12px 12px",
                borderRadius: 12,
                border: "1px solid rgba(15,23,42,0.10)",
                background: "rgba(255,255,255,0.95)",
                outline: "none",
                boxShadow: "inset 0 1px 0 rgba(255,255,255,0.7)",
                color: "#0f172a",
                fontSize: 14,
              }}
              onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
                if (e.key === "Enter" && !e.shiftKey) send();
              }}
            />

            <button
              onClick={send}
              disabled={loading}
              style={{
                padding: "12px 16px",
                borderRadius: 12,
                border: "1px solid rgba(37,99,235,0.35)",
                background: loading ? "rgba(37,99,235,0.45)" : "linear-gradient(135deg, rgba(37,99,235,1) 0%, rgba(59,130,246,0.92) 60%, rgba(16,185,129,0.78) 120%)",
                color: "white",
                cursor: "pointer",
                fontWeight: 900,
                letterSpacing: 0.2,
                boxShadow: loading ? "none" : "0 14px 26px rgba(37,99,235,0.22)",
              }}
            >
              {loading ? "Thinking…" : "Send"}
            </button>
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gap: 12 }}>
        <div style={{ border: "1px solid rgba(15,23,42,0.08)", borderRadius: 16, background: "rgba(255,255,255,0.78)", boxShadow: "0 10px 30px rgba(2, 6, 23, 0.06)" }}>
          <div style={{ padding: 14, borderBottom: "1px solid rgba(15,23,42,0.08)" }}>
            <div style={{ fontSize: 13, fontWeight: 800, color: "#0f172a", letterSpacing: 0.2 }}>SQL & Results</div>
            <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>
              Read-only execution with RBAC allowlisting.
            </div>
          </div>

          <div style={{ padding: 14 }}>
            {lastSql ? (
              <details>
                <summary style={{ cursor: "pointer", color: "#2563eb", fontWeight: 800 }}>
                  SQL
                </summary>
                <pre
                  style={{
                    whiteSpace: "pre-wrap",
                    background: "#0b1220",
                    color: "#e5e7eb",
                    padding: 12,
                    borderRadius: 12,
                    overflowX: "auto",
                    border: "1px solid rgba(255,255,255,0.08)",
                    marginTop: 10,
                    fontSize: 12,
                    lineHeight: 1.5,
                  }}
                >
                  {lastSql}
                </pre>
              </details>
            ) : (
              <div style={{ color: "#94a3b8", fontSize: 13, lineHeight: 1.6 }}>
                Run a query to see the generated SQL and result preview here.
              </div>
            )}

            {lastData && lastData.length > 0 ? (
              <div style={{ marginTop: 14 }}>
                {chartSuggested ? (
                  <>
                    <div style={{ fontSize: 12, color: "#64748b", fontWeight: 800, marginBottom: 8 }}>
                      Chart preview · {chartType}
                    </div>
                    <div style={{ border: "1px solid rgba(15,23,42,0.08)", borderRadius: 14, padding: 10, background: "rgba(248,250,252,0.7)" }}>
                      <ChartView data={lastData} chartType={chartType} />
                    </div>
                  </>
                ) : (
                  <>
                    <div style={{ fontSize: 12, color: "#64748b", fontWeight: 800, marginBottom: 8 }}>Result table</div>
                    <TableView data={lastData} />
                  </>
                )}
              </div>
            ) : null}
          </div>
        </div>

        <div style={{ border: "1px dashed rgba(15,23,42,0.18)", borderRadius: 16, padding: 14, background: "rgba(248,250,252,0.55)" }}>
          <div style={{ fontSize: 12, fontWeight: 900, color: "#0f172a" }}>Tip</div>
          <div style={{ fontSize: 13, color: "#475569", marginTop: 6, lineHeight: 1.6 }}>
            Ask for aggregated insights (group-by, averages, top-N). If your role is restricted, the backend will return a role-based “no access” message.
          </div>
        </div>
      </div>
    </div>
  );
}
