import React, { useMemo, useState } from "react";
import Chat from "./components/Chat";

export default function App() {
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; content: string }[]>(
    []
  );

  const styles = useMemo(
    () => ({
      appShell: {
        minHeight: "100vh",
        background:
          "radial-gradient(1200px 600px at 15% 10%, rgba(37,99,235,0.14), transparent 55%), radial-gradient(900px 500px at 85% 0%, rgba(16,185,129,0.12), transparent 50%), #f8fafc",
        fontFamily:
          'ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial',
        color: "#0f172a",
      } as React.CSSProperties,
      topbar: {
        position: "sticky" as const,
        top: 0,
        zIndex: 10,
        backdropFilter: "blur(10px)",
        background: "rgba(248,250,252,0.72)",
        borderBottom: "1px solid rgba(15,23,42,0.08)",
      },
      topbarInner: {
        maxWidth: 1200,
        margin: "0 auto",
        padding: "14px 16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 16,
      },
      brand: {
        display: "flex",
        alignItems: "center",
        gap: 12,
        minWidth: 260,
      },
      logo: {
        width: 34,
        height: 34,
        borderRadius: 12,
        background:
          "linear-gradient(135deg, rgba(37,99,235,1) 0%, rgba(59,130,246,0.9) 35%, rgba(16,185,129,0.85) 100%)",
        boxShadow: "0 10px 24px rgba(37,99,235,0.18)",
      },
      title: { fontSize: 14, fontWeight: 700, letterSpacing: 0.2 },
      subtitle: { fontSize: 12, color: "#475569", marginTop: 2 },
      badge: {
        fontSize: 12,
        padding: "8px 10px",
        borderRadius: 999,
        border: "1px solid rgba(15,23,42,0.10)",
        background: "rgba(255,255,255,0.65)",
        color: "#334155",
        display: "flex",
        alignItems: "center",
        gap: 8,
      },
      page: {
        maxWidth: 1200,
        margin: "0 auto",
        padding: "18px 16px 36px",
      },
    }),
    []
  );

  return (
    <div style={styles.appShell}>
      <div style={styles.topbar}>
        <div style={styles.topbarInner}>
          <div style={styles.brand}>
            <div style={styles.logo} />
            <div>
              <div style={styles.title}>text2sql-conversational-postgres</div>
              <div style={styles.subtitle}>Business-ready NL→SQL chatbot UI</div>
            </div>
          </div>

          <div style={styles.badge} title="Frontend talks to backend on localhost:8000">
            <span aria-hidden>●</span> <span>Backend</span>{" "}
            <span style={{ fontWeight: 700 }}>http://localhost:8000</span>
          </div>
        </div>
      </div>

      <div style={styles.page}>
        <Chat onMessagesChange={setMessages} messages={messages} />
      </div>
    </div>
  );
}
