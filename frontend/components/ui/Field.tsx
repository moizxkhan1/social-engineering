import { InputHTMLAttributes, forwardRef } from "react";

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export const Field = forwardRef<HTMLInputElement, FieldProps>(
  ({ label, error, hint, className = "", id, ...props }, ref) => {
    const fieldId = id || props.name;

    return (
      <div className="space-y-1.5">
        {label && (
          <label
            htmlFor={fieldId}
            className="block text-sm font-medium text-slate-700 dark:text-slate-300"
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={fieldId}
          className={`
            w-full px-4 py-2.5
            text-slate-900 dark:text-slate-100
            bg-white dark:bg-slate-800
            border rounded-lg
            transition-colors duration-150
            placeholder:text-slate-400 dark:placeholder:text-slate-500
            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
            disabled:bg-slate-100 disabled:cursor-not-allowed dark:disabled:bg-slate-900
            ${
              error
                ? "border-red-500 focus:ring-red-500"
                : "border-slate-300 dark:border-slate-600"
            }
            ${className}
          `}
          {...props}
        />
        {error && (
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        )}
        {hint && !error && (
          <p className="text-sm text-slate-500 dark:text-slate-400">{hint}</p>
        )}
      </div>
    );
  }
);

Field.displayName = "Field";
