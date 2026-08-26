// xterm.js terminal connected to the backend over a ticket-authenticated
// WebSocket (spec Section 17). Mints a fresh single-use ticket via REST
// immediately before opening the socket -- never reuses one.

import { useEffect, useRef } from "react";
import { Terminal as XTerm } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";
import { api } from "../services/api";

export default function Terminal({ instanceId }: { instanceId: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const term = new XTerm({ convertEol: true, cursorBlink: true, fontSize: 14 });
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(containerRef.current);
    fitAddon.fit();

    let socket: WebSocket | null = null;
    let cancelled = false;

    async function connect() {
      term.writeln("Requesting terminal session...");
      const { ticket } = await api.post<{ ticket: string }>(
        `/instances/${instanceId}/terminal-ticket`,
      );
      if (cancelled) return;

      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(
        `${proto}://${window.location.host}/ws/instances/${instanceId}/terminal?ticket=${ticket}`,
      );
      socketRef.current = socket;

      socket.onopen = () => term.writeln("Connected.\r\n");
      socket.onmessage = (event) => term.write(event.data);
      socket.onclose = () => term.writeln("\r\n[connection closed]");
      socket.onerror = () => term.writeln("\r\n[connection error]");

      term.onData((data) => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send(data);
        }
      });
    }

    connect().catch((err) => term.writeln(`Failed to connect: ${err}`));

    const handleResize = () => fitAddon.fit();
    window.addEventListener("resize", handleResize);

    return () => {
      cancelled = true;
      window.removeEventListener("resize", handleResize);
      socket?.close();
      term.dispose();
    };
  }, [instanceId]);

  return <div id="terminal-container" ref={containerRef} />;
}
