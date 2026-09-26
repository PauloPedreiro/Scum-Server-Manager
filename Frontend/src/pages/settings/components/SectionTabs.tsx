interface SectionTabsProps<T extends string> {
  sections: T[];
  activeSection: T;
  onSectionChange: (section: T) => void;
  formatLabel?: (section: T) => string;
}

export default function SectionTabs<T extends string>({
  sections,
  activeSection,
  onSectionChange,
  formatLabel = (s) => `[${s}]`,
}: SectionTabsProps<T>) {
  return (
    <div className="card p-2 sm:p-4">
      <div className="flex flex-wrap gap-2">
        {sections.map((section) => (
          <button
            key={section}
            onClick={() => onSectionChange(section)}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
              activeSection === section
                ? 'bg-scum-orange text-white'
                : 'bg-white/5 text-white/70 hover:bg-white/10 hover:text-white'
            }`}
          >
            {formatLabel(section)}
          </button>
        ))}
      </div>
    </div>
  );
}

