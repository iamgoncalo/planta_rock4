"use client";

import { useEffect, useRef, useState, useCallback } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_URL = API_URL
  .replace("http://", "ws://")
  .replace("https://", "wss://") + "/api/v1/sensors/terminal";

interface TerminalLine {
  type: "input" | "output" | "system";
  text: string;
}

export function SensorTerminal() {
  const [lines, setLines] = useState<TerminalLine[]>([
    { type: "system", text: "A ligar ao servidor..." },
  ]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const [history, setHistory] = useState<string[]>([]);
  const [historyIdx, setHistoryIdx] = useState(-1);
  const wsRef = useRef<WebSocket | null>(null);
  const outputRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [lines, scrollToBottom]);

  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === "welcome" || msg.type === "output" || msg.type === "error") {
          const text = msg.output || "";
          setLines((prev) => [...prev, { type: "output", text }]);
        }
      } catch {
        setLines((prev) => [...prev, { type: "output", text: evt.data }]);
      }
    };

    ws.onerror = () => {
      setLines((prev) => [
        ...prev,
        { type: "system", text: "Erro de ligação ao terminal." },
      ]);
    };

    ws.onclose = () => {
      setConnected(false);
      setLines((prev) => [
        ...prev,
        { type: "system", text: "Terminal desligado." },
      ]);
    };

    return () => {
      ws.close();
    };
  }, []);

  const sendCommand = useCallback((cmd: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    if (!cmd.trim()) return;

    setLines((prev) => [...prev, { type: "input", text: `> ${cmd}` }]);
    setHistory((prev) => [cmd, ...prev.slice(0, 49)]);
    setHistoryIdx(-1);

    wsRef.current.send(JSON.stringify({ command: cmd }));
    setInput("");
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      sendCommand(input);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const next = Math.min(historyIdx + 1, history.length - 1);
      setHistoryIdx(next);
      setInput(history[next] || "");
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      const next = Math.max(historyIdx - 1, -1);
      setHistoryIdx(next);
      setInput(next === -1 ? "" : history[next] || "");
    }
  };

  const renderLine = (line: TerminalLine, idx: number) => {
    const style: React.CSSProperties = {
      whiteSpace: "pre-wrap",
      wordBreak: "break-word",
      lineHeight: 1.5,
      fontFamily: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace",
      fontSize: 13,
    };

    if (line.type === "input") {
      return (
        <div key={idx} style={{ ...style, color: "#6FAF82" }}>
          {line.text}
        </div>
      );
    }
    if (line.type === "system") {
      return (
        <div key={idx} style={{ ...style, color: "#D48B3A", fontStyle: "italic" }}>
          {line.text}
        </div>
      );
    }
    return (
      <div key={idx} style={{ ...style, color: "#1F2937" }}>
        {line.text}
      </div>
    );
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        backgroundColor: "#F9FAFB",
        border: "1px solid #E5E7EB",
        borderRadius: 8,
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "8px 14px",
          backgroundColor: "#1F2937",
          color: "#F9FAFB",
        }}
      >
        <span style={{ fontFamily: "monospace", fontSize: 13, fontWeight: 600 }}>
          PlantaOS Terminal
        </span>
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            fontSize: 12,
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: connected ? "#6FAF82" : "#6B7280",
            }}
          />
          {connected ? "Ligado" : "Desligado"}
        </span>
      </div>

      {/* Output */}
      <div
        ref={outputRef}
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "12px 14px",
          backgroundColor: "#F9FAFB",
          minHeight: 0,
        }}
        onClick={() => inputRef.current?.focus()}
      >
        {lines.map(renderLine)}
      </div>

      {/* Input */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          padding: "8px 14px",
          borderTop: "1px solid #E5E7EB",
          backgroundColor: "#fff",
          gap: 8,
        }}
      >
        <span
          style={{
            fontFamily: "monospace",
            fontSize: 13,
            color: "#6FAF82",
            fontWeight: 700,
          }}
        >
          $
        </span>
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={connected ? "Escreva um comando..." : "Sem ligação"}
          disabled={!connected}
          style={{
            flex: 1,
            border: "none",
            outline: "none",
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace",
            fontSize: 13,
            color: "#1F2937",
            backgroundColor: "transparent",
          }}
          autoComplete="off"
          autoCorrect="off"
          autoCapitalize="off"
          spellCheck={false}
        />
        <button
          onClick={() => sendCommand(input)}
          disabled={!connected || !input.trim()}
          style={{
            padding: "4px 12px",
            backgroundColor: connected && input.trim() ? "#1F2937" : "#E5E7EB",
            color: connected && input.trim() ? "#F9FAFB" : "#9CA3AF",
            border: "none",
            borderRadius: 4,
            fontSize: 12,
            cursor: connected && input.trim() ? "pointer" : "default",
            fontFamily: "monospace",
          }}
        >
          Enviar
        </button>
      </div>
    </div>
  );
}
