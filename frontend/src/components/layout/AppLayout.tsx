import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Box, Toolbar, useMediaQuery, useTheme } from "@mui/material";
import Sidebar, { DRAWER_WIDTH } from "./Sidebar";
import Header from "./Header";
import PlanLimitBanner from "@/components/common/PlanLimitBanner";
import ChatWidget from "@/components/chat/ChatWidget";
import { ROUTES } from "@/router/routes";

export default function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up("md"));
  const location = useLocation();
  // 全画面チャットページではフローティングウィジェットを重ねない
  const showWidget = location.pathname !== ROUTES.CHAT;

  return (
    <Box sx={{ display: "flex" }}>
      <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      <Header onMenuClick={() => setMobileOpen(true)} />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: { xs: 1.5, md: 3 },
          width: isDesktop ? `calc(100% - ${DRAWER_WIDTH}px)` : "100%",
          minHeight: "100vh",
          bgcolor: "background.default",
        }}
      >
        <Toolbar />
        <PlanLimitBanner />
        <Outlet />
      </Box>
      {showWidget && <ChatWidget />}
    </Box>
  );
}
