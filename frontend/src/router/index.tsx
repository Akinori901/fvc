import { createBrowserRouter } from "react-router-dom";
import { ROUTES } from "./routes";
import AppLayout from "@/components/layout/AppLayout";
import ProtectedRoute from "@/components/common/ProtectedRoute";
import LoginPage from "@/pages/LoginPage";
import AuthCallbackPage from "@/pages/AuthCallbackPage";
import DashboardPage from "@/pages/DashboardPage";
import StockListPage from "@/pages/StockListPage";
import StockDetailPage from "@/pages/StockDetailPage";
import EtfListPage from "@/pages/EtfListPage";
import EtfDetailPage from "@/pages/EtfDetailPage";
import ReitListPage from "@/pages/ReitListPage";
import ReitDetailPage from "@/pages/ReitDetailPage";
import CalculatePage from "@/pages/CalculatePage";
import ValuationListPage from "@/pages/ValuationListPage";
import ValuationDetailPage from "@/pages/ValuationDetailPage";
import WatchlistPage from "@/pages/WatchlistPage";
import PortfolioPage from "@/pages/PortfolioPage";
import AccountInputPage from "@/pages/portfolio/AccountInputPage";
import PaperTradingPage from "@/pages/PaperTradingPage";
import FxAnalysisPage from "@/pages/FxAnalysisPage";
import NewsPage from "@/pages/NewsPage";
import WikiPage from "@/pages/WikiPage";
import ChatPage from "@/pages/ChatPage";
import ShareDashboardPage from "@/pages/portfolio/ShareDashboardPage";
import SettingsPage from "@/pages/SettingsPage";
import AdminUsersPage from "@/pages/AdminUsersPage";

const router = createBrowserRouter([
  {
    path: ROUTES.LOGIN,
    element: <LoginPage />,
  },
  {
    // Cognito Hosted UI からのリダイレクト戻り先。ProtectedRoute の外に置く
    // (この時点では isAuthenticated=false なので、ProtectedRoute 内に置くと
    // 即 /login にリダイレクトされてしまう)。
    path: ROUTES.AUTH_CALLBACK,
    element: <AuthCallbackPage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      // AppLayout外（ヘッダー・サイドバーなし）
      { path: ROUTES.PORTFOLIO_SHARE, element: <ShareDashboardPage /> },
      {
        element: <AppLayout />,
        children: [
          { path: ROUTES.DASHBOARD, element: <DashboardPage /> },
          { path: ROUTES.STOCKS, element: <StockListPage /> },
          { path: ROUTES.STOCK_DETAIL, element: <StockDetailPage /> },
          { path: ROUTES.ETF, element: <EtfListPage /> },
          { path: ROUTES.ETF_DETAIL, element: <EtfDetailPage /> },
          { path: ROUTES.REIT, element: <ReitListPage /> },
          { path: ROUTES.REIT_DETAIL, element: <ReitDetailPage /> },
          { path: ROUTES.CALCULATE, element: <CalculatePage /> },
          { path: ROUTES.VALUATIONS, element: <ValuationListPage /> },
          { path: ROUTES.VALUATION_DETAIL, element: <ValuationDetailPage /> },
          { path: ROUTES.WATCHLIST, element: <WatchlistPage /> },
          { path: ROUTES.PORTFOLIO, element: <PortfolioPage /> },
          { path: ROUTES.PORTFOLIO_ACCOUNT_INPUT, element: <AccountInputPage /> },
          { path: ROUTES.PAPER_TRADING, element: <PaperTradingPage /> },
          { path: ROUTES.FX, element: <FxAnalysisPage /> },
          { path: ROUTES.NEWS, element: <NewsPage /> },
          { path: ROUTES.WIKI, element: <WikiPage /> },
          { path: ROUTES.CHAT, element: <ChatPage /> },
          { path: ROUTES.SETTINGS, element: <SettingsPage /> },
          { path: ROUTES.ADMIN_USERS, element: <AdminUsersPage /> },
        ],
      },
    ],
  },
]);

export default router;
