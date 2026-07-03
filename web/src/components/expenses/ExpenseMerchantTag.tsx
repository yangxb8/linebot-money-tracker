type Props = {
  label: string;
};

export function ExpenseMerchantTag({ label }: Props) {
  return (
    <span className="inline-block max-w-full truncate rounded-full bg-blue-50 px-2 py-0.5 text-xs text-blue-700">
      {label}
    </span>
  );
}
