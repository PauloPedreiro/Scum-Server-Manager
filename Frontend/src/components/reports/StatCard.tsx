interface StatCardProps {
  label: string;
  value: string | number;
  unit?: string;
  color?: string;
}

export function StatCard({ label, value, unit, color = 'text-white' }: StatCardProps) {
  return (
    <div className="p-3 sm:p-4 rounded-xl bg-black/30 border border-white/5">
      <div className="text-xs sm:text-sm text-white/70 mb-1">{label}</div>
      <div className={`text-xl sm:text-2xl font-bold ${color}`}>
        {value}
      </div>
      {unit && (
        <div className="text-xs text-white/50 mt-1">{unit}</div>
      )}
    </div>
  );
}
