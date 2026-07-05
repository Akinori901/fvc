import { useEffect, useState } from "react";
import {
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  FormHelperText,
  InputLabel,
  MenuItem,
  Radio,
  RadioGroup,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { useFamilyMembers } from "@/hooks/useFamilyPortfolio";
import { useCreateGoal, useUpdateGoal } from "@/hooks/useGoals";
import type { FinancialGoal } from "@/types/goals";

interface Props {
  open: boolean;
  onClose: () => void;
  goal: FinancialGoal | null; // null = 新規作成
}

const CURRENT_YEAR = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: 51 }, (_, i) => CURRENT_YEAR + i);
const MONTH_OPTIONS = Array.from({ length: 12 }, (_, i) => i + 1);

export default function GoalEditDialog({ open, onClose, goal }: Props) {
  const { data: members = [] } = useFamilyMembers();
  const createMut = useCreateGoal();
  const updateMut = useUpdateGoal();

  const [name, setName] = useState("");
  const [targetValue, setTargetValue] = useState("");
  const [targetYear, setTargetYear] = useState<number>(CURRENT_YEAR + 5);
  const [targetMonth, setTargetMonth] = useState<number>(1);
  const [scopeType, setScopeType] = useState<"family" | "members">("family");
  const [memberIds, setMemberIds] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);

  // ダイアログ起動時に初期値を設定
  useEffect(() => {
    if (!open) return;
    if (goal) {
      setName(goal.name);
      setTargetValue(String(goal.target_value_jpy));
      const [y, m] = goal.target_date.split("-");
      setTargetYear(Number(y));
      setTargetMonth(Number(m));
      setScopeType(goal.scope_type);
      setMemberIds(goal.member_ids);
    } else {
      setName("");
      setTargetValue("");
      setTargetYear(CURRENT_YEAR + 5);
      setTargetMonth(1);
      setScopeType("family");
      setMemberIds([]);
    }
    setError(null);
  }, [open, goal]);

  const handleSubmit = async () => {
    setError(null);
    const targetNum = Number(targetValue.replace(/,/g, ""));
    if (!Number.isFinite(targetNum) || targetNum <= 0) {
      setError("目標金額は0より大きい数値で入力してください");
      return;
    }
    if (!name.trim()) {
      setError("目標名を入力してください");
      return;
    }
    if (scopeType === "members" && memberIds.length === 0) {
      setError("メンバーを1人以上選択してください");
      return;
    }
    const targetDate = `${targetYear}-${String(targetMonth).padStart(2, "0")}-01`;
    const payload = {
      name: name.trim(),
      target_value_jpy: targetNum,
      target_date: targetDate,
      scope_type: scopeType,
      member_ids: scopeType === "members" ? memberIds : [],
    };
    try {
      if (goal) {
        await updateMut.mutateAsync({ id: goal.id, data: payload });
      } else {
        await createMut.mutateAsync(payload);
      }
      onClose();
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      setError(err?.response?.data?.detail ?? "保存に失敗しました");
    }
  };

  const toggleMember = (id: number) => {
    setMemberIds((prev) => (prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]));
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{goal ? "目標を編集" : "新規目標"}</DialogTitle>
      <DialogContent>
        <Stack spacing={2.5} sx={{ mt: 1 }}>
          <TextField
            label="目標名"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="例: 5000万円到達"
            fullWidth
            autoFocus
          />
          <TextField
            label="目標金額（円）"
            value={targetValue}
            onChange={(e) => setTargetValue(e.target.value)}
            placeholder="例: 50000000"
            fullWidth
            inputMode="numeric"
          />
          <Stack direction="row" spacing={2}>
            <FormControl fullWidth>
              <InputLabel>達成目標年</InputLabel>
              <Select
                label="達成目標年"
                value={targetYear}
                onChange={(e) => setTargetYear(Number(e.target.value))}
              >
                {YEAR_OPTIONS.map((y) => (
                  <MenuItem key={y} value={y}>
                    {y}年
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl fullWidth>
              <InputLabel>達成目標月</InputLabel>
              <Select
                label="達成目標月"
                value={targetMonth}
                onChange={(e) => setTargetMonth(Number(e.target.value))}
              >
                {MONTH_OPTIONS.map((m) => (
                  <MenuItem key={m} value={m}>
                    {m}月
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>
          <FormControl>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
              スコープ
            </Typography>
            <RadioGroup
              row
              value={scopeType}
              onChange={(e) => setScopeType(e.target.value as "family" | "members")}
            >
              <FormControlLabel value="family" control={<Radio />} label="家族合計" />
              <FormControlLabel value="members" control={<Radio />} label="メンバー指定" />
            </RadioGroup>
            <FormHelperText>
              {scopeType === "family"
                ? "家族合算に含む全メンバーが対象になります"
                : "下記から対象メンバーを選択してください"}
            </FormHelperText>
          </FormControl>
          {scopeType === "members" && (
            <Box>
              {members.map((m) => (
                <FormControlLabel
                  key={m.id}
                  control={
                    <Checkbox
                      checked={memberIds.includes(m.id ?? -1)}
                      onChange={() => toggleMember(m.id ?? -1)}
                    />
                  }
                  label={m.name}
                />
              ))}
            </Box>
          )}
          {error && (
            <Typography variant="body2" color="error.main">
              {error}
            </Typography>
          )}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>キャンセル</Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={createMut.isPending || updateMut.isPending}
        >
          保存
        </Button>
      </DialogActions>
    </Dialog>
  );
}
