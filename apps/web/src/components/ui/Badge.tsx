import type { HTMLAttributes } from "react";

// A small, understated chip for reason codes and counts. Full rounding, muted
// fill, concise label, matching the design system's chip treatment.
interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: "neutral" | "primary" | "error";
}

const TONES = {
  neutral: "bg-panel text-muted",
  primary: "bg-primary/10 text-primary",
  error: "bg-error/10 text-error",
};

export function Badge({
  tone = "neutral",
  className = "",
  ...props
}: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold ${TONES[tone]} ${className}`}
      {...props}
    />
  );
}
