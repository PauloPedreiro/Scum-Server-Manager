import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requireAdmin = false }) => {
  const { user, token, isAuthenticated, isAdmin, isLoading } = useAuth();
  const location = useLocation();

  console.log('[PROTECTED ROUTE] Estado:', {
    isAuthenticated,
    isAdmin,
    isLoading,
    pathname: location.pathname,
    requireAdmin
  });

  // Mostrar loading enquanto verifica autenticação
  if (isLoading) {
    console.log('[PROTECTED ROUTE] Mostrando loading...');
    return (
      <div className="min-h-screen flex items-center justify-center bg-scum-dark">
        <div className="text-scum-light text-center">
          <div className="w-8 h-8 border-2 border-scum-accent border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-sm">Verificando autenticação...</p>
        </div>
      </div>
    );
  }

  // Se não está autenticado, redirecionar para login
  if (!isAuthenticated) {
    console.log('[PROTECTED ROUTE] ❌ NÃO AUTENTICADO - Redirecionando para login');
    console.log('[PROTECTED ROUTE] Debug:', {
      user: !!user,
      token: !!token,
      isAuthenticated,
      isLoading,
      pathname: location.pathname
    });
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Se requer admin mas usuário não é admin, redirecionar para dashboard
  if (requireAdmin && !isAdmin) {
    console.log('[PROTECTED ROUTE] Não é admin, redirecionando para dashboard');
    return <Navigate to="/dashboard" replace />;
  }

  console.log('[PROTECTED ROUTE] Acesso permitido');
  return <>{children}</>;
};

export default ProtectedRoute; 