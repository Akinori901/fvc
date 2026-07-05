/**
 * EventBridge Scheduler の Asia/Tokyo タイムゾーン前提で
 * 単純な「曜日固定 + 時刻固定」cron 式から次回実行時刻を算出する。
 *
 * ブラウザの実行環境のタイムゾーンに依存せず、JST 基準で計算する。
 */

export interface SimpleCron {
  /** 0-59 */
  minute: number;
  /** 0-23 */
  hour: number;
  /** 0=日, 1=月, ..., 6=土。指定しなければ毎日 */
  daysOfWeek?: number[];
}

interface JstFields {
  year: number;
  month: number; // 1-12
  day: number;   // 1-31
  hour: number;
  minute: number;
  second: number;
  weekday: number; // 0=日, 6=土
}

/** Date を JST のフィールドに分解する */
function toJstFields(d: Date): JstFields {
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    weekday: "short",
    hour12: false,
  });
  const parts = fmt.formatToParts(d);
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? "0";
  const weekdayMap: Record<string, number> = {
    Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6,
  };
  // hour が "24" になることがあるので 24 → 0 に正規化
  const rawHour = parseInt(get("hour"), 10);
  return {
    year: parseInt(get("year"), 10),
    month: parseInt(get("month"), 10),
    day: parseInt(get("day"), 10),
    hour: rawHour === 24 ? 0 : rawHour,
    minute: parseInt(get("minute"), 10),
    second: parseInt(get("second"), 10),
    weekday: weekdayMap[get("weekday")] ?? 0,
  };
}

/** JSTの「年月日 時:分」を実時刻 Date に変換する */
function jstDateAt(year: number, month: number, day: number, hour: number, minute: number): Date {
  // JST = UTC+9。Date.UTC で UTC基準で組み立て、9時間引くと JST のその時刻になる。
  return new Date(Date.UTC(year, month - 1, day, hour - 9, minute, 0, 0));
}

/** JSTの「年月日」に n日加算した {year, month, day} を返す */
function addDaysJst(year: number, month: number, day: number, n: number): { year: number; month: number; day: number; weekday: number } {
  const base = jstDateAt(year, month, day, 12, 0); // 正午にしておけば DST等の影響なし(JSTにはないが念のため)
  const shifted = new Date(base.getTime() + n * 24 * 60 * 60 * 1000);
  const f = toJstFields(shifted);
  return { year: f.year, month: f.month, day: f.day, weekday: f.weekday };
}

/**
 * 与えられた基準時刻以降で、cron 式に最初に一致する Date を返す。
 *
 * 動作: JST 基準で「今日」から最大8日先までを走査し、
 *   1) 曜日が daysOfWeek に該当
 *   2) その日の hour:minute が base 以降
 * の最初の日時を返す。
 */
export function nextRunAt(cron: SimpleCron, base: Date = new Date()): Date {
  const baseJst = toJstFields(base);
  const days = cron.daysOfWeek ?? [0, 1, 2, 3, 4, 5, 6];

  for (let offset = 0; offset <= 8; offset++) {
    const { year, month, day, weekday } = addDaysJst(baseJst.year, baseJst.month, baseJst.day, offset);
    if (!days.includes(weekday)) continue;

    const candidate = jstDateAt(year, month, day, cron.hour, cron.minute);
    if (offset === 0 && candidate.getTime() <= base.getTime()) {
      // 今日のスケジュールはもう過ぎている
      continue;
    }
    return candidate;
  }
  // 通常ここには来ない（8日内に必ず該当があるはず）
  throw new Error("nextRunAt: no candidate found within 8 days");
}

/** Date を "YYYY-MM-DD HH:mm" (JST) で整形 */
export function formatJst(d: Date): string {
  const f = toJstFields(d);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${f.year}-${pad(f.month)}-${pad(f.day)} ${pad(f.hour)}:${pad(f.minute)}`;
}

/** Date を "MM-DD HH:mm" (JST) で整形（年が同じ時用） */
export function formatJstShort(d: Date): string {
  const f = toJstFields(d);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(f.month)}-${pad(f.day)} ${pad(f.hour)}:${pad(f.minute)}`;
}
