/**
 * TaxonGuard logo. An original mark: a leaf (the taxon, a living thing) set
 * inside a shield (the guard, a verified record). It echoes GBIF's green,
 * leaf-forward identity without reproducing the GBIF logo.
 */
export function LogoMark({
  size = 28,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="TaxonGuard"
      className={className}
    >
      <path
        d="M16 3.2 L26.5 6.8 V15.2 C26.5 21.6 22.2 26.4 16 28.8 C9.8 26.4 5.5 21.6 5.5 15.2 V6.8 Z"
        fill="#61A350"
      />
      <path
        d="M16 9 C12.6 12, 12.6 16.4, 16 19.6 C19.4 16.4, 19.4 12, 16 9 Z"
        fill="#FFFFFF"
      />
      <path
        d="M16 10 L16 19"
        stroke="#61A350"
        strokeWidth="1.1"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function Logo({ className }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className ?? ""}`}>
      <LogoMark />
      <span className="text-xl font-bold tracking-tight text-ink">
        TaxonGuard
      </span>
    </span>
  );
}
