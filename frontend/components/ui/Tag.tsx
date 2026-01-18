import { HTMLAttributes, forwardRef } from "react";

type TagVariant =
  | "default"
  | "primary"
  | "success"
  | "warning"
  | "danger"
  | "info";

interface TagProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: TagVariant;
  size?: "sm" | "md";
}

const variantStyles: Record<TagVariant, string> = {
  default:
    "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300",
  primary: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  success:
    "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200",
  warning:
    "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  danger: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  info: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200",
};

const sizeStyles = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-sm",
};

export const Tag = forwardRef<HTMLSpanElement, TagProps>(
  ({ variant = "default", size = "md", className = "", children, ...props }, ref) => {
    return (
      <span
        ref={ref}
        className={`
          inline-flex items-center
          font-medium rounded-full
          ${variantStyles[variant]}
          ${sizeStyles[size]}
          ${className}
        `}
        {...props}
      >
        {children}
      </span>
    );
  }
);

Tag.displayName = "Tag";
