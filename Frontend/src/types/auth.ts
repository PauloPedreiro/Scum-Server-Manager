export interface LoginRequest {
  username: string;
  password: string;
}

export interface User {
  id: string;
  username: string;
  steamId: string | null;
  role: string;
  permissions: string[];
  profile: {
    firstName: string;
    lastName: string;
    avatar: string | null;
    timezone: string;
    language: string;
  };
  isFirstLogin: boolean;
  requiresPasswordChange: boolean;
}

export interface LoginResponse {
  success: boolean;
  message: string;
  data: {
    user: User;
    token: string;
  };
}

export interface AuthError {
  success: false;
  error: string;
}

export interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
  error: string | null;
} 