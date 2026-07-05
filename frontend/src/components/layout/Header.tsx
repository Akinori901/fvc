import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AppBar,
  Box,
  Divider,
  IconButton,
  Menu,
  MenuItem,
  Toolbar,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import MenuIcon from "@mui/icons-material/Menu";
import { signOut } from "aws-amplify/auth";

import { useAuthStore } from "@/stores/authStore";
import { DRAWER_WIDTH } from "./Sidebar";

interface HeaderProps {
  onMenuClick: () => void;
}

export default function Header({ onMenuClick }: HeaderProps) {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const theme = useTheme();
  const isDesktop = useMediaQuery(theme.breakpoints.up("md"));

  const handleLogout = async () => {
    setAnchorEl(null);
    // Cognito signOut。Hosted UI の logout URL にリダイレクトされ、その後
    // logout_urls で設定した /login に戻る。Hub.signedOut event 経由で
    // authStore もクリアされる。signOut 失敗時はフォールバックで /login へ
    // 遷移 + zustand クリア。
    try {
      await signOut();
    } catch {
      logout();
      navigate("/login");
    }
  };

  return (
    <AppBar
      position="fixed"
      color="default"
      elevation={1}
      sx={{
        width: isDesktop ? `calc(100% - ${DRAWER_WIDTH}px)` : "100%",
        ml: isDesktop ? `${DRAWER_WIDTH}px` : 0,
      }}
    >
      <Toolbar>
        {!isDesktop && (
          <IconButton
            edge="start"
            color="inherit"
            aria-label="メニューを開く"
            onClick={onMenuClick}
            sx={{ mr: 1 }}
          >
            <MenuIcon />
          </IconButton>
        )}
        <Box sx={{ flexGrow: 1 }} />
        <Typography variant="body2" sx={{ mr: 1 }}>
          {user?.username}
          {user?.is_superuser && "(管理者)"}
        </Typography>
        <IconButton onClick={(e) => setAnchorEl(e.currentTarget)}>
          <AccountCircleIcon />
        </IconButton>
        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={() => setAnchorEl(null)}
        >
          <MenuItem onClick={() => { setAnchorEl(null); navigate("/settings"); }}>
            パスワード変更
          </MenuItem>
          <Divider />
          <MenuItem onClick={handleLogout}>ログアウト</MenuItem>
        </Menu>
      </Toolbar>
    </AppBar>
  );
}
