import { create } from 'zustand';

interface AnnounceState {
  message: string;
  announce: (message: string) => void;
}

export const useAnnounceStore = create<AnnounceState>((set) => ({
  message: '',
  announce: (message) => {
    set({ message: '' });
    setTimeout(() => set({ message }), 50);
  },
}));
