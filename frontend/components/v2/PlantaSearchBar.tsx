'use client';

import { useRouter, usePathname } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

const ATTACH_KEY = 'planta-pending-image';
const MAX_IMAGE_BYTES = 2_000_000; // 2 MB

export default function PlantaSearchBar() {
  const router = useRouter();
  const pathname = usePathname();
  const [input, setInput] = useState('');
  const [focused, setFocused] = useState(false);
  const [recording, setRecording] = useState(false);
  const [locBusy, setLocBusy] = useState(false);
  const [pendingFile, setPendingFile] = useState<{ name: string; size: number } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const recogRef = useRef<any>(null);

  // Restaurar chip se já houver imagem pendente em sessionStorage
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(ATTACH_KEY);
      if (!raw) return;
      const data = JSON.parse(raw);
      if (data?.name && data?.size) {
        setPendingFile({ name: data.name, size: data.size });
      }
    } catch {}
  }, []);

  const submit = (text?: string) => {
    const content = (text ?? input).trim();
    const hasAttach = !!pendingFile;
    if (!content && !hasAttach) return;

    // Mensagem default se só anexou imagem sem texto
    const finalText = content || 'Esta imagem.';
    router.push(`/v2/chat?q=${encodeURIComponent(finalText)}${hasAttach ? '&attach=1' : ''}`);
    setInput('');
    setPendingFile(null);
  };

  // ──── MIC · Web Speech API ────────────────────────────────────
  const toggleMic = () => {
    const W = window as any;
    const SR = W.SpeechRecognition || W.webkitSpeechRecognition;
    if (!SR) {
      alert('Microfone não suportado neste browser. Tenta Chrome ou Safari recente.');
      return;
    }
    if (recording) {
      try { recogRef.current?.stop(); } catch {}
      setRecording(false);
      return;
    }
    const recog = new SR();
    recog.lang = 'pt-PT';
    recog.continuous = false;
    recog.interimResults = true;
    recog.maxAlternatives = 1;
    recog.onresult = (e: any) => {
      const transcript = Array.from(e.results as any[])
        .map((r) => r[0].transcript)
        .join(' ');
      setInput(transcript);
    };
    recog.onerror = () => setRecording(false);
    recog.onend = () => setRecording(false);
    try {
      recog.start();
      recogRef.current = recog;
      setRecording(true);
    } catch (err) {
      setRecording(false);
      alert('Não consegui iniciar o microfone. Verifica permissões.');
    }
  };

  // ──── LOCATION · GPS ──────────────────────────────────────────
  const captureLocation = () => {
    if (!('geolocation' in navigator)) {
      alert('Geolocalização não suportada neste browser.');
      return;
    }
    setLocBusy(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        const lat = latitude.toFixed(6);
        const lng = longitude.toFixed(6);
        setLocBusy(false);
        submit(`Estou em ${lat}, ${lng}. Qual a casa-de-banho mais próxima?`);
      },
      (err) => {
        setLocBusy(false);
        alert(`Não consegui obter localização: ${err.message}`);
      },
      { timeout: 8000, enableHighAccuracy: true },
    );
  };

  // ──── CLIP · upload imagem ────────────────────────────────────
  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      alert('Por agora só aceito imagens.');
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      alert('Imagem grande demais (máx 2 MB).');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      try {
        sessionStorage.setItem(
          ATTACH_KEY,
          JSON.stringify({
            name: file.name,
            size: file.size,
            type: file.type,
            dataUrl: reader.result,
          }),
        );
        setPendingFile({ name: file.name, size: file.size });
      } catch (err) {
        alert('Não consegui guardar a imagem (memória cheia?).');
      }
    };
    reader.readAsDataURL(file);
    // Reset input para permitir re-upload do mesmo ficheiro
    e.target.value = '';
  };

  const removeAttachment = () => {
    try { sessionStorage.removeItem(ATTACH_KEY); } catch {}
    setPendingFile(null);
  };

  // No /v2/chat o input proprio do chat substitui esta barra
  if (pathname && pathname.startsWith('/v2/chat')) return null;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 22,
        left: '50%',
        transform: 'translateX(-50%)',
        width: 'min(720px, calc(100% - 32px))',
        zIndex: 99,
      }}
    >
      {/* Chip de imagem anexada */}
      {pendingFile && (
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 8,
            background: 'var(--green-pale, #EDF4EF)',
            border: '1px solid var(--green-dark, #1B3A21)',
            borderRadius: 999,
            padding: '5px 6px 5px 12px',
            marginBottom: 8,
            fontSize: 12,
            color: 'var(--green-dark)',
            fontFamily: 'inherit',
          }}
        >
          <span aria-hidden="true">📎</span>
          <span style={{ maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {pendingFile.name}
          </span>
          <span style={{ opacity: 0.55, fontSize: 11 }}>
            {(pendingFile.size / 1024).toFixed(0)} KB
          </span>
          <button
            onClick={removeAttachment}
            aria-label="Remover anexo"
            style={{
              background: 'white',
              border: 'none',
              borderRadius: '50%',
              width: 22,
              height: 22,
              cursor: 'pointer',
              color: 'var(--green-dark)',
              fontSize: 12,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 0,
            }}
          >
            ✕
          </button>
        </div>
      )}

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 2,
          background: 'white',
          border: '1px solid var(--green-dark, #1B3A21)',
          borderRadius: 999,
          padding: '8px 8px 8px 10px',
          boxShadow: focused
            ? '0 18px 48px rgba(27, 58, 33, 0.22), 0 2px 6px rgba(27, 58, 33, 0.10)'
            : '0 14px 38px rgba(13, 26, 15, 0.10), 0 2px 6px rgba(13, 26, 15, 0.04)',
          transition: 'all 0.18s',
        }}
      >
        {/* MIC */}
        <button
          type="button"
          onClick={toggleMic}
          title={recording ? 'Parar gravação' : 'Falar com a Planta'}
          aria-label={recording ? 'Parar microfone' : 'Falar'}
          className={recording ? 'mic-recording' : ''}
          style={{
            ...iconBtn,
            background: recording ? 'var(--amber, #C25A1A)' : 'transparent',
            color: recording ? 'white' : 'var(--ink)',
          }}
        >
          <MicIcon />
        </button>

        {/* CLIP */}
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          title="Anexar imagem"
          aria-label="Anexar imagem"
          style={iconBtn}
        >
          <ClipIcon />
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          style={{ display: 'none' }}
          onChange={handleFile}
        />

        {/* LOCATION */}
        <button
          type="button"
          onClick={captureLocation}
          disabled={locBusy}
          title="Partilhar a minha localização"
          aria-label="Partilhar localização"
          style={{
            ...iconBtn,
            color: locBusy ? 'var(--amber, #C25A1A)' : 'var(--ink)',
            animation: locBusy ? 'loc-pulse 1s ease-in-out infinite' : 'none',
          }}
        >
          <LocationIcon />
        </button>

        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') submit(); }}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={recording ? 'A ouvir em Português…' : 'Pergunta à Planta…'}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            padding: '10px 8px',
            fontSize: 15.5,
            color: 'var(--ink)',
            minWidth: 0,
            fontFamily: 'inherit',
            letterSpacing: '-0.005em',
          }}
        />

        {/* SEND */}
        <button
          onClick={() => submit()}
          disabled={!input.trim() && !pendingFile}
          style={{
            background: (input.trim() || pendingFile) ? 'var(--green-dark, #1B3A21)' : '#EBE9E2',
            color: (input.trim() || pendingFile) ? 'white' : '#A0A39A',
            border: 'none',
            borderRadius: '50%',
            width: 40,
            height: 40,
            cursor: (input.trim() || pendingFile) ? 'pointer' : 'default',
            transition: 'background 0.15s, transform 0.15s',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
          onMouseEnter={(e) => {
            if (input.trim() || pendingFile) e.currentTarget.style.transform = 'scale(1.05)';
          }}
          onMouseLeave={(e) => { e.currentTarget.style.transform = 'scale(1)'; }}
          aria-label="Enviar para chat"
        >
          <ArrowUp />
        </button>
      </div>

      <div
        style={{
          textAlign: 'center',
          marginTop: 10,
          fontSize: 11,
          color: 'var(--muted)',
          fontFamily: 'var(--font-mono)',
          letterSpacing: '0.04em',
        }}
      >
        {recording
          ? 'A ouvir em Português · clica no microfone para parar'
          : 'PlantaOS can make mistakes'}
      </div>

      <style jsx global>{`
        .mic-recording {
          animation: mic-pulse 1.2s ease-in-out infinite;
        }
        @keyframes mic-pulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(194, 90, 26, 0.5); }
          50% { box-shadow: 0 0 0 10px rgba(194, 90, 26, 0); }
        }
        @keyframes loc-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.45; }
        }
      `}</style>
    </div>
  );
}

const iconBtn: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  width: 36,
  height: 36,
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  flexShrink: 0,
  padding: 0,
  transition: 'background 0.15s, color 0.15s',
};

function MicIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  );
}

function ClipIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
    </svg>
  );
}

function LocationIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  );
}

function ArrowUp() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="19" x2="12" y2="5" />
      <polyline points="5 12 12 5 19 12" />
    </svg>
  );
}
