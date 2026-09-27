import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import type { AuthResponse, LearnerProfileResponse, UserProfileResponse } from '../types';
import { api } from '../services';

interface AuthContextType {
  userId: string | null;
  profile: LearnerProfileResponse | null;
  userProfile: UserProfileResponse | null;
  profileComplete: boolean;
  mindProfileComplete: boolean;
  isLoading: boolean;
  login: (auth: AuthResponse) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
  refreshUserProfile: () => Promise<void>;
  refreshAuthStatus: () => Promise<AuthResponse | null>;
}

const AuthContext = createContext<AuthContextType | null>(null);

const STORAGE_KEY = 'clario_user_id';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [userId, setUserId] = useState<string | null>(null);
  const [profile, setProfile] = useState<LearnerProfileResponse | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfileResponse | null>(null);
  const [profileComplete, setProfileComplete] = useState(false);
  const [mindProfileComplete, setMindProfileComplete] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      setIsLoading(false);
      return;
    }
    void api.getAuthStatus(stored).then(auth => {
      setUserId(auth.user_id);
      setProfileComplete(auth.profile_complete);
      setMindProfileComplete(auth.mind_profile_complete);
    }).catch(() => {
      localStorage.removeItem(STORAGE_KEY);
    }).finally(() => setIsLoading(false));
  }, []);

  const login = async (auth: AuthResponse) => {
    localStorage.setItem(STORAGE_KEY, auth.user_id);
    setUserId(auth.user_id);
    setProfileComplete(auth.profile_complete);
    setMindProfileComplete(auth.mind_profile_complete);
    await refreshProfile(auth.user_id);
    if (auth.profile_complete) {
      await refreshUserProfile(auth.user_id);
    }
  };

  const logout = () => {
    localStorage.removeItem(STORAGE_KEY);
    setUserId(null);
    setProfile(null);
    setUserProfile(null);
    setProfileComplete(false);
    setMindProfileComplete(false);
  };

  const refreshAuthStatus = async (): Promise<AuthResponse | null> => {
    if (!userId) return null;
    const auth = await api.getAuthStatus(userId);
    setProfileComplete(auth.profile_complete);
    setMindProfileComplete(auth.mind_profile_complete);
    return auth;
  };

  const refreshProfile = async (id = userId) => {
    if (!id) return;
    try {
      const profileData = await api.getLearnerProfile(id);
      setProfile(profileData);
    } catch {
      setProfile(null);
    }
  };

  const refreshUserProfile = async (id = userId) => {
    if (!id) return;
    try {
      setUserProfile(await api.getUserProfile(id));
    } catch {
      setUserProfile(null);
    }
  };

  return React.createElement(
    AuthContext.Provider,
    { value: {
      userId, profile, userProfile, profileComplete, mindProfileComplete, isLoading,
      login, logout, refreshProfile, refreshUserProfile, refreshAuthStatus,
    } },
    children
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}