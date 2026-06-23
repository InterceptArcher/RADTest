/**
 * RegionToggle — v3.1. "Canada only" checkbox for the new-job form. When checked,
 * the backend scopes the CONTACT pipeline to Canadian employees only (general
 * company intelligence stays global). Controlled component.
 */
'use client';

interface RegionToggleProps {
  checked: boolean;
  onChange: (value: boolean) => void;
}

export default function RegionToggle({ checked, onChange }: RegionToggleProps) {
  return (
    <label className="flex items-start gap-2 cursor-pointer select-none">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 h-4 w-4 rounded border-slate-300"
      />
      <span className="text-sm text-slate-700">
        <span className="font-medium">Canada only</span>
        <span className="block text-xs text-slate-500">
          Limit stakeholder contacts to Canadian employees (company intelligence stays global).
        </span>
      </span>
    </label>
  );
}
