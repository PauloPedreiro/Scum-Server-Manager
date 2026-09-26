import { ReactNode } from 'react';

type Props = {
  title: string;
  subtitle?: string;
  children: ReactNode;
  right?: ReactNode;
};

export function ActionToolPage({ title, subtitle, children, right }: Props) {
  return (
    <div className="space-y-4">
      <div className="card p-4 flex items-start gap-3">
        <div className="min-w-0">
          <div className="text-lg font-semibold">{title}</div>
          {subtitle && <div className="text-sm text-white/60">{subtitle}</div>}
        </div>
        {right && <div className="ml-auto">{right}</div>}
      </div>
      {children}
    </div>
  );
}
