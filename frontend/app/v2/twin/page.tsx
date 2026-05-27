'use client';

import { useEffect, useRef, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'https://api.plantarockinrio.com';

// Layout 2D dos 8 clusters num plano (Parque Tejo)
// Coordenadas baseadas no SVG masterplan R08 24/03/2026
// (relativo a uma área de 530m × 380m)
const CLUSTER_LAYOUT: Record<string, { x: number; z: number; size: number; unisex: boolean }> = {
  'wc-01': { x: -180,  z:  80, size: 25, unisex: false },
  'wc-02': { x:  -80,  z: 130, size: 28, unisex: false },
  'wc-03': { x:   60,  z: -40, size: 24, unisex: false },
  'wc-04': { x:  140,  z:  60, size: 28, unisex: false },
  'wc-05': { x:  200,  z: -80, size: 38, unisex: true  },
  'wc-06': { x:  -60,  z: -100, size: 42, unisex: true  },
  'wc-07': { x: -200,  z: -60, size: 26, unisex: false },
  'wc-08': { x:   50,  z: 140, size: 28, unisex: false },
};

interface ClusterPayload {
  cluster_id: string;
  ts: number;
  params: {
    pessoas_estimadas: number;
    ocupacao_instantanea: number;
    is_unissex?: boolean;
    capacidade_total?: number;
  };
}

export default function TwinPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [snap, setSnap] = useState<ClusterPayload[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [streamOk, setStreamOk] = useState(false);
  const sceneStateRef = useRef<{
    THREE?: any;
    renderer?: any;
    scene?: any;
    camera?: any;
    controls?: any;
    bars?: Map<string, any>;
    labels?: Map<string, any>;
    targetOcc?: Map<string, number>;
    animationId?: number;
  }>({});

  // Carregar three.js + OrbitControls via CDN dinamicamente
  useEffect(() => {
    if (!containerRef.current) return;

    const loadScript = (src: string) => new Promise<void>((resolve, reject) => {
      if (document.querySelector(`script[src="${src}"]`)) {
        resolve();
        return;
      }
      const s = document.createElement('script');
      s.src = src;
      s.async = true;
      s.onload = () => resolve();
      s.onerror = () => reject(new Error(`failed to load ${src}`));
      document.head.appendChild(s);
    });

    let mounted = true;

    (async () => {
      await loadScript('https://cdn.jsdelivr.net/npm/three@0.158.0/build/three.min.js');
      await loadScript('https://cdn.jsdelivr.net/npm/three@0.158.0/examples/js/controls/OrbitControls.js');
      if (!mounted || !containerRef.current) return;

      // @ts-ignore
      const THREE = (window as any).THREE;
      if (!THREE) return;
      sceneStateRef.current.THREE = THREE;

      const container = containerRef.current;
      const w = container.clientWidth;
      const h = container.clientHeight;

      const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      renderer.setSize(w, h);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      container.appendChild(renderer.domElement);
      sceneStateRef.current.renderer = renderer;

      const scene = new THREE.Scene();
      scene.background = new THREE.Color('#F4F2EB');
      sceneStateRef.current.scene = scene;

      const camera = new THREE.PerspectiveCamera(50, w / h, 1, 5000);
      camera.position.set(280, 280, 380);
      camera.lookAt(0, 0, 0);
      sceneStateRef.current.camera = camera;

      // OrbitControls
      // @ts-ignore
      const controls = new THREE.OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.08;
      controls.maxPolarAngle = Math.PI / 2 - 0.05;
      sceneStateRef.current.controls = controls;

      // Lights
      const ambient = new THREE.AmbientLight(0xffffff, 0.6);
      scene.add(ambient);
      const dir = new THREE.DirectionalLight(0xffffff, 0.7);
      dir.position.set(120, 240, 200);
      scene.add(dir);

      // Chão (Parque Tejo)
      const groundGeo = new THREE.PlaneGeometry(600, 440);
      const groundMat = new THREE.MeshLambertMaterial({ color: '#E8E2D1' });
      const ground = new THREE.Mesh(groundGeo, groundMat);
      ground.rotation.x = -Math.PI / 2;
      ground.position.y = 0;
      scene.add(ground);

      // Grelha
      const grid = new THREE.GridHelper(600, 30, '#C9C1AC', '#D8D2BD');
      grid.position.y = 0.02;
      scene.add(grid);

      // Palco Mundo (referência)
      const stageGeo = new THREE.BoxGeometry(200, 18, 60);
      const stageMat = new THREE.MeshLambertMaterial({ color: '#1B3A21' });
      const stage = new THREE.Mesh(stageGeo, stageMat);
      stage.position.set(0, 9, 180);
      scene.add(stage);

      // 8 clusters como prismas
      const bars = new Map<string, any>();
      const labels = new Map<string, any>();
      const targetOcc = new Map<string, number>();

      Object.entries(CLUSTER_LAYOUT).forEach(([id, layout]) => {
        const size = layout.size;
        const initialHeight = 12;
        const geo = new THREE.BoxGeometry(size, initialHeight, size);
        const mat = new THREE.MeshLambertMaterial({
          color: layout.unisex ? '#7A4A8E' : '#4A7C59',
        });
        const bar = new THREE.Mesh(geo, mat);
        bar.position.set(layout.x, initialHeight / 2, layout.z);
        bar.userData = { clusterId: id, baseSize: size };
        scene.add(bar);
        bars.set(id, bar);
        targetOcc.set(id, 0);

        // Texto label via sprite (canvas)
        const cnv = document.createElement('canvas');
        cnv.width = 256; cnv.height = 96;
        const ctx = cnv.getContext('2d')!;
        ctx.fillStyle = layout.unisex ? '#7A4A8E' : '#1B3A21';
        ctx.font = 'bold 64px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(id.toUpperCase(), 128, 60);
        const tex = new THREE.CanvasTexture(cnv);
        const spriteMat = new THREE.SpriteMaterial({ map: tex, transparent: true });
        const sprite = new THREE.Sprite(spriteMat);
        sprite.position.set(layout.x, 60, layout.z);
        sprite.scale.set(40, 15, 1);
        scene.add(sprite);
        labels.set(id, sprite);
      });

      sceneStateRef.current.bars = bars;
      sceneStateRef.current.labels = labels;
      sceneStateRef.current.targetOcc = targetOcc;

      // Raycaster — click
      const raycaster = new THREE.Raycaster();
      const mouse = new THREE.Vector2();
      renderer.domElement.addEventListener('click', (ev: MouseEvent) => {
        const rect = renderer.domElement.getBoundingClientRect();
        mouse.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1;
        raycaster.setFromCamera(mouse, camera);
        const hits = raycaster.intersectObjects(Array.from(bars.values()));
        if (hits.length > 0) {
          const id = hits[0].object.userData.clusterId;
          setSelected(id);
        }
      });

      // Animate loop
      const animate = () => {
        const id = requestAnimationFrame(animate);
        sceneStateRef.current.animationId = id;
        // Suavizar altura para target
        bars.forEach((bar: any, clusterId: string) => {
          const target = targetOcc.get(clusterId) || 0;
          const targetHeight = 12 + target * 0.8;  // 0% → 12; 100% → 92
          const currentH = bar.geometry.parameters.height;
          if (Math.abs(currentH - targetHeight) > 0.5) {
            const newH = currentH + (targetHeight - currentH) * 0.08;
            bar.geometry.dispose();
            bar.geometry = new THREE.BoxGeometry(bar.userData.baseSize, newH, bar.userData.baseSize);
            bar.position.y = newH / 2;
            // Cor: gradiente verde→amarelo→vermelho com ocupação
            const occ = target;
            let color;
            if (occ < 60) color = '#4A7C59';
            else if (occ < 80) color = '#A85D00';
            else color = '#C25A1A';
            const isUni = CLUSTER_LAYOUT[clusterId]?.unisex;
            (bar.material as any).color.set(isUni ? '#7A4A8E' : color);
          }
        });

        controls.update();
        renderer.render(scene, camera);
      };
      animate();

      // Resize
      const handleResize = () => {
        if (!container) return;
        const w2 = container.clientWidth;
        const h2 = container.clientHeight;
        camera.aspect = w2 / h2;
        camera.updateProjectionMatrix();
        renderer.setSize(w2, h2);
      };
      window.addEventListener('resize', handleResize);
    })();

    return () => {
      mounted = false;
      const s = sceneStateRef.current;
      if (s.animationId) cancelAnimationFrame(s.animationId);
      if (s.renderer) {
        s.renderer.dispose();
        if (s.renderer.domElement.parentNode) {
          s.renderer.domElement.parentNode.removeChild(s.renderer.domElement);
        }
      }
    };
  }, []);

  // SSE para actualizar alturas dos prismas
  useEffect(() => {
    const es = new EventSource(`${API_BASE}/api/v1/telemetry/clusters/stream`);
    es.onopen = () => setStreamOk(true);
    es.onerror = () => setStreamOk(false);
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        const clusters: ClusterPayload[] = data.clusters || [];
        setSnap(clusters);
        const tgt = sceneStateRef.current.targetOcc;
        if (tgt) {
          clusters.forEach(c => {
            tgt.set(c.cluster_id, c.params.ocupacao_instantanea);
          });
        }
      } catch {}
    };
    return () => es.close();
  }, []);

  const selectedCluster = snap.find(c => c.cluster_id === selected);

  return (
    <div style={{ padding: '24px 24px 96px', maxWidth: 1400, margin: '0 auto' }}>
      <div style={{ marginBottom: 14 }}>
        <div className="section-label">Sistema · Digital Twin 3D</div>
        <h1 className="serif" style={{
          fontSize: 'clamp(26px, 4vw, 40px)',
          fontWeight: 500, color: 'var(--color-ink)', lineHeight: 1.1, marginBottom: 6,
        }}>
          Parque Tejo · Twin
        </h1>
        <p style={{ color: 'var(--color-muted)', fontSize: 13 }}>
          8 clusters como prismas · altura = ocupação · cor = pressão · 
          <span style={{ color: '#7A4A8E', fontWeight: 600, marginLeft: 4 }}>roxo</span> = unissex (WC-05, WC-06) · 
          arrasta para rodar · roda para zoom
          {streamOk && <span style={{ color: '#4A7C59', marginLeft: 8 }}>● stream activo</span>}
        </p>
      </div>

      {/* CANVAS 3D */}
      <div
        ref={containerRef}
        style={{
          width: '100%',
          height: 'min(70vh, 600px)',
          background: '#F4F2EB',
          borderRadius: 12,
          overflow: 'hidden',
          border: '1px solid var(--color-border)',
        }}
      />

      {/* Mini KPIs row */}
      <div style={{
        marginTop: 12,
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
        gap: 8,
      }}>
        {snap.map(c => {
          const isUni = ['wc-05', 'wc-06'].includes(c.cluster_id);
          const occ = c.params.ocupacao_instantanea;
          const color = isUni ? '#7A4A8E' : occ >= 80 ? '#C25A1A' : occ >= 60 ? '#A85D00' : '#4A7C59';
          return (
            <div
              key={c.cluster_id}
              onClick={() => setSelected(c.cluster_id)}
              style={{
                background: 'white',
                border: selected === c.cluster_id
                  ? `2px solid ${color}`
                  : '1px solid var(--color-border)',
                borderRadius: 8,
                padding: 10,
                cursor: 'pointer',
              }}
            >
              <div className="mono" style={{ fontSize: 11, fontWeight: 700, color: 'var(--color-ink)' }}>
                {c.cluster_id.toUpperCase()}
                {isUni && <span style={{ fontSize: 8, color: '#7A4A8E', marginLeft: 4 }}>U</span>}
              </div>
              <div style={{ fontSize: 18, fontWeight: 700, color, lineHeight: 1.1, marginTop: 3 }}>
                {occ}%
              </div>
              <div className="mono" style={{ fontSize: 9, color: 'var(--color-muted)', marginTop: 2 }}>
                {c.params.pessoas_estimadas} pessoas
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected detail */}
      {selectedCluster && (
        <div style={{
          marginTop: 14, padding: 14,
          background: 'white', border: '1px solid var(--color-border)',
          borderRadius: 10,
        }}>
          <h3 className="serif" style={{ fontSize: 20, fontWeight: 500, marginBottom: 8 }}>
            Cluster {selectedCluster.cluster_id.toUpperCase()}
            {selectedCluster.params.is_unissex && (
              <span style={{
                fontSize: 11, marginLeft: 8,
                background: '#F3EAFF', color: '#7A4A8E',
                padding: '2px 8px', borderRadius: 999,
                fontWeight: 700, letterSpacing: '0.08em',
              }}>UNISSEX</span>
            )}
          </h3>
          <div className="mono" style={{ fontSize: 11, color: 'var(--color-muted)' }}>
            Ocupação <strong style={{ color: 'var(--color-ink)' }}>{selectedCluster.params.ocupacao_instantanea}%</strong>
            {' · '}Pessoas <strong style={{ color: 'var(--color-ink)' }}>{selectedCluster.params.pessoas_estimadas}</strong>
            {' · '}Capacidade <strong style={{ color: 'var(--color-ink)' }}>{selectedCluster.params.capacidade_total ?? '—'}</strong>
          </div>
        </div>
      )}
    </div>
  );
}
