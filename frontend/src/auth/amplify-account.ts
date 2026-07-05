/**
 * Cognito (Amplify) 経由のアカウント操作ヘルパー。
 *
 * パスワード変更とメール変更を Amplify Auth に薄くラップする。
 * `SettingsPage` から呼ばれ、ログイン中のユーザーが自分の Cognito User Pool
 * 上の属性を更新できる。
 *
 * メール変更は Cognito の仕様上 2 段階:
 * 1. `updateUserAttributes` で新メアド送信 → Cognito が確認コードをメール送信
 * 2. `confirmUserAttribute` で確認コードを送って確定
 *
 * 設計書: docs/design/cognito-oauth-migration.md §8.5
 */
import {
  confirmUserAttribute,
  updatePassword,
  updateUserAttributes,
} from "aws-amplify/auth";

export async function changeCognitoPassword(
  oldPassword: string,
  newPassword: string,
): Promise<void> {
  await updatePassword({ oldPassword, newPassword });
}

/**
 * メアド変更フロー Step 1: Cognito にメアド更新リクエストを送る。
 * Cognito が新メアドに確認コードをメール送信する。
 * @returns true = コード入力フェーズに進む必要あり / false = 即時反映済み
 *   (email_verified=true で属性更新が即時に確定するケース)
 */
export async function startCognitoEmailUpdate(newEmail: string): Promise<boolean> {
  const result = await updateUserAttributes({
    userAttributes: { email: newEmail },
  });
  const emailUpdate = result.email;
  if (!emailUpdate) {
    // result に email が含まれない場合は即時反映扱い (実質起こらないが安全側)
    return false;
  }
  // CONFIRM_ATTRIBUTE_WITH_CODE → コード入力が必要
  // DONE → 確認不要、即時反映
  return emailUpdate.nextStep.updateAttributeStep === "CONFIRM_ATTRIBUTE_WITH_CODE";
}

/**
 * メアド変更フロー Step 2: 受け取った確認コードで確定する。
 */
export async function confirmCognitoEmailUpdate(
  confirmationCode: string,
): Promise<void> {
  await confirmUserAttribute({
    userAttributeKey: "email",
    confirmationCode,
  });
}
