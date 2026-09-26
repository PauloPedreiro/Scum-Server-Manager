import { Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { authService } from '@/services/auth';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

export function ProtectedRoute({ children, requireAdmin = false }: ProtectedRouteProps) {
  const [isValidating, setIsValidating] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [mustLinkDiscord, setMustLinkDiscord] = useState(false);

  // Validar token ao montar componente
  useEffect(() => {
    const validateToken = async () => {
      setIsValidating(true);
      
      // Verificar se token existe e não está expirado
      if (!authService.isAuthenticated()) {
        setIsAuthenticated(false);
        setIsValidating(false);
        return;
      }

      // Validar token com backend
      try {
        const user = await authService.getCurrentUser();
        if (user) {
          setIsAuthenticated(true);
          setMustLinkDiscord(authService.mustLinkDiscordFromUser(user));
        } else {
          setIsAuthenticated(false);
          setMustLinkDiscord(false);
        }
      } catch (error) {
        setIsAuthenticated(false);
        setMustLinkDiscord(false);
      } finally {
        setIsValidating(false);
      }
    };

    validateToken();
  }, []);

  // Mostrar loading durante validação
  if (isValidating) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-scum-orange"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Gate: admin precisa vincular Discord antes de liberar acesso ao app
  if (mustLinkDiscord && window.location.pathname !== '/activate-discord') {
    return <Navigate to="/activate-discord" replace />;
  }

  if (requireAdmin && !authService.isAdmin()) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <>{children}</>;
}

