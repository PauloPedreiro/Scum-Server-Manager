import { ReactNode } from 'react';

type Props = {
  title: string;
  subtitle?: string;
  children: ReactNode;
};

export function ModuleToolPage({ title, subtitle, children }: Props) {
  return (
    <div className="space-y-4">
      <div className="card p-4">
        <div className="text-lg font-semibold">{title}</div>
        {subtitle && <div className="text-sm text-white/60">{subtitle}</div>}
      </div>
      {children}
    </div>
  );
}
