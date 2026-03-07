import { create } from 'zustand';
import { apiGet } from '../api/client';
import { isLiveMode, isSimulatorMode } from '../api/mode';
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
  setProfile: (profile: UserProfile | null) => void;
  setPreferences: (prefs: UserPreference[]) => void;
  setSkills: (skills: UserSkill[]) => void;
  setInterests: (interests: UserInterest[]) => void;
  setPatterns: (patterns: EnhancedPattern[]) => void;
  fetchUserData: (userId?: string) => Promise<void>;
}

export const useUserStore = create<UserState>((set) => ({
  profile: (isLiveMode() || isSimulatorMode()) ? null : sarahProfile,
  preferences: (isLiveMode() || isSimulatorMode()) ? [] : sarahPreferences,
  skills: (isLiveMode() || isSimulatorMode()) ? [] : sarahSkills,
  interests: (isLiveMode() || isSimulatorMode()) ? [] : sarahInterests,
  patterns: (isLiveMode() || isSimulatorMode()) ? [] : sarahEnhancedPatterns,
  loading: false,
  error: null,

  setProfile: (profile) => set({ profile }),
  setPreferences: (preferences) => set({ preferences }),
  setSkills: (skills) => set({ skills }),
  setInterests: (interests) => set({ interests }),
  setPatterns: (patterns) => set({ patterns }),

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
