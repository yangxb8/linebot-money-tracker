"use client";

type Props = {
  value: string;
  onChange: (value: string) => void;
  invalid?: boolean;
  min?: string;
  max?: string;
  className?: string;
  id?: string;
};

export function IsoDateInput({
  value,
  onChange,
  invalid = false,
  min,
  max,
  className = "",
  id,
}: Props) {
  return (
    <input
      id={id}
      type="date"
      value={value}
      min={min}
      max={max}
      onChange={(e) => onChange(e.target.value)}
      className={`w-full rounded-lg border px-3 py-2 text-sm ${
        invalid
          ? "border-red-500 focus:border-red-500 focus:outline-none focus:ring-2 focus:ring-red-200"
          : "border-gray-200 focus:border-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-100"
      } ${className}`}
    />
  );
}
