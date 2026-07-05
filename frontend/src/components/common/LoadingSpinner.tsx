import { Box, CircularProgress } from "@mui/material";

export default function LoadingSpinner() {
  return (
    <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
      <CircularProgress />
    </Box>
  );
}
