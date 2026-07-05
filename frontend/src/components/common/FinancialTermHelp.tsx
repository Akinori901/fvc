import { type ReactNode, useState } from "react";
import { Box, IconButton, Popover, Typography } from "@mui/material";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import { FINANCIAL_TERMS } from "@/constants/financialTerms";

interface Props {
  termKey: string;
  extra?: ReactNode;
}

export default function FinancialTermHelp({ termKey, extra }: Props) {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const term = FINANCIAL_TERMS[termKey];
  if (!term) return null;

  return (
    <>
      <IconButton
        size="small"
        onClick={(e) => setAnchorEl(e.currentTarget)}
        sx={{ color: "text.secondary", p: 0.25 }}
      >
        <HelpOutlineIcon sx={{ fontSize: 14 }} />
      </IconButton>
      <Popover
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
        transformOrigin={{ vertical: "top", horizontal: "left" }}
      >
        <Box sx={{ p: 2, maxWidth: 340 }}>
          <Typography variant="subtitle2" gutterBottom>
            {term.label}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {term.description}
          </Typography>
          {term.formula && (
            <Typography
              variant="body2"
              sx={{ fontFamily: "monospace", fontSize: "0.8rem", mb: 1, whiteSpace: "pre-line" }}
            >
              {term.formula}
            </Typography>
          )}
          <Typography variant="subtitle2" sx={{ mt: 1, mb: 0.5 }}>
            判断基準
          </Typography>
          <Typography variant="body2" sx={{ whiteSpace: "pre-line" }}>
            {term.interpretation}
          </Typography>
          {extra}
        </Box>
      </Popover>
    </>
  );
}
