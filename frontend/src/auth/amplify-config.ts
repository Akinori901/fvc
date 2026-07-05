/**
 * AWS Amplify Auth (Cognito) 設定。
 *
 * `main.tsx` から副作用 import されることで `Amplify.configure()` が呼ばれる。
 * 環境変数 VITE_COGNITO_USER_POOL_ID 等が空の場合は configure をスキップし、
 * 既存の SimpleJWT 経路をそのまま使えるようにする (Phase C 移行期間中の安全弁)。
 *
 * 設計書: docs/design/cognito-oauth-migration.md §8.2
 */
import { Amplify } from "aws-amplify";

const userPoolId = import.meta.env.VITE_COGNITO_USER_POOL_ID;
const userPoolClientId = import.meta.env.VITE_COGNITO_WEB_CLIENT_ID;
const domainPrefix = import.meta.env.VITE_COGNITO_DOMAIN_PREFIX;
const region = import.meta.env.VITE_COGNITO_REGION ?? "ap-northeast-1";

if (userPoolId && userPoolClientId && domainPrefix) {
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId,
        userPoolClientId,
        loginWith: {
          oauth: {
            domain: `${domainPrefix}.auth.${region}.amazoncognito.com`,
            scopes: ["openid", "profile", "email"],
            redirectSignIn: [`${window.location.origin}/auth/callback`],
            redirectSignOut: [`${window.location.origin}/login`],
            responseType: "code",
          },
        },
      },
    },
  });
} else {
  // 環境変数未設定時は Amplify を初期化しない。Phase C の段階導入中・
  // ローカル開発で Cognito を使わない場合の動作を維持するため。
  console.info(
    "[amplify-config] VITE_COGNITO_* env vars not set. Cognito auth is disabled.",
  );
}
