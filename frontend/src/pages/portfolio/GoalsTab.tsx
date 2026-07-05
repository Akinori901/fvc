import { useEffect, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  IconButton,
  Stack,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import DragIndicatorIcon from "@mui/icons-material/DragIndicator";
import {
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { restrictToVerticalAxis } from "@dnd-kit/modifiers";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import LoadingSpinner from "@/components/common/LoadingSpinner";
import { useFamilyMembers } from "@/hooks/useFamilyPortfolio";
import { useDeleteGoal, useGoalProgress, useGoals, useReorderGoals } from "@/hooks/useGoals";
import type { FinancialGoal } from "@/types/goals";

import GoalEditDialog from "./GoalEditDialog";
import GoalProgressCard from "./GoalProgressCard";
import GoalProgressChart from "./GoalProgressChart";

function GoalDetailSection({ goal }: { goal: FinancialGoal }) {
  const { data: progress, isLoading } = useGoalProgress(goal.id);
  if (isLoading || !progress) {
    return (
      <Box sx={{ py: 3 }}>
        <LoadingSpinner />
      </Box>
    );
  }
  return (
    <Stack spacing={2} sx={{ mt: 2 }}>
      <GoalProgressCard progress={progress} />
      <GoalProgressChart progress={progress} />
    </Stack>
  );
}

interface SortableGoalCardProps {
  goal: FinancialGoal;
  isExpanded: boolean;
  scopeLabel: string;
  targetDate: string;
  onToggleExpand: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

function SortableGoalCard({
  goal,
  isExpanded,
  scopeLabel,
  targetDate,
  onToggleExpand,
  onEdit,
  onDelete,
}: SortableGoalCardProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: goal.id,
  });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 10 : "auto",
  };

  return (
    <Card ref={setNodeRef} style={style}>
      <CardContent>
        <Stack direction="row" alignItems="center" spacing={1}>
          {/* ドラッグハンドル */}
          <IconButton
            size="small"
            sx={{ cursor: "grab", touchAction: "none", color: "text.secondary" }}
            aria-label="並び替え"
            {...attributes}
            {...listeners}
          >
            <DragIndicatorIcon fontSize="small" />
          </IconButton>

          <Stack
            direction="row"
            justifyContent="space-between"
            alignItems="center"
            sx={{ flex: 1, cursor: "pointer", "&:hover": { bgcolor: "action.hover" }, p: 0.5, borderRadius: 1 }}
            onClick={onToggleExpand}
          >
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle1" fontWeight="bold">
                {goal.name}
              </Typography>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 0.5 }}>
                <Typography variant="body2" color="text.secondary">
                  目標 ¥{Number(goal.target_value_jpy).toLocaleString()} / {targetDate}
                </Typography>
                <Chip label={scopeLabel} size="small" variant="outlined" />
              </Stack>
            </Box>
            <Stack direction="row" spacing={0.5}>
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit();
                }}
              >
                <EditIcon fontSize="small" />
              </IconButton>
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete();
                }}
              >
                <DeleteIcon fontSize="small" />
              </IconButton>
            </Stack>
          </Stack>
        </Stack>
        {isExpanded && <GoalDetailSection goal={goal} />}
      </CardContent>
    </Card>
  );
}

export default function GoalsTab() {
  const { data: goals = [], isLoading } = useGoals();
  const { data: members = [] } = useFamilyMembers();
  const deleteMut = useDeleteGoal();
  const reorderMut = useReorderGoals();
  const [editingGoal, setEditingGoal] = useState<FinancialGoal | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  // ローカル順序（楽観的更新用）
  const [localOrder, setLocalOrder] = useState<FinancialGoal[]>([]);
  useEffect(() => {
    setLocalOrder(goals);
  }, [goals]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const handleNew = () => {
    setEditingGoal(null);
    setDialogOpen(true);
  };
  const handleEdit = (goal: FinancialGoal) => {
    setEditingGoal(goal);
    setDialogOpen(true);
  };
  const handleDelete = async (goal: FinancialGoal) => {
    if (!confirm(`目標「${goal.name}」を削除しますか？`)) return;
    await deleteMut.mutateAsync(goal.id);
    if (expandedId === goal.id) setExpandedId(null);
  };

  const handleDragStart = () => {
    // ドラッグ中は展開を畳む（カードサイズが変わって移動が乱れるのを防ぐ）
    setExpandedId(null);
  };

  const handleDragEnd = (e: DragEndEvent) => {
    const { active, over } = e;
    if (!over || active.id === over.id) return;
    const oldIdx = localOrder.findIndex((g) => g.id === active.id);
    const newIdx = localOrder.findIndex((g) => g.id === over.id);
    if (oldIdx < 0 || newIdx < 0) return;
    const newOrder = arrayMove(localOrder, oldIdx, newIdx);
    setLocalOrder(newOrder);
    reorderMut.mutate(newOrder.map((g) => g.id));
  };

  const memberNameMap = Object.fromEntries(members.map((m) => [m.id, m.name]));

  if (isLoading) return <LoadingSpinner />;

  return (
    <Stack spacing={2}>
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Typography variant="h6">目標管理</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={handleNew}>
          新規目標
        </Button>
      </Stack>

      {localOrder.length === 0 && (
        <Card>
          <CardContent>
            <Typography color="text.secondary">
              まだ目標が登録されていません。「新規目標」から登録してください。
            </Typography>
          </CardContent>
        </Card>
      )}

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        modifiers={[restrictToVerticalAxis]}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <SortableContext items={localOrder.map((g) => g.id)} strategy={verticalListSortingStrategy}>
          <Stack spacing={2}>
            {localOrder.map((g) => {
              const isExpanded = expandedId === g.id;
              const targetDate = g.target_date.slice(0, 7).replace("-", "年") + "月";
              const scopeLabel =
                g.scope_type === "family"
                  ? "家族合計"
                  : g.member_ids.map((id) => memberNameMap[id] ?? `#${id}`).join(", ");
              return (
                <SortableGoalCard
                  key={g.id}
                  goal={g}
                  isExpanded={isExpanded}
                  scopeLabel={scopeLabel}
                  targetDate={targetDate}
                  onToggleExpand={() => setExpandedId(isExpanded ? null : g.id)}
                  onEdit={() => handleEdit(g)}
                  onDelete={() => handleDelete(g)}
                />
              );
            })}
          </Stack>
        </SortableContext>
      </DndContext>

      <GoalEditDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        goal={editingGoal}
      />
    </Stack>
  );
}
