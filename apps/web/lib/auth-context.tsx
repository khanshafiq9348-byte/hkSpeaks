"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { apiClient } from "./api";

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: string;
  avatar_url?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  loginAsDemo: (role?: "creator" | "admin") => Promise<User | void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  isLoading: true,
  login: () => {},
  logout: () => {},
  loginAsDemo: async () => {},
  refreshUser: async () => {},
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = async () => {
    try {
      const u = await apiClient<User>("/auth/me");
      setUser(u);
    } catch {
      setUser(null);
      localStorage.removeItem("hk_token");
      setToken(null);
      // Auto-reconnect session as creator
      await loginAsDemo("creator");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const savedToken = localStorage.getItem("hk_token");
    if (savedToken) {
      setToken(savedToken);
      refreshUser();
    } else {
      // Auto-initialize authenticated session for creator
      loginAsDemo("creator");
    }
  }, []);

  const login = (newToken: string, newUser: User) => {
    localStorage.setItem("hk_token", newToken);
    setToken(newToken);
    setUser(newUser);
  };

  const loginAsDemo = async (role: "creator" | "admin" = "creator") => {
    setIsLoading(true);
    try {
      const creds =
        role === "admin"
          ? { email: "admin@hkspeaks.ai", password: "AdminPass123!" }
          : { email: "creator@hkspeaks.ai", password: "CreatorPass123!" };
      const res = await apiClient<{ access_token: string; user: User }>("/auth/login", {
        method: "POST",
        body: JSON.stringify(creds),
      });
      login(res.access_token, res.user);
      return res.user;
    } catch (e) {
      console.error("Demo login error:", e);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("hk_token");
    setToken(null);
    setUser(null);
    window.location.href = "/login";
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout, loginAsDemo, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
