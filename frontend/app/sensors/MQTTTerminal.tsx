'use client';
/**
 * MQTTTerminal — xterm.js terminal bridged to the device-control WebSocket.
 * Loaded via dynamic import (no SSR) from sensors/page.tsx.
 */
import React, {
  useEffect, useRef, useImperativeHandle, forwardRef, useState,
} from 'react';

interface MQTTTerminalHandle {
  sendCmd: (cmd: string) => void;
}

interface MQTTTerminalProps {
  wsUrl: string;
  height?: number;
}

const MQTTTerminal = forwardRef<MQTTTerminalHandle, MQTTTerminalProps>(
  function MQTTTerminal({ wsUrl, height = 460 }, ref) {
    const containerRef = useRef<HTMLDivElement>(null);
    const termRef      = useRef<import('@xterm/xterm').Terminal | null>(null);
    const wsRef        = useRef<WebSocket | null>(null);
    const inputBuf     = useRef('');
    const [connected, setConnected]   = useState(false);
    const [msgCount, setMsgCount]     = useState(0);
    const destroyedRef = useRef(false);

    useImperativeHandle(ref, () => ({
      sendCmd(cmd: string) {
        if (termRef.current) {
          termRef.current.write('\r\n\x1b[36m$ \x1b[0m' + cmd + '\r\n');
        }
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ command: cmd }));
        }
        inputBuf.current = '';
      },
    }));

    useEffect(() => {
      destroyedRef.current = false;
      let term: import('@xterm/xterm').Terminal;
      let fitAddon: import('@xterm/addon-fit').FitAddon;
      let ws: WebSocket;

      async function init() {
        const { Terminal } = await import('@xterm/xterm');
        const { FitAddon } = await import('@xterm/addon-fit');
        // @ts-ignore — CSS import resolved by Next.js bundler at runtime
      await import('@xterm/xterm/css/xterm.css');

        if (destroyedRef.current || !containerRef.current) return;

        term = new Terminal({
          theme: {
            background:  '#0a1a0c',
            foreground:  '#b8debb',
            cursor:      '#6FAF82',
            black:       '#0a1a0c',
            green:       '#6FAF82',
            yellow:      '#D4A020',
            red:         '#C25A1A',
            cyan:        '#7AC5B8',
            blue:        '#4A7C59',
            white:       '#c8e8c8',
            brightBlack: '#3a5540',
            brightGreen: '#8fcf9f',
            brightYellow:'#e4b030',
          },
          fontFamily:  'JetBrains Mono, "Cascadia Code", Menlo, Monaco, Consolas, monospace',
          fontSize:    12,
          lineHeight:  1.45,
          cursorBlink: true,
          cursorStyle: 'block',
          scrollback:  3000,
          convertEol:  true,
        });

        fitAddon = new FitAddon();
        term.loadAddon(fitAddon);
        term.open(containerRef.current);
        fitAddon.fit();
        termRef.current = term;

        term.writeln('\x1b[32m╔══════════════════════════════════════════════╗\x1b[0m');
        term.writeln('\x1b[32m║  PlantaOS  ·  Device Terminal  v3.0          ║\x1b[0m');
        term.writeln('\x1b[32m║  Rock in Rio Lisboa 2026  ·  MQTT bridge      ║\x1b[0m');
        term.writeln('\x1b[32m╚══════════════════════════════════════════════╝\x1b[0m');
        term.writeln('');
        term.writeln('\x1b[90mDigita \x1b[36mhelp\x1b[90m para ver todos os comandos disponíveis.\x1b[0m');
        term.writeln('');
        term.write('\x1b[36m$ \x1b[0m');

        // Key input → buffer until Enter
        term.onKey(({ key, domEvent }) => {
          const code = domEvent.key;
          if (code === 'Enter') {
            const cmd = inputBuf.current.trim();
            inputBuf.current = '';
            term.write('\r\n');
            if (cmd) {
              if (ws?.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ command: cmd }));
              } else {
                term.writeln('\x1b[33m[sem ligação — backend offline]\x1b[0m');
                term.write('\x1b[36m$ \x1b[0m');
              }
            } else {
              term.write('\x1b[36m$ \x1b[0m');
            }
          } else if (code === 'Backspace') {
            if (inputBuf.current.length > 0) {
              inputBuf.current = inputBuf.current.slice(0, -1);
              term.write('\b \b');
            }
          } else if (code === 'l' && domEvent.ctrlKey) {
            term.clear();
            term.write('\x1b[36m$ \x1b[0m');
          } else if (key.length === 1 && !domEvent.ctrlKey && !domEvent.metaKey) {
            inputBuf.current += key;
            term.write(key);
          }
        });

        // Resize observer
        const ro = new ResizeObserver(() => {
          try { fitAddon.fit(); } catch {}
        });
        ro.observe(containerRef.current!);

        connectWS();

        function connectWS() {
          if (destroyedRef.current) return;
          ws = new WebSocket(wsUrl);
          wsRef.current = ws;

          ws.onopen = () => {
            if (destroyedRef.current) return;
            setConnected(true);
            term.writeln('\x1b[32m[ligado ao MQTT bridge]\x1b[0m');
            term.write('\x1b[36m$ \x1b[0m');
          };

          ws.onmessage = (e) => {
            try {
              const msg = JSON.parse(e.data) as {
                type: string;
                output?: string;
                cluster_id?: string;
                channel?: string;
              };
              if (!termRef.current) return;
              if (msg.output) {
                // Strip trailing prompt-write so we don't double-print
                const out = msg.output.replace(/\n?\$ $/, '');
                if (out) termRef.current.write(out);
                // Re-print prompt after output
                if (msg.type !== 'serial') {
                  termRef.current.write('\r\n\x1b[36m$ \x1b[0m');
                }
                setMsgCount(c => c + 1);
              }
            } catch {}
          };

          ws.onclose = () => {
            if (destroyedRef.current) return;
            setConnected(false);
            termRef.current?.writeln('\r\n\x1b[90m[desligado — a tentar reconectar em 5s…]\x1b[0m');
            setTimeout(connectWS, 5000);
          };

          ws.onerror = () => {
            termRef.current?.writeln(
              '\r\n\x1b[33m[backend offline — inicia o servidor para controlar hardware real]\x1b[0m'
            );
          };
        }
      }

      init();

      return () => {
        destroyedRef.current = true;
        wsRef.current?.close();
        termRef.current?.dispose();
      };
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [wsUrl]);

    return (
      <div style={{ borderRadius: 10, overflow: 'hidden', border: '1px solid #1a3a20' }}>
        {/* Status bar */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          background: '#0a1a0c',
          padding: '6px 14px',
          borderBottom: '1px solid #1a3a20',
        }}>
          <span style={{
            width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
            background: connected ? '#6FAF82' : '#556655',
            boxShadow: connected ? '0 0 6px #6FAF82' : 'none',
            transition: 'background .3s, box-shadow .3s',
          }} />
          <span style={{ fontSize: 11, color: '#556655', fontFamily: 'monospace' }}>
            {connected ? 'MQTT bridge · ligado' : 'A ligar ao backend…'}
          </span>
          {msgCount > 0 && (
            <span style={{
              marginLeft: 4, fontSize: 10, color: '#3a5540',
              fontFamily: 'monospace',
            }}>
              {msgCount} msgs
            </span>
          )}
          <span style={{ marginLeft: 'auto', fontSize: 10, color: '#2a4a2a', fontFamily: 'monospace' }}>
            PlantaOS v3 · {wsUrl.split('/').slice(2, 3)}
          </span>
        </div>

        {/* xterm container */}
        <div
          ref={containerRef}
          style={{
            height,
            background: '#0a1a0c',
            overflow: 'hidden',
          }}
        />

        {/* Help footer */}
        <div style={{
          background: '#0a1a0c',
          borderTop: '1px solid #1a3a20',
          padding: '5px 14px',
          display: 'flex', gap: 12, flexWrap: 'wrap',
        }}>
          {['ping','diagnostics','status','scan','serial on','flash','reset','help'].map(cmd => (
            <code
              key={cmd}
              style={{
                fontSize: 10, color: '#4a7c59', cursor: 'pointer',
                fontFamily: 'monospace',
              }}
              onClick={() => {
                if (termRef.current) termRef.current.write(cmd);
                inputBuf.current = cmd;
                termRef.current?.focus();
              }}
            >{cmd}</code>
          ))}
        </div>
      </div>
    );
  }
);

export default MQTTTerminal;
