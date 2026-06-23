import type { HTMLAttributes } from "react";

// A light information container: white surface, hairline border, soft 8px
// corners, 16px padding. Flat by default, matching the design system.
interface CardProps extends HTMLAttributes<HTMLDivElement> {
  selected?: boolean;
}

export function Card({
  selected = false,
  className = "",
  ...props
}: CardProps) {
  const border = selected ? "border-secondary" : "border-hairline";
  return (
    <div
      className={`rounded-lg border ${border} bg-white p-sm ${className}`}
      {...props}
    />
  );
}
