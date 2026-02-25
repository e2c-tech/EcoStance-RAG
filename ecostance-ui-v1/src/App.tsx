import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import SidebarLayout from './components/SidebarLayout';
import SuperAdminLayout from './components/SuperAdminLayout';
import DashboardPage from './pages/DashboardPage';
import KnowledgeBaseListPage from './pages/KnowledgeBaseListPage';
import KnowledgeBaseDetailsPage from './pages/KnowledgeBaseDetailsPage';
import InternalChatPage from './pages/InternalChatPage';
import PublicChatPage from './pages/PublicChatPage';
import PublicAgentPage from './pages/PublicAgentPage';
import AdminPublicChatPage from './pages/AdminPublicChatPage';
import AdminPublicAgentPage from './pages/AdminPublicAgentPage';
import DatabaseChatPage from './pages/DatabaseChatPage';
import AIAgentPage from './pages/AIAgentPage';
import TenantSettingsPage from './pages/TenantSettingsPage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import KBDiagnosticPage from './pages/KBDiagnosticPage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import SuperAdminLoginPage from './pages/admin/SuperAdminLoginPage';
import SuperAdminDashboard from './pages/admin/SuperAdminDashboard';
import TenantManagementPage from './pages/admin/TenantManagementPage';
import TenantDetailsPage from './pages/admin/TenantDetailsPage';
import SystemHealthPage from './pages/admin/SystemHealthPage';
import AnalyticsPage from './pages/admin/AnalyticsPage';
import QuotaManagementPage from './pages/admin/QuotaManagementPage';
import AuditLogsPage from './pages/admin/AuditLogsPage';
import MaintenancePage from './pages/admin/MaintenancePage';
import PlatformSettingsPage from './pages/admin/PlatformSettingsPage';
import GmailCallbackPage from './pages/GmailCallbackPage';
import UserManagementPage from './pages/UserManagementPage';
import SetPasswordPage from './pages/SetPasswordPage';
import PaymentSuccessPage from './pages/billing/PaymentSuccessPage';
import PaymentCancelPage from './pages/billing/PaymentCancelPage';
import { AuthProvider, useAuth } from './context/AuthContext.v2';
import { KnowledgeBaseProvider } from './context/KnowledgeBaseContext';
import { DatabaseProvider } from './context/DatabaseContext';
import { TenantProvider } from './context/TenantContext';
import { RBACProvider } from './context/RBACContext';
import { IntegrationProvider } from './context/IntegrationContext';
import { JobProvider } from './context/JobContext';
import { Icons } from './components/icons';

// ProtectedRoute component to ensure only authenticated users can access certain routes
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, isAuthLoading } = useAuth();

  if (isAuthLoading) {
    // Optionally, render a loading spinner here
    return <div className="flex justify-center items-center h-screen w-full"><Icons.Spinner className="h-10 w-10 animate-spin text-primary" /></div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

// SuperAdminRoute component for super admin only pages
// This doesn't use AuthContext - it checks localStorage directly
const SuperAdminRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, isAuthLoading } = useAuth();

  if (isAuthLoading) {
    return <div className="flex justify-center items-center h-screen w-full"><Icons.Spinner className="h-10 w-10 animate-spin text-primary" /></div>;
  }

  // Check if user is super admin
  const isSuperAdmin =
    user?.role === 'super_admin' ||
    user?.role === 'admin' ||
    user?.tenantId === 'platform-admin-tenant-id';

  if (!user || !isSuperAdmin) {
    return <Navigate to="/admin/login" replace />;
  }

  return <>{children}</>;
};

function App() {
  return (
    <AuthProvider>
      <TenantProvider>
        <DatabaseProvider>
          <RBACProvider>
            <IntegrationProvider>
              <KnowledgeBaseProvider>
                <JobProvider>
                  <Router basename="/ecostance-ui">
                    <Routes>
                      {/* Public Routes */}
                      <Route path="/login" element={<LoginPage />} />
                      <Route path="/register" element={<SignupPage />} />
                      <Route path="/public-chat" element={<PublicChatPage />} />
                      <Route path="/public-agent" element={<PublicAgentPage />} />
                      <Route path="/auth/set-password" element={<SetPasswordPage />} />

                      {/* Super Admin Routes */}
                      <Route path="/admin/login" element={<SuperAdminLoginPage />} />
                      <Route
                        path="/admin"
                        element={
                          <SuperAdminRoute>
                            <SuperAdminLayout />
                          </SuperAdminRoute>
                        }
                      >
                        <Route path="dashboard" element={<SuperAdminDashboard />} />
                        <Route path="tenants" element={<TenantManagementPage />} />
                        <Route path="tenants/:tenantId" element={<TenantDetailsPage />} />
                        <Route path="analytics" element={<AnalyticsPage />} />
                        <Route path="quotas" element={<QuotaManagementPage />} />
                        <Route path="system" element={<SystemHealthPage />} />
                        <Route path="maintenance" element={<MaintenancePage />} />
                        <Route path="audit-logs" element={<AuditLogsPage />} />
                        <Route path="settings" element={<PlatformSettingsPage />} />
                      </Route>

                      {/* Protected Routes with Sidebar */}
                      <Route
                        path="/"
                        element={
                          <ProtectedRoute>
                            <SidebarLayout />
                          </ProtectedRoute>
                        }
                      >
                        <Route index element={<DashboardPage />} />
                        <Route path="knowledge-base" element={<KnowledgeBaseListPage />} />
                        <Route path="knowledge-base/:kbId" element={<KnowledgeBaseDetailsPage />} />
                        <Route path="kb-diagnostic" element={<KBDiagnosticPage />} />
                        <Route path="chat" element={<InternalChatPage />} />
                        <Route path="database-chat" element={<DatabaseChatPage />} />
                        <Route path="ai-agent" element={<AIAgentPage />} />
                        <Route path="users" element={<UserManagementPage />} />
                        <Route path="settings" element={<TenantSettingsPage />} />
                        <Route path="admin/public-chat" element={<AdminPublicChatPage />} />
                        <Route path="admin/public-agent" element={<AdminPublicAgentPage />} />
                        <Route path="gmail/callback" element={<GmailCallbackPage />} />
                        <Route path="billing/success" element={<PaymentSuccessPage />} />
                        <Route path="billing/cancel" element={<PaymentCancelPage />} />
                        <Route
                          path="admin/dashboard"
                          element={
                            <SuperAdminRoute>
                              <AdminDashboardPage />
                            </SuperAdminRoute>
                          }
                        />
                      </Route>

                      {/* Fallback Route */}
                      <Route path="*" element={<AuthRedirector />} />
                    </Routes>
                  </Router>
                </JobProvider>
              </KnowledgeBaseProvider>
            </IntegrationProvider>
          </RBACProvider>
        </DatabaseProvider>
      </TenantProvider>
    </AuthProvider>
  );
}

// Helper component to handle redirection based on authentication status for the catch-all route
const AuthRedirector = () => {
  const { isAuthenticated, isAuthLoading } = useAuth();

  if (isAuthLoading) {
    return null; // Or a loading spinner
  }

  return isAuthenticated ? <Navigate to="/" replace /> : <Navigate to="/login" replace />;
};

export default App;
