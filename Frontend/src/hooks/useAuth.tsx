import React, { useState, useEffect, createContext, useContext } from 'react';
import authService, { User } from '../services/authService';

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  isLoading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        // Verificar se há token salvo
        if (authService.isAuthenticated()) {
          const result = await authService.verify();
          if (result.success && result.user) {
            setUser(result.user);
            setToken(authService.getToken());
          } else {
            // Token inválido, limpar dados
            await authService.logout();
          }
        }
      } catch (error) {
        console.error('[AUTH] Erro ao inicializar autenticação:', error);
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = async (username: string, password: string) => {
    try {
      setIsLoading(true);
      setError(null);
      
      console.log('[LOGIN] Tentando login:', { username });
      const response = await authService.login(username, password);
      console.log('[LOGIN] Resposta do login:', response);
      
      if (response.success && response.data) {
        const { user, token } = response.data;
        console.log('[LOGIN] Definindo estado do usuário:', { user, token });
        setUser(user);
        setToken(token);
        console.log('[LOGIN] Estado definido, aguardando atualização...');
      } else {
        const errorMessage = response.message || 'Credenciais inválidas';
        setError(errorMessage);
        throw new Error(errorMessage);
      }
    } catch (error: any) {
      console.error('[LOGIN] Erro ao fazer login:', error);
      const errorMessage = error.message || 'Erro ao fazer login';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await authService.logout();
      setUser(null);
      setToken(null);
      setError(null);
    } catch (error) {
      console.error('[LOGOUT] Erro ao fazer logout:', error);
    }
  };

  const value: AuthContextType = {
    user,
    token,
    login,
    logout,
    isLoading,
    error,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin' || false,
  };

  // Debug logs
  console.log('[AUTH CONTEXT] Estado atual:', {
    user: !!user,
    token: !!token,
    isLoading,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin' || false,
  });

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}; 