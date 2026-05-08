import React, { useState } from "react";
import Chat from "./components/Chat";

export default function App() {
  const [messages, setMessages] = useState<{ role: "user" | "assistant"; content: string }[]>([]);

  return (
    <div style={{ maxWidth: 980, margin: "0 auto", padding: 16, fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif" }}>
      <h1 style={{ margin: "8px 0 16px" }}>text2sql-conversational-postgres</h1>
      <Chat
        onMessagesChange={setMessages}
        messages={messages}
      />
    </div>
  );
}
