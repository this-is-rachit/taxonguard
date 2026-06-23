import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "link";

const VARIANTS: Record<Variant, string> = {
  // Solid blue primary action, per the app convention.
  primary:
    "rounded-md bg-secondary px-5 py-2.5 text-sm font-bold text-white hover:opacity-90 disabled:opacity-50",
  // Outlined secondary action.
  secondary:
    "rounded-md border border-hairline px-5 py-2.5 text-sm font-bold text-ink hover:border-primary hover:text-primary disabled:opacity-50",
  // Lightweight text action in the green accent.
  link: "text-sm font-bold text-primary hover:underline disabled:opacity-50",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

export function Button({
  variant = "primary",
  className = "",
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`${VARIANTS[variant]} focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary ${className}`}
      {...props}
    />
  );
}
