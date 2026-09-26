import FieldInput from './FieldInput';

interface FieldCardProps {
  keyName: string;
  value: string | number | boolean;
  displayName: string;
  onChange: (value: string | number | boolean) => void;
}

export default function FieldCard({ keyName, value, displayName, onChange }: FieldCardProps) {
  return (
    <div className="flex flex-col gap-3 p-4 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 transition-colors">
      <div className="flex-1 min-w-0">
        <label className="block text-sm font-medium text-white/90 mb-1 break-words">
          {displayName}
        </label>
        <p className="text-xs text-white/40">
          <code className="text-white/60">{keyName}</code>
        </p>
      </div>
      <div className="w-full">
        <FieldInput
          keyName={keyName}
          value={value}
          onChange={onChange}
          displayName={displayName}
        />
      </div>
    </div>
  );
}

