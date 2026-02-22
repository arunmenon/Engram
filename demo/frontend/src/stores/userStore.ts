import { create } from 'zustand';
import { apiGet } from '../api/client';
import { isLiveMode } from '../api/mode';
import {
  sarahProfile,
  sarahPreferences,
  sarahSkills,
  sarahInterests,
  sarahEnhancedPatterns,
  type UserProfile,
  type UserPreference,
  type UserSkill,
  type UserInterest,
} from '../data/mockUserProfile';
import type { EnhancedPattern } from '../types/behavioral';

interface UserState {
  profile: UserProfile | null;
  preferences: UserPreference[];
  skills: UserSkill[];
  interests: UserInterest[];
  patterns: EnhancedPattern[];
  loading: boolean;
  error: string | null;
  fetchUserData: (userId?: string) => Promise<void>;
}

export const useUserStore = create<UserState>((set) => ({
  profile: isLiveMode() ? null : sarahProfile,
  preferences: isLiveMode() ? [] : sarahPreferences,
  skills: isLiveMode() ? [] : sarahSkills,
  interests: isLiveMode() ? [] : sarahInterests,
  patterns: isLiveMode() ? [] : sarahEnhancedPatterns,
  loading: false,
  error: null,

  fetchUserData: async (userId = 'profile-sarah') => {
    if (!isLiveMode()) return;
    set({ loading: true, error: null });
    try {
      const [profile, preferences, skills, interests] = await Promise.all([
        apiGet<UserProfile>(`/v1/users/${userId}/profile`),
        apiGet<UserPreference[]>(`/v1/users/${userId}/preferences`),
        apiGet<UserSkill[]>(`/v1/users/${userId}/skills`),
        apiGet<UserInterest[]>(`/v1/users/${userId}/interests`),
      ]);
      set({ profile, preferences, skills, interests, loading: false });
    } catch (e) {
      set({
        error: e instanceof Error ? e.message : 'Failed to fetch user data',
        loading: false,
      });
    }
  },
}));
