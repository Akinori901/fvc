import { useState } from "react";
import {
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  Stack,
  Divider,
  ListItemText,
  ListItemIcon,
} from "@mui/material";
import SaveIcon from "@mui/icons-material/Save";
import DeleteIcon from "@mui/icons-material/Delete";
import type { ScreeningPreset, ScreeningFilters } from "@/types/screeningPreset";
import PresetSaveDialog from "./PresetSaveDialog";

interface Props {
  presets: ScreeningPreset[];
  selectedPresetId: number | null;
  onSelect: (presetId: number | null, filters: ScreeningFilters | null) => void;
  onSave: (name: string, priority: number) => void;
  onDelete: (id: number) => void;
}

export default function PresetSelector({ presets, selectedPresetId, onSelect, onSave, onDelete }: Props) {
  const [saveOpen, setSaveOpen] = useState(false);

  return (
    <>
      <Stack direction="row" alignItems="center" spacing={0.5}>
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel>プリセット</InputLabel>
          <Select
            value={selectedPresetId ?? "default"}
            label="プリセット"
            onChange={(e) => {
              const val = e.target.value;
              if (val === "default") {
                onSelect(null, null);
              } else {
                const preset = presets.find((p) => p.id === val);
                if (preset) onSelect(preset.id, preset.filters);
              }
            }}
          >
            <MenuItem value="default">
              <ListItemText primary="デフォルト" />
            </MenuItem>
            {presets.length > 0 && <Divider />}
            {presets.map((p) => (
              <MenuItem key={p.id} value={p.id}>
                <ListItemText primary={p.name} secondary={`優先度: ${p.priority}`} />
                <ListItemIcon sx={{ minWidth: 32 }}>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(p.id);
                    }}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </ListItemIcon>
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <IconButton size="small" onClick={() => setSaveOpen(true)} title="現在の設定を保存">
          <SaveIcon fontSize="small" />
        </IconButton>
      </Stack>
      <PresetSaveDialog open={saveOpen} onClose={() => setSaveOpen(false)} onSave={onSave} />
    </>
  );
}
