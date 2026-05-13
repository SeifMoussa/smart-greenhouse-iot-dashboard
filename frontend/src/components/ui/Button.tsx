import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger" | "ghost";

const VARIANT_CLASSES: Record<Variant, string> = {
  primary:
    "bg-leaf-600 hover:bg-leaf-700 text-white focus-visible:ring-leaf-500 disabled:bg-leaf-400",
  secondary:
    "bg-slate-200 hover:bg-slate-300 text-slate-900 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-100 focus-visible:ring-slate-400 disabled:opacity-50",
  danger: "bg-red-600 hover:bg-red-700 text-white focus-visible:ring-red-500 disabled:bg-red-400",
  ghost:
    "bg-transparent hover:bg-slate-100 text-slate-700 dark:hover:bg-slate-800 dark:text-slate-200 focus-visible:ring-slate-400 disabled:opacity-50",
};

export function Button({
  variant = "primary",
  loading = false,
  className = "",
  children,
  disabled,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  loading?: boolean;
}) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-slate-950 ${VARIANT_CLASSES[variant]} ${className}`}
    >
      {loading && (
        <span
          aria-hidden="true"
          className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-r-transparent"
        />
      )}
      {children}
    </button>
  );
}
