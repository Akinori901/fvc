import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Stack,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  IconButton,
  Divider,
  Avatar,
  FormControlLabel,
  Switch,
  Tooltip,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import CalendarMonthIcon from "@mui/icons-material/CalendarMonth";
import PersonIcon from "@mui/icons-material/Person";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import HistoryToggleOffIcon from "@mui/icons-material/HistoryToggleOff";
import {
  useFamilyMembers,
  usePortfolioAccounts,
  useCreateFamilyMember,
  useUpdateFamilyMember,
  useDeleteFamilyMember,
  useCreatePortfolioAccount,
  useUpdatePortfolioAccount,
  useDeletePortfolioAccount,
} from "@/hooks/useFamilyPortfolio";
import { formatCurrency } from "@/utils/format";
import CsvImportDialog from "./CsvImportDialog";
import {
  MEMBER_ROLE_LABELS,
  INSTITUTION_TYPE_LABELS,
  ASSET_CLASS_LABELS,
  TRADING_TYPE_LABELS,
  MARGIN_CREDIT_TYPE_LABELS,
} from "@/types/familyPortfolio";
import type {
  FamilyMember,
  FamilyMemberInput,
  MemberRole,
  InstitutionType,
  AssetClass,
  TradingType,
  MarginCreditType,
  PortfolioAccount,
  PortfolioAccountInput,
  AccountRow,
  ImportWarning,
} from "@/types/familyPortfolio";

// 取込漏れ警告の表示定義
const IMPORT_WARNING_META: Record<
  ImportWarning,
  { label: string; tooltip: string }
> = {
  no_detail: {
    label: "明細なし",
    tooltip:
      "この口座は明細（保有銘柄）がありません。専用CSVでの取り込みが必要かもしれません（信用・iDeCo・ジュニアNISA等は総合CSVに含まれません）。全て売却済みの場合はこの警告は無視できます。",
  },
  stale: {
    label: "更新が古い",
    tooltip:
      "最新の残高が14日以上前です。CSVの取り込みが止まっている可能性があります。",
  },
};

const MEMBER_ROLES = Object.entries(MEMBER_ROLE_LABELS) as [MemberRole, string][];
const INSTITUTION_TYPES = Object.entries(INSTITUTION_TYPE_LABELS) as [InstitutionType, string][];
const ASSET_CLASSES = Object.entries(ASSET_CLASS_LABELS) as [AssetClass, string][];
const TRADING_TYPES = Object.entries(TRADING_TYPE_LABELS) as [TradingType, string][];
const MARGIN_CREDIT_TYPES = Object.entries(MARGIN_CREDIT_TYPE_LABELS) as [MarginCreditType, string][];
const CURRENCIES = ["JPY", "USD"];

const PRESET_COLORS = [
  "#1976d2", "#7b1fa2", "#c62828", "#2e7d32",
  "#e65100", "#00838f", "#4527a0", "#827717",
];

interface AccountsTabProps {
  accountRows?: AccountRow[];
}

export default function AccountsTab({ accountRows = [] }: AccountsTabProps) {
  const navigate = useNavigate();
  const { data: members = [] } = useFamilyMembers();
  const { data: accounts = [] } = usePortfolioAccounts();
  const createMember = useCreateFamilyMember();
  const updateMember = useUpdateFamilyMember();
  const deleteMember = useDeleteFamilyMember();
  const createAccount = useCreatePortfolioAccount();
  const updateAccount = useUpdatePortfolioAccount();
  const deleteAccount = useDeletePortfolioAccount();

  // 家族メンバーダイアログ
  const [memberDialog, setMemberDialog] = useState(false);
  const [editMember, setEditMember] = useState<FamilyMember | null>(null);
  const [mName, setMName] = useState("");
  const [mRole, setMRole] = useState<MemberRole>("self");
  const [mColor, setMColor] = useState(PRESET_COLORS[0]);
  const [mIncludeInTotal, setMIncludeInTotal] = useState(true);

  // CSVインポートダイアログ
  const [csvImportDialog, setCsvImportDialog] = useState(false);

  // 口座ダイアログ
  const [accountDialog, setAccountDialog] = useState(false);
  const [editAccount, setEditAccount] = useState<PortfolioAccount | null>(null);
  const [aMemberId, setAMemberId] = useState<number | "">("");
  const [aInstitution, setAInstitution] = useState("");
  const [aType, setAType] = useState<InstitutionType>("securities_jp");
  const [aClass, setAClass] = useState<AssetClass>("jp_stock");
  const [aTradingType, setATradingType] = useState<TradingType>("spot");
  const [aMarginCreditType, setAMarginCreditType] = useState<MarginCreditType | "">("");
  const [aMarginInterestRate, setAMarginInterestRate] = useState<string>("");
  const [aNickname, setANickname] = useState("");
  const [aCurrency, setACurrency] = useState("JPY");

  // 最新残高マップ（account_id → AccountRow）
  const latestByAccount = Object.fromEntries(accountRows.map((r) => [r.id, r]));

  const openAddMember = () => {
    setEditMember(null);
    setMName(""); setMRole("self"); setMColor(PRESET_COLORS[0]); setMIncludeInTotal(true);
    setMemberDialog(true);
  };
  const openEditMember = (m: FamilyMember) => {
    setEditMember(m);
    setMName(m.name); setMRole(m.role); setMColor(m.color_code); setMIncludeInTotal(m.include_in_family_total);
    setMemberDialog(true);
  };
  const handleSaveMember = () => {
    const data: FamilyMemberInput = { name: mName, role: mRole, color_code: mColor, include_in_family_total: mIncludeInTotal };
    const onSuccess = () => setMemberDialog(false);
    if (editMember) {
      updateMember.mutate({ id: editMember.id, data }, { onSuccess });
    } else {
      createMember.mutate(data, { onSuccess });
    }
  };

  const openAddAccount = (memberId?: number) => {
    setEditAccount(null);
    setAMemberId(memberId ?? (members[0]?.id ?? ""));
    setAInstitution(""); setAType("securities_jp"); setAClass("jp_stock"); setATradingType("spot");
    setAMarginCreditType(""); setAMarginInterestRate("");
    setANickname(""); setACurrency("JPY");
    setAccountDialog(true);
  };
  const openEditAccount = (a: PortfolioAccount) => {
    setEditAccount(a);
    setAMemberId(a.family_member_id);
    setAInstitution(a.institution); setAType(a.institution_type);
    setAClass(a.asset_class); setATradingType(a.trading_type ?? "spot"); setANickname(a.nickname); setACurrency(a.currency);
    setAMarginCreditType((a.margin_credit_type ?? "") as MarginCreditType | "");
    setAMarginInterestRate(a.margin_interest_rate ?? "");
    setAccountDialog(true);
  };
  const handleSaveAccount = () => {
    if (!aMemberId || !aInstitution) return;
    const data: PortfolioAccountInput = {
      family_member_id: aMemberId as number,
      institution: aInstitution,
      institution_type: aType,
      asset_class: aClass,
      trading_type: aTradingType,
      nickname: aNickname,
      currency: aCurrency,
      margin_credit_type: aTradingType === "margin" && aMarginCreditType ? aMarginCreditType : null,
      margin_interest_rate: aTradingType === "margin" && aMarginInterestRate ? aMarginInterestRate : null,
    };
    const onSuccess = () => setAccountDialog(false);
    if (editAccount) {
      updateAccount.mutate({ id: editAccount.id, data }, { onSuccess });
    } else {
      createAccount.mutate(data, { onSuccess });
    }
  };

  // メンバーIDでグルーピング
  const accountsByMember = members.reduce<Record<number, PortfolioAccount[]>>((acc, m) => {
    acc[m.id] = accounts.filter((a) => a.family_member_id === m.id && a.is_active);
    return acc;
  }, {});

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h6">口座・資産管理</Typography>
        <Stack direction="row" spacing={1}>
          <Button size="small" startIcon={<UploadFileIcon />} onClick={() => setCsvImportDialog(true)} variant="outlined" color="success">
            CSV取込
          </Button>
          <Button size="small" startIcon={<PersonIcon />} onClick={openAddMember} variant="outlined">
            メンバー追加
          </Button>
          <Button size="small" startIcon={<AddIcon />} onClick={() => openAddAccount()} variant="contained">
            口座追加
          </Button>
        </Stack>
      </Stack>

      {members.length === 0 ? (
        <Card>
          <CardContent>
            <Typography color="text.secondary" align="center">
              まず「メンバー追加」で家族を登録してください。
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <Stack spacing={3}>
          {members.map((member) => (
            <Box key={member.id}>
              <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                <Avatar sx={{ bgcolor: member.color_code, width: 28, height: 28, fontSize: 13 }}>
                  {member.name[0]}
                </Avatar>
                <Typography variant="subtitle1" fontWeight="bold">
                  {member.name}
                  <Chip label={member.role_display} size="small" sx={{ ml: 1 }} />
                  {!member.include_in_family_total && (
                    <Chip label="合算対象外" size="small" variant="outlined" color="warning" />
                  )}
                </Typography>
                <IconButton size="small" onClick={() => openEditMember(member)}>
                  <EditIcon fontSize="small" />
                </IconButton>
                <IconButton
                  size="small"
                  color="error"
                  onClick={() => deleteMember.mutate(member.id)}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
                <Button size="small" startIcon={<AddIcon />} onClick={() => openAddAccount(member.id)}>
                  口座追加
                </Button>
              </Stack>

              {(accountsByMember[member.id] ?? []).length === 0 ? (
                <Typography variant="body2" color="text.secondary" sx={{ pl: 2 }}>
                  口座が登録されていません。
                </Typography>
              ) : (
                <Stack spacing={1}>
                  {(accountsByMember[member.id] ?? []).map((acc) => {
                    const latest = latestByAccount[acc.id];
                    return (
                      <Card key={acc.id} variant="outlined">
                        <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                          <Stack direction="row" justifyContent="space-between" alignItems="center">
                            <Box>
                              <Stack direction="row" spacing={1} alignItems="center">
                                <Typography variant="body1" fontWeight="bold">
                                  {acc.nickname || acc.institution}
                                </Typography>
                                {acc.nickname && (
                                  <Typography variant="body2" color="text.secondary">
                                    {acc.institution}
                                  </Typography>
                                )}
                                <Chip label={acc.institution_type_display} size="small" variant="outlined" />
                                <Chip label={acc.asset_class_display} size="small" color="primary" variant="outlined" />
                                {acc.trading_type === "margin" && (
                                  <Chip label="信用" size="small" color="warning" variant="outlined" />
                                )}
                                {acc.currency !== "JPY" && (
                                  <Chip label={acc.currency} size="small" color="warning" />
                                )}
                                {(acc.import_warnings ?? []).map((w) => (
                                  <Tooltip key={w} title={IMPORT_WARNING_META[w].tooltip}>
                                    <Chip
                                      icon={
                                        w === "no_detail" ? (
                                          <WarningAmberIcon />
                                        ) : (
                                          <HistoryToggleOffIcon />
                                        )
                                      }
                                      label={IMPORT_WARNING_META[w].label}
                                      size="small"
                                      color="warning"
                                      variant="outlined"
                                    />
                                  </Tooltip>
                                ))}
                              </Stack>
                              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                                {latest?.latest_value_jpy != null
                                  ? `最新残高: ${formatCurrency(Number(latest.latest_value_jpy))}（${latest.latest_date}）`
                                  : "残高未入力"}
                              </Typography>
                            </Box>
                            <Stack direction="row" spacing={0.5}>
                              <Button
                                size="small"
                                startIcon={<CalendarMonthIcon />}
                                onClick={() => navigate(`/portfolio/accounts/${acc.id}/input`)}
                              >
                                月次入力
                              </Button>
                              <IconButton size="small" onClick={() => openEditAccount(acc)}>
                                <EditIcon fontSize="small" />
                              </IconButton>
                              <IconButton
                                size="small"
                                color="error"
                                onClick={() => deleteAccount.mutate(acc.id)}
                              >
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </Stack>
                          </Stack>
                        </CardContent>
                      </Card>
                    );
                  })}
                </Stack>
              )}
              <Divider sx={{ mt: 2 }} />
            </Box>
          ))}
        </Stack>
      )}

      {/* 家族メンバーダイアログ */}
      <Dialog open={memberDialog} onClose={() => setMemberDialog(false)} maxWidth="xs" fullWidth>
        <DialogTitle>{editMember ? "メンバー編集" : "メンバー追加"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              label="名前"
              value={mName}
              onChange={(e) => setMName(e.target.value)}
              fullWidth
              required
            />
            <TextField
              select
              label="役割"
              value={mRole}
              onChange={(e) => setMRole(e.target.value as MemberRole)}
              fullWidth
            >
              {MEMBER_ROLES.map(([k, v]) => (
                <MenuItem key={k} value={k}>{v}</MenuItem>
              ))}
            </TextField>
            <Box>
              <Typography variant="body2" gutterBottom>カラー</Typography>
              <Stack direction="row" spacing={1}>
                {PRESET_COLORS.map((c) => (
                  <Box
                    key={c}
                    onClick={() => setMColor(c)}
                    sx={{
                      width: 28, height: 28, borderRadius: "50%", bgcolor: c, cursor: "pointer",
                      border: mColor === c ? "3px solid #000" : "2px solid transparent",
                    }}
                  />
                ))}
              </Stack>
            </Box>
            <FormControlLabel
              control={
                <Switch
                  checked={mIncludeInTotal}
                  onChange={(e) => setMIncludeInTotal(e.target.checked)}
                />
              }
              label="家族合算に含める"
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setMemberDialog(false)}>キャンセル</Button>
          <Button
            variant="contained"
            onClick={handleSaveMember}
            disabled={!mName || createMember.isPending || updateMember.isPending}
          >
            保存
          </Button>
        </DialogActions>
      </Dialog>

      {/* CSVインポートダイアログ */}
      <CsvImportDialog open={csvImportDialog} onClose={() => setCsvImportDialog(false)} />

      {/* 口座ダイアログ */}
      <Dialog open={accountDialog} onClose={() => setAccountDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editAccount ? "口座編集" : "口座追加"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <TextField
              select
              label="家族メンバー"
              value={aMemberId}
              onChange={(e) => setAMemberId(Number(e.target.value))}
              fullWidth
              required
            >
              {members.map((m) => (
                <MenuItem key={m.id} value={m.id}>{m.name}</MenuItem>
              ))}
            </TextField>
            <TextField
              label="機関名"
              value={aInstitution}
              onChange={(e) => setAInstitution(e.target.value)}
              fullWidth
              required
              placeholder="例: 楽天証券、SBI証券、楽天銀行"
            />
            <TextField
              select
              label="機関種別"
              value={aType}
              onChange={(e) => setAType(e.target.value as InstitutionType)}
              fullWidth
            >
              {INSTITUTION_TYPES.map(([k, v]) => (
                <MenuItem key={k} value={k}>{v}</MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="資産クラス"
              value={aClass}
              onChange={(e) => setAClass(e.target.value as AssetClass)}
              fullWidth
            >
              {ASSET_CLASSES.map(([k, v]) => (
                <MenuItem key={k} value={k}>{v}</MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="取引方式"
              value={aTradingType}
              onChange={(e) => setATradingType(e.target.value as TradingType)}
              fullWidth
            >
              {TRADING_TYPES.map(([k, v]) => (
                <MenuItem key={k} value={k}>{v}</MenuItem>
              ))}
            </TextField>
            {aTradingType === "margin" && (
              <>
                <TextField
                  select
                  label="信用枠区分"
                  value={aMarginCreditType}
                  onChange={(e) => setAMarginCreditType(e.target.value as MarginCreditType | "")}
                  fullWidth
                  helperText="制度信用 / 一般信用の区分。期限・現引き計算に使用"
                >
                  <MenuItem value="">未設定</MenuItem>
                  {MARGIN_CREDIT_TYPES.map(([k, v]) => (
                    <MenuItem key={k} value={k}>{v}</MenuItem>
                  ))}
                </TextField>
                <TextField
                  label="信用金利 (年率、例: 0.0285)"
                  value={aMarginInterestRate}
                  onChange={(e) => setAMarginInterestRate(e.target.value)}
                  fullWidth
                  type="number"
                  inputProps={{ step: "0.0001", min: "0", max: "1" }}
                  helperText="例: 楽天証券制度信用 = 0.0285 (2.85%)"
                />
              </>
            )}
            <TextField
              label="表示名（任意）"
              value={aNickname}
              onChange={(e) => setANickname(e.target.value)}
              fullWidth
              placeholder="例: NISA口座、メイン証券"
            />
            <TextField
              select
              label="通貨"
              value={aCurrency}
              onChange={(e) => setACurrency(e.target.value)}
              fullWidth
            >
              {CURRENCIES.map((c) => <MenuItem key={c} value={c}>{c}</MenuItem>)}
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAccountDialog(false)}>キャンセル</Button>
          <Button
            variant="contained"
            onClick={handleSaveAccount}
            disabled={!aMemberId || !aInstitution || createAccount.isPending || updateAccount.isPending}
          >
            保存
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
