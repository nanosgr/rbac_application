'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api/client';
import { userService } from '@/lib/api/services';
import { AuthContextType, LoginCredentials, User } from '@/types';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // Load user on mount
  useEffect(() => {
    const loadUser = async () => {
      const savedToken = apiClient.getToken();
      if (savedToken) {
        try {
          const userData = await userService.getMe();
          setUser(userData);
          setTokenState(savedToken);
        } catch (error) {
          console.error('Failed to load user:', error);
          apiClient.setToken(null);
        }
      }
      setIsLoading(false);
    };

    loadUser();
  }, []);

  const login = useCallback(async (credentials: LoginCredentials) => {
    try {
      const response = await apiClient.login(credentials.username, credentials.password);
      apiClient.setToken(response.access_token);
      setTokenState(response.access_token);

      const userData = await userService.getMe();
      setUser(userData);

      router.push('/dashboard');
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  }, [router]);

  const logout = useCallback(() => {
    apiClient.setToken(null);
    setUser(null);
    setTokenState(null);
    router.push('/login');
  }, [router]);

  const hasPermission = useCallback((permission: string): boolean => {
    if (!user) return false;
    if (user.is_superuser) return true;

    const [resource, action] = permission.split(':');

    for (const role of user.roles) {
      if (!role.is_active) continue;

      for (const perm of role.permissions) {
        if (perm.is_active && perm.resource === resource && perm.action === action) {
          return true;
        }
      }
    }

    return false;
  }, [user]);

  const hasAnyPermission = useCallback((permissions: string[]): boolean => {
    return permissions.some(permission => hasPermission(permission));
  }, [hasPermission]);

  const hasAllPermissions = useCallback((permissions: string[]): boolean => {
    return permissions.every(permission => hasPermission(permission));
  }, [hasPermission]);

  const value: AuthContextType = {
    user,
    setUser,
    token,
    login,
    logout,
    isAuthenticated: !!user,
    isLoading,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
