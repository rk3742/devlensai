export function Badge({ children, tone = "default" }) {
  const tones = {
    default: "bg-base-800 text-ink-dim border-base-700",
    accent: "bg-accent/10 text-accent border-accent/30",
    warn: "bg-warn/10 text-warn border-warn/30",
    danger: "bg-danger/10 text-danger border-danger/30",
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-mono border ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function Card({ children, className = "" }) {
  return (
    <div className={`bg-base-900 border border-base-700 rounded-xl ${className}`}>
      {children}
    </div>
  );
}

export function Spinner({ size = 16 }) {
  return (
    <svg
      className="animate-spin text-accent"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity="0.2" />
      <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function Button({ children, variant = "primary", className = "", ...props }) {
  const variants = {
    primary: "bg-accent text-base-950 hover:bg-accent-dim font-semibold",
    secondary: "bg-base-800 text-ink border border-base-700 hover:border-base-600",
    ghost: "text-ink-dim hover:text-ink hover:bg-base-800",
    danger: "bg-danger/10 text-danger border border-danger/30 hover:bg-danger/20",
  };
  return (
    <button
      className={`px-4 py-2 rounded-lg text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2 ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

export function EmptyState({ icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-16 px-6">
      {icon && <div className="mb-4 text-ink-faint">{icon}</div>}
      <h3 className="font-mono text-ink text-lg mb-2">{title}</h3>
      {description && <p className="text-ink-dim text-sm max-w-sm mb-6">{description}</p>}
      {action}
    </div>
  );
}

export function ErrorBanner({ message }) {
  if (!message) return null;
  return (
    <div className="bg-danger/10 border border-danger/30 text-danger rounded-lg px-4 py-3 text-sm font-mono">
      {message}
    </div>
  );
}
