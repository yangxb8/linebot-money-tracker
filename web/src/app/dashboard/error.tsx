"use client";

export default function DashboardError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 text-center space-y-4">
      <p className="text-sm text-gray-600">
        Something went wrong loading the dashboard.
      </p>
      <button
        type="button"
        onClick={reset}
        className="text-sm text-green-700 underline"
      >
        Try again
      </button>
    </div>
  );
}
