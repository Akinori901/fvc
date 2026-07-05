import { useLocation, useNavigate } from "react-router-dom";
import {
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  Box,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import DashboardIcon from "@mui/icons-material/Dashboard";
import ListAltIcon from "@mui/icons-material/ListAlt";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import ApartmentIcon from "@mui/icons-material/Apartment";
import CalculateIcon from "@mui/icons-material/Calculate";
import HistoryIcon from "@mui/icons-material/History";
import StarIcon from "@mui/icons-material/Star";
import AccountBalanceWalletIcon from "@mui/icons-material/AccountBalanceWallet";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import SportsEsportsIcon from "@mui/icons-material/SportsEsports";
import CurrencyExchangeIcon from "@mui/icons-material/CurrencyExchange";
import NewspaperIcon from "@mui/icons-material/Newspaper";
import MenuBookIcon from "@mui/icons-material/MenuBook";
import ChatIcon from "@mui/icons-material/Chat";
import SettingsIcon from "@mui/icons-material/Settings";
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import { ROUTES } from "@/router/routes";
import { useAuthStore } from "@/stores/authStore";

const DRAWER_WIDTH = 240;

const menuItems = [
  { label: "ダッシュボード", icon: <DashboardIcon />, path: ROUTES.DASHBOARD },
  { label: "銘柄一覧", icon: <ListAltIcon />, path: ROUTES.STOCKS },
  { label: "ETF一覧", icon: <TrendingUpIcon />, path: ROUTES.ETF },
  { label: "J-REIT一覧", icon: <ApartmentIcon />, path: ROUTES.REIT },
  { label: "適正株価算出", icon: <CalculateIcon />, path: ROUTES.CALCULATE },
  { label: "算出履歴", icon: <HistoryIcon />, path: ROUTES.VALUATIONS },
  { label: "ウォッチリスト", icon: <StarIcon />, path: ROUTES.WATCHLIST },
  { label: "ポートフォリオ", icon: <AccountBalanceWalletIcon />, path: ROUTES.PORTFOLIO },
  { label: "持ち株登録", icon: <ShowChartIcon />, path: ROUTES.PORTFOLIO_STOCKS },
  { label: "仮想売買", icon: <SportsEsportsIcon />, path: ROUTES.PAPER_TRADING },
  { label: "FX分析", icon: <CurrencyExchangeIcon />, path: ROUTES.FX },
  { label: "ニュース", icon: <NewspaperIcon />, path: ROUTES.NEWS },
  { label: "AIチャット", icon: <ChatIcon />, path: ROUTES.CHAT },
  { label: "用語集", icon: <MenuBookIcon />, path: ROUTES.WIKI },
  { label: "設定", icon: <SettingsIcon />, path: ROUTES.SETTINGS },
];

// superuser のみ表示する admin 系メニュー
const adminMenuItems = [
  { label: "ユーザー管理", icon: <AdminPanelSettingsIcon />, path: ROUTES.ADMIN_USERS },
];

interface SidebarProps {
  mobileOpen: boolean;
  onClose: () => void;
}

export default function Sidebar({ mobileOpen, onClose }: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up("md"));
  const isSuperuser = useAuthStore((s) => s.user?.is_superuser ?? false);

  const handleNavigate = (path: string) => {
    navigate(path);
    if (!isDesktop) onClose();
  };

  const visibleItems = [
    ...menuItems,
    ...(isSuperuser ? adminMenuItems : []),
  ];

  const drawerContent = (
    <>
      <Toolbar>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <CalculateIcon color="primary" />
          <Typography variant="h6" noWrap color="primary" fontWeight="bold">
            FVC
          </Typography>
        </Box>
      </Toolbar>
      <List>
        {visibleItems.map((item) => (
          <ListItemButton
            key={item.path}
            selected={location.pathname + location.search === item.path || (location.pathname === item.path && !item.path.includes("?"))}
            onClick={() => handleNavigate(item.path)}
          >
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
    </>
  );

  if (isDesktop) {
    return (
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: DRAWER_WIDTH,
            boxSizing: "border-box",
          },
        }}
      >
        {drawerContent}
      </Drawer>
    );
  }

  return (
    <Drawer
      variant="temporary"
      open={mobileOpen}
      onClose={onClose}
      ModalProps={{ keepMounted: true }}
      sx={{
        "& .MuiDrawer-paper": {
          width: DRAWER_WIDTH,
          boxSizing: "border-box",
        },
      }}
    >
      {drawerContent}
    </Drawer>
  );
}

export { DRAWER_WIDTH };
