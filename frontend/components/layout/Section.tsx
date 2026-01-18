import { ReactNode } from "react";

interface SectionProps {
  title: string;
  description?: string;
  children: ReactNode;
  action?: ReactNode;
}

export function Section({ title, description, children, action }: SectionProps) {
  return (
    <section className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900 dark:text-white">
            {title}
          </h2>
          {description && (
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              {description}
            </p>
          )}
        </div>
        {action && <div>{action}</div>}
      </div>
      <div>{children}</div>
    </section>
  );
}
