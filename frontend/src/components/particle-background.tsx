"use client";

import { useEffect, useRef } from "react";

export function ParticleBackground() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const count = 30;
    const particles: HTMLDivElement[] = [];

    for (let i = 0; i < count; i++) {
      const p = document.createElement("div");
      p.style.cssText =
        "position:absolute;border-radius:50%;background:#00d4ff;pointer-events:none;";
      p.style.left = `${Math.random() * 100}%`;
      p.style.top = "100%";
      const size = 1 + Math.random() * 2;
      p.style.width = `${size}px`;
      p.style.height = `${size}px`;
      p.style.animation = `particle-float-landing ${6 + Math.random() * 6}s linear infinite`;
      p.style.animationDelay = `${Math.random() * 8}s`;
      p.style.opacity = String(0.3 + Math.random() * 0.4);
      container.appendChild(p);
      particles.push(p);
    }

    return () => {
      particles.forEach((p) => p.remove());
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 pointer-events-none z-[2]"
      aria-hidden="true"
    />
  );
}
