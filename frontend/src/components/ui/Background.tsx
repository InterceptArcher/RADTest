'use client';

import { useEffect, useRef } from 'react';

/**
 * Animated HP liquid-glass backdrop: a bold blue squiggle ribbon + drifting
 * orbs + a faint "hp" emblem watermark, drawn on a fixed full-screen canvas
 * behind the app so the frosted panels refract over it. Ported from the
 * approved design mockup. Respects prefers-reduced-motion.
 */
export default function Background() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    const x = c.getContext('2d');
    if (!x) return;

    let W = 0, H = 0, phase = 0, raf = 0;
    const rz = () => { W = c.width = window.innerWidth; H = c.height = window.innerHeight; };
    rz();
    window.addEventListener('resize', rz);

    const orbs = Array.from({ length: 7 }, () => ({
      x: Math.random(), y: Math.random(), r: 120 + Math.random() * 180,
      vx: (Math.random() - 0.5) * 0.0006, vy: (Math.random() - 0.5) * 0.0006,
      h: Math.random() < 0.5 ? '0,150,214' : '127,209,240',
    }));

    function squiggle(baseFrac: number, ampFrac: number, lw: number, alpha: number, off: number, glow: number) {
      x!.save();
      x!.globalAlpha = alpha; x!.lineWidth = lw; x!.lineCap = 'round';
      x!.shadowColor = 'rgba(0,150,214,.85)'; x!.shadowBlur = glow;
      const g = x!.createLinearGradient(0, 0, W, 0);
      g.addColorStop(0, 'rgba(0,150,214,0)');
      g.addColorStop(0.18, 'rgba(0,150,214,.75)');
      g.addColorStop(0.5, 'rgba(0,134,214,1)');
      g.addColorStop(0.82, 'rgba(91,155,245,.8)');
      g.addColorStop(1, 'rgba(127,209,240,0)');
      x!.strokeStyle = g; x!.beginPath();
      const base = H * baseFrac, amp = H * ampFrac;
      for (let px = -60; px <= W + 60; px += 12) {
        const t = px / (W || 1);
        const y = base + Math.sin(t * Math.PI * 3 + phase + off) * amp * Math.sin(t * Math.PI);
        px <= -60 ? x!.moveTo(px, y) : x!.lineTo(px, y);
      }
      x!.stroke(); x!.restore();
    }

    function draw() {
      x!.clearRect(0, 0, W, H);
      squiggle(0.60, 0.22, Math.max(80, W * 0.072), 0.55, 0, 110);
      squiggle(0.60, 0.22, Math.max(26, W * 0.022), 0.85, 0, 40);
      squiggle(0.40, 0.13, Math.max(40, W * 0.034), 0.20, 2.1, 80);
      orbs.forEach((o) => {
        o.x += o.vx; o.y += o.vy;
        if (o.x < -0.1 || o.x > 1.1) o.vx *= -1;
        if (o.y < -0.1 || o.y > 1.1) o.vy *= -1;
        const g = x!.createRadialGradient(o.x * W, o.y * H, 0, o.x * W, o.y * H, o.r);
        g.addColorStop(0, `rgba(${o.h},.16)`); g.addColorStop(1, `rgba(${o.h},0)`);
        x!.fillStyle = g; x!.beginPath(); x!.arc(o.x * W, o.y * H, o.r, 0, 7); x!.fill();
      });
      phase += 0.004;
      x!.save(); x!.globalAlpha = 0.05; x!.translate(W - 150, H - 130);
      x!.strokeStyle = '#0a6fa5'; x!.lineWidth = 10; x!.beginPath(); x!.arc(0, 0, 92, 0, 7); x!.stroke();
      x!.fillStyle = '#0a6fa5'; x!.font = 'italic 800 64px Inter, system-ui, sans-serif';
      x!.textAlign = 'center'; x!.textBaseline = 'middle'; x!.fillText('hp', 0, 6); x!.restore();
    }

    const reduce = window.matchMedia('(prefers-reduced-motion:reduce)').matches;
    if (reduce) { draw(); }
    else { const loop = () => { draw(); raf = requestAnimationFrame(loop); }; loop(); }

    return () => { window.removeEventListener('resize', rz); cancelAnimationFrame(raf); };
  }, []);

  return <canvas id="bg" ref={ref} />;
}
