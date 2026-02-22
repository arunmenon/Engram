export type DataMode = 'mock' | 'live';

const STORAGE_KEY = 'engram-data-mode';

export function getDataMode(): DataMode {
  return (localStorage.getItem(STORAGE_KEY) as DataMode) ?? 'mock';
}

export function setDataMode(mode: DataMode): void {
  localStorage.setItem(STORAGE_KEY, mode);
}

export function isLiveMode(): boolean {
  return getDataMode() === 'live';
}
