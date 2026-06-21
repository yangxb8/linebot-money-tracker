import { LanguageProvider } from "@/components/LanguageProvider";

const ERROR_MESSAGES: Record<string, string> = {
  auth_failed: "ログインに失敗しました。もう一度お試しください。",
  invalid_state:
    "ログインセッションの有効期限が切れました。もう一度お試しください。",
  line_oauth: "LINEログインが拒否されました。",
  missing_code: "LINEから認証情報を受け取れませんでした。",
};

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string; reason?: string }>;
}) {
  const params = await searchParams;
  const errorCode = params.error;
  const errorMessage =
    (errorCode && ERROR_MESSAGES[errorCode]) ||
    (errorCode ? "ログインに失敗しました。もう一度お試しください。" : null);
  const errorDetail = params.reason;

  return (
    <LanguageProvider>
      <main className="min-h-screen flex flex-col items-center justify-center bg-gray-50 px-6">
        <div className="w-full max-w-sm space-y-6 text-center">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">家計簿</h1>
            <p className="text-sm text-gray-500 mt-2">
              LINEボットで記録した支出を確認
            </p>
          </div>
          {errorMessage && (
            <div className="text-sm text-red-600 rounded-lg bg-red-50 px-3 py-2 text-left space-y-1">
              <p>{errorMessage}</p>
              {errorDetail && (
                <p className="text-xs text-red-500 break-all">{errorDetail}</p>
              )}
            </div>
          )}
          <a
            href="/api/auth/line/login"
            className="inline-flex w-full items-center justify-center rounded-xl bg-[#06C755] px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-[#05b34c]"
          >
            LINEでログイン
          </a>
        </div>
      </main>
    </LanguageProvider>
  );
}
