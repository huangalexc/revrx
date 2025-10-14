import { create } from 'zustand';

interface Encounter {
  id: string;
  userId: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETE' | 'FAILED';
  processingTime?: number;
  createdAt: string;
  updatedAt: string;
  patientAge?: number;
  patientSex?: string;
  visitDate?: string;
  errorMessage?: string;
}

interface EncounterState {
  encounters: Encounter[];
  currentEncounter: Encounter | null;
  isLoading: boolean;
  setEncounters: (encounters: Encounter[]) => void;
  setCurrentEncounter: (encounter: Encounter | null) => void;
  setLoading: (isLoading: boolean) => void;
  addEncounter: (encounter: Encounter) => void;
  updateEncounter: (id: string, updates: Partial<Encounter>) => void;
}

export const useEncounterStore = create<EncounterState>((set) => ({
  encounters: [],
  currentEncounter: null,
  isLoading: false,
  setEncounters: (encounters) => set({ encounters }),
  setCurrentEncounter: (encounter) => set({ currentEncounter: encounter }),
  setLoading: (isLoading) => set({ isLoading }),
  addEncounter: (encounter) =>
    set((state) => ({ encounters: [encounter, ...state.encounters] })),
  updateEncounter: (id, updates) =>
    set((state) => ({
      encounters: state.encounters.map((e) =>
        e.id === id ? { ...e, ...updates } : e
      ),
    })),
}));
