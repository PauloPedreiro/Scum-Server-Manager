import React from 'react';
import { useAuth } from '../hooks/useAuth';

const AuthDebug: React.FC = () => {
  const { user, token, isAuthenticated, isAdmin, isLoading } = useAuth();

  return (
    <div style={{
      position: 'fixed',
      top: '10px',
      right: '10px',
      background: 'rgba(0,0,0,0.8)',
      color: 'white',
      padding: '10px',
      borderRadius: '5px',
      fontSize: '12px',
      zIndex: 9999,
      fontFamily: 'monospace'
    }}>
      <div><strong>Auth Debug:</strong></div>
      <div>User: {user ? '✅' : '❌'}</div>
      <div>Token: {token ? '✅' : '❌'}</div>
      <div>isAuthenticated: {isAuthenticated ? '✅' : '❌'}</div>
      <div>isAdmin: {isAdmin ? '✅' : '❌'}</div>
      <div>isLoading: {isLoading ? '⏳' : '✅'}</div>
      <div>User ID: {user?.id || 'N/A'}</div>
      <div>Username: {user?.username || 'N/A'}</div>
      <div>Role: {user?.role || 'N/A'}</div>
    </div>
  );
};

export default AuthDebug; 