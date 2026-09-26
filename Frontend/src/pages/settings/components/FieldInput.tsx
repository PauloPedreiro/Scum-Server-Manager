import { getFieldType } from '@/utils/fieldTypeDetector';
import { getFieldConstraints } from '@/utils/fieldConstraints';

interface FieldInputProps {
  keyName: string;
  value: string | number | boolean;
  onChange: (value: string | number | boolean) => void;
  displayName?: string;
}

export default function FieldInput({ keyName, value, onChange, displayName }: FieldInputProps) {
  const fieldType = getFieldType(keyName, String(value));
  const constraints = getFieldConstraints(keyName);

  // Campo Booleano - Toggle
  if (fieldType === 'boolean') {
    const normalizedValue = String(value).trim().toLowerCase();
    const isChecked =
      value === true ||
      value === 1 ||
      normalizedValue === 'true' ||
      normalizedValue === '1' ||
      normalizedValue === 'yes' ||
      normalizedValue === 'on';

    const usesNumericBoolean =
      typeof value === 'number' || normalizedValue === '0' || normalizedValue === '1';

    return (
      <div className="flex justify-end">
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={isChecked}
            onChange={(e) => {
              if (typeof value === 'boolean') {
                onChange(e.target.checked);
              } else if (usesNumericBoolean) {
                onChange(e.target.checked ? 1 : 0);
              } else {
                onChange(e.target.checked ? 'True' : 'False');
              }
            }}
            className="sr-only peer"
          />
          <div className={`relative inline-flex h-7 w-14 items-center rounded-full transition-all duration-200 ease-in-out shadow-lg peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-scum-orange peer-focus:ring-offset-2 peer-focus:ring-offset-gray-900 ${
            isChecked 
              ? 'bg-green-500 hover:bg-green-600' 
              : 'bg-gray-600 hover:bg-gray-500'
          }`}>
            <span
              className={`inline-block h-6 w-6 transform rounded-full bg-white shadow-md transition-transform duration-200 ease-in-out ${
                isChecked ? 'translate-x-7' : 'translate-x-0.5'
              }`}
            />
          </div>
        </label>
      </div>
    );
  }

  // Campo com opções específicas - Select
  if (constraints?.options) {
    const isValidOption = constraints.options.includes(String(value).trim());
    return (
      <select
        value={isValidOption ? String(value).trim() : ''}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent text-sm"
      >
        <option value="">-- Selecione --</option>
        {constraints.options.map((option) => (
          <option key={option} value={option} className="bg-gray-900">
            {option}
          </option>
        ))}
      </select>
    );
  }

  // Campo Numérico - Input Number
  if (fieldType === 'number') {
    // Extrair apenas a parte numérica do valor (remove sufixos como "g", "kg", etc.)
    const numericValue = String(value).replace(/[^0-9.-]/g, '');
    const displayValue = numericValue === '' ? '' : (isNaN(Number(numericValue)) ? '' : numericValue);
    
    return (
      <input
        type="number"
        min={constraints?.min}
        max={constraints?.max}
        step={constraints?.step ?? 'any'}
        value={displayValue}
        onChange={(e) => {
          let newValue = e.target.value;
          if (constraints?.decimalPlaces !== undefined && newValue.includes('.')) {
            const parts = newValue.split('.');
            if (parts[1] && parts[1].length > constraints.decimalPlaces) {
              newValue = `${parts[0]}.${parts[1].substring(0, constraints.decimalPlaces)}`;
            }
          }
          onChange(newValue === '' ? '' : parseFloat(newValue) || 0);
        }}
        className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent text-sm"
      />
    );
  }

  // Campo de Tempo - Input Text
  if (fieldType === 'time') {
    return (
      <input
        type="text"
        value={String(value || '')}
        onChange={(e) => onChange(e.target.value)}
        placeholder="HH:MM:SS"
        pattern={constraints?.pattern || "\\d{1,2}:\\d{2}:\\d{2}"}
        maxLength={constraints?.maxLength ?? 8}
        className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent text-sm"
      />
    );
  }

  // Campo de Texto - Input Text padrão
  return (
    <input
      type="text"
      value={String(value || '')}
      onChange={(e) => onChange(e.target.value)}
      maxLength={constraints?.maxLength}
      pattern={constraints?.pattern}
      className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-scum-orange focus:border-transparent text-sm"
    />
  );
}

