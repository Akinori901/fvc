import { useState } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Stack,
} from "@mui/material";

interface Props {
  open: boolean;
  onClose: () => void;
  onSave: (name: string, priority: number) => void;
  defaultName?: string;
  defaultPriority?: number;
}

export default function PresetSaveDialog({ open, onClose, onSave, defaultName = "", defaultPriority = 0 }: Props) {
  const [name, setName] = useState(defaultName);
  const [priority, setPriority] = useState(defaultPriority);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>プリセット保存</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          <TextField
            label="プリセット名"
            value={name}
            onChange={(e) => setName(e.target.value)}
            size="small"
            fullWidth
            required
          />
          <TextField
            label="優先度（小さいほど優先）"
            type="number"
            value={priority}
            onChange={(e) => setPriority(parseInt(e.target.value, 10) || 0)}
            size="small"
            fullWidth
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>キャンセル</Button>
        <Button
          variant="contained"
          disabled={!name.trim()}
          onClick={() => { onSave(name.trim(), priority); onClose(); }}
        >
          保存
        </Button>
      </DialogActions>
    </Dialog>
  );
}
