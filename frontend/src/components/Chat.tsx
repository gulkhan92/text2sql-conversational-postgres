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
    <div style={{ overflowX: "auto", border: "1px solid #e5e7eb", borderRadius: 8 }}>
      <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 520 }}>
        <thead style={{ background: "#f8fafc" }}>
          <tr>
            {columns.map((c: string) => (
              <th key={c} style={{ textAlign: "left", padding: 8, borderBottom: "1px solid #e5e7eb" }}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, idx) => (
            <tr key={idx}>
              {columns.map((c: string) => (
                <td key={c} style={{ padding: 8, borderBottom: "1px solid #f1f5f9" }}>
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

  if (chartType === "pie" && keys.length >= 2) {
    // pie expects numeric "value" and "name"
    const pieData = data.slice(0, 8).map((r, i) => ({
      name: String(r[xKey] ?? i),
      value: Number(r[yKey] ?? 0),
    }));
    return (
      <ResponsiveContainer width="100%" height={320}>
        <PieChart>
          <Pie data={pieData} dataKey="value" nameKey="name" outerRadius={100} label>
            {pieData.map((_, idx) => (
              <Cell key={idx} />
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
          <Line type="monotone" dataKey="y" stroke="#3b82f6" />
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
          <Bar dataKey="y" fill="#2563eb" />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  // default table
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

    onMessagesChange([...messages, { role: "user", content: msg }]);
    setInput("");
    setLoading(true);

    try {
      const resp = await postChat(msg);
      setLastSql(resp.sql || "");
      setLastData(resp.data || []);
      setChartSuggested(Boolean(resp.chart_suggested));
      setChartType(resp.chart_type || "bar");

      onMessagesChange([
        ...messages,
        { role: "user", content: msg },
        { role: "assistant", content: resp.answer || "" },
      ]);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Request failed";
      onMessagesChange([
        ...messages,
        { role: "user", content: msg },
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
    <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 12 }}>
      <div style={{ border: "1px solid #e5e7eb", borderRadius: 12, padding: 12, minHeight: 320, background: "#fff" }}>
        <div style={{ display: "grid", gap: 10 }}>
          {messages.length === 0 ? (
            <div style={{ color: "#6b7280" }}>Ask a question about the customer spending dataset.</div>
          ) : (
            messages.map((m, idx) => (
              <div key={idx} style={{ background: m.role === "user" ? "#eff6ff" : "#f8fafc", border: "1px solid #e5e7eb", borderRadius: 10, padding: 10 }}>
                <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>{m.role.toUpperCase()}</div>
                <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>
              </div>
            ))
          )}
        </div>
      </div>

      <div style={{ display: "grid", gap: 8 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 8 }}>
          <input
            value={input}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setInput(e.target.value)}
            placeholder="e.g., average amount spent by gender"
            style={{ padding: 10, borderRadius: 10, border: "1px solid #e5e7eb" }}
            onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => {
              if (e.key === "Enter" && !e.shiftKey) send();
            }}
          />
          <button
            onClick={send}
            disabled={loading}
            style={{ padding: "10px 14px", borderRadius: 10, border: "1px solid #2563eb", background: "#2563eb", color: "white", cursor: "pointer" }}
          >
            {loading ? "Thinking..." : "Send"}
          </button>
        </div>

        {lastSql ? (
          <details>
            <summary style={{ cursor: "pointer", color: "#2563eb" }}>SQL</summary>
            <pre style={{ whiteSpace: "pre-wrap", background: "#0b1220", color: "#e5e7eb", padding: 12, borderRadius: 10, overflowX: "auto" }}>
              {lastSql}
            </pre>
          </details>
        ) : null}

        {lastData && lastData.length > 0 ? (
          <div style={{ marginTop: 8 }}>
            {chartSuggested ? (
              <>
                <div style={{ fontSize: 12, color: "#64748b", marginBottom: 6 }}>
                  Chart: {chartType}
                </div>
                <ChartView data={lastData} chartType={chartType} />
              </>
            ) : (
              <>
                <div style={{ fontSize: 12, color: "#64748b", marginBottom: 6 }}>Result table</div>
                <TableView data={lastData} />
              </>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
