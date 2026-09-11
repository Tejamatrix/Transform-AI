"use client";

import { ReactNode, useEffect, useRef } from "react";

/** Gyroscopic wrapper: elements subtly lean toward the cursor (desktop)
 *  or device tilt (mobile). Lerped for a premium, weighty feel.
 *  Disabled automatically when the user prefers reduced motion. */
export function Gyro({
  children,
  strength = 9,
  tilt = 3.5,
  className = "",
}: {
  children: ReactNode;
  strength?: number;
  tilt?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let tx = 0, ty = 0, cx = 0, cy = 0, raf = 0;
    let active = true;

    const setTarget = (x: number, y: number) => { tx = x; ty = y; };
    const onMouse = (e: MouseEvent) =>
      setTarget((e.clientX / window.innerWidth - 0.5) * 2, (e.clientY / window.innerHeight - 0.5) * 2);
    const onOrient = (e: DeviceOrientationEvent) => {
      if (e.gamma == null || e.beta == null) return;
      setTarget(
        Math.max(-1, Math.min(1, e.gamma / 35)),
        Math.max(-1, Math.min(1, (e.beta - 40) / 35)),
      );
    };
    const loop = () => {
      if (!active) return;
      cx += (tx - cx) * 0.055;
      cy += (ty - cy) * 0.055;
      if (ref.current) {
        ref.current.style.transform =
          `perspective(1000px) translate3d(${(cx * strength).toFixed(2)}px, ${(cy * strength).toFixed(2)}px, 0) ` +
          `rotateX(${(-cy * tilt).toFixed(2)}deg) rotateY(${(cx * tilt).toFixed(2)}deg)`;
      }
      raf = requestAnimationFrame(loop);
    };
    window.addEventListener("mousemove", onMouse, { passive: true });
    window.addEventListener("deviceorientation", onOrient, { passive: true });
    raf = requestAnimationFrame(loop);
    return () => {
      active = false;
      window.removeEventListener("mousemove", onMouse);
      window.removeEventListener("deviceorientation", onOrient);
      cancelAnimationFrame(raf);
    };
  }, [strength, tilt]);

  return (
    <div ref={ref} className={`will-change-transform ${className}`} style={{ transformStyle: "preserve-3d" }}>
      {children}
    </div>
  );
}
