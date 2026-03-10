'use client';

// src/components/implementation/analyze/BrainVisualizer.tsx

import { useEffect, useRef } from 'react';

interface Node {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
  pulse: number;
  active: boolean;
}

interface Edge {
  from: number;
  to: number;
  progress: number;
  speed: number;
  active: boolean;
}

interface Props {
  isActive: boolean; // false when analysis is complete
}

export function BrainVisualizer({ isActive }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef<{ nodes: Node[]; edges: Edge[]; frame: number; raf: number }>({
    nodes: [],
    edges: [],
    frame: 0,
    raf: 0,
  });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const W = canvas.width;
    const H = canvas.height;
    const N = 22;

    // Init nodes
    const nodes: Node[] = Array.from({ length: N }, () => ({
      x: 40 + Math.random() * (W - 80),
      y: 40 + Math.random() * (H - 80),
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      r: 3 + Math.random() * 4,
      pulse: Math.random() * Math.PI * 2,
      active: Math.random() > 0.4,
    }));

    // Init edges — each node connects to 2-3 closest neighbours
    const edges: Edge[] = [];
    for (let i = 0; i < N; i++) {
      const dists = nodes
        .map((n, j) => ({
          j,
          d: Math.hypot(nodes[i].x - n.x, nodes[i].y - n.y),
        }))
        .filter(({ j }) => j !== i)
        .sort((a, b) => a.d - b.d)
        .slice(0, 3);

      dists.forEach(({ j }) => {
        if (!edges.find((e) => (e.from === j && e.to === i))) {
          edges.push({ from: i, to: j, progress: Math.random(), speed: 0.003 + Math.random() * 0.005, active: nodes[i].active });
        }
      });
    }

    stateRef.current = { nodes, edges, frame: 0, raf: 0 };

    const AMBER  = 'rgba(245, 158, 11,';
    const BLUE   = 'rgba(99, 179, 237,';
    const WHITE  = 'rgba(255, 255, 255,';

    const draw = () => {
      const { frame } = stateRef.current;
      ctx.clearRect(0, 0, W, H);

      // Move nodes
      nodes.forEach((n) => {
        if (!isActive) return;
        n.x += n.vx;
        n.y += n.vy;
        if (n.x < 20 || n.x > W - 20) n.vx *= -1;
        if (n.y < 20 || n.y > H - 20) n.vy *= -1;
        n.pulse += 0.04;
        // Occasionally toggle active
        if (Math.random() < 0.002) n.active = !n.active;
      });

      // Draw edges
      edges.forEach((e) => {
        const from = nodes[e.from];
        const to = nodes[e.to];
        const dist = Math.hypot(from.x - to.x, from.y - to.y);
        if (dist > 200) return;

        const alpha = (1 - dist / 200) * (e.active ? 0.5 : 0.12);

        // Static edge line
        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.lineTo(to.x, to.y);
        ctx.strokeStyle = `${WHITE} ${alpha * 0.3})`;
        ctx.lineWidth = 1;
        ctx.stroke();

        if (!e.active || !isActive) return;

        // Travelling pulse on edge
        e.progress += e.speed;
        if (e.progress > 1) e.progress = 0;

        const px = from.x + (to.x - from.x) * e.progress;
        const py = from.y + (to.y - from.y) * e.progress;

        const grad = ctx.createRadialGradient(px, py, 0, px, py, 8);
        grad.addColorStop(0, `${AMBER} 0.9)`);
        grad.addColorStop(1, `${AMBER} 0)`);
        ctx.beginPath();
        ctx.arc(px, py, 8, 0, Math.PI * 2);
        ctx.fillStyle = grad;
        ctx.fill();
      });

      // Draw nodes
      nodes.forEach((n) => {
        const pulseScale = 1 + Math.sin(n.pulse) * 0.2;
        const r = n.r * (n.active ? pulseScale : 1);

        // Glow
        if (n.active) {
          const glow = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, r * 4);
          glow.addColorStop(0, `${AMBER} 0.3)`);
          glow.addColorStop(1, `${AMBER} 0)`);
          ctx.beginPath();
          ctx.arc(n.x, n.y, r * 4, 0, Math.PI * 2);
          ctx.fillStyle = glow;
          ctx.fill();
        }

        // Node body
        ctx.beginPath();
        ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
        ctx.fillStyle = n.active ? `${AMBER} 0.9)` : `${WHITE} 0.12)`;
        ctx.fill();
      });

      stateRef.current.frame = frame + 1;
      stateRef.current.raf = requestAnimationFrame(draw);
    };

    stateRef.current.raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(stateRef.current.raf);
  }, [isActive]);

  return (
    <canvas
      ref={canvasRef}
      width={600}
      height={200}
      className="w-full h-48 rounded-xl opacity-80"
    />
  );
}