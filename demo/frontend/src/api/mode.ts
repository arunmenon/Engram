export type DataMode = 'mock' | 'live';
export type LiveSubMode = 'interactive' | 'simulator' | 'dynamic';

const STORAGE_KEY = 'engram-data-mode';
const SUBMODE_KEY = 'engram-live-submode';

export function getDataMode(): DataMode {
  return (localStorage.getItem(STORAGE_KEY) as DataMode) ?? 'mock';
}

export function setDataMode(mode: DataMode): void {
  localStorage.setItem(STORAGE_KEY, mode);
}

export function isLiveMode(): boolean {
  return getDataMode() === 'live';
}

export function getLiveSubMode(): LiveSubMode {
  return (localStorage.getItem(SUBMODE_KEY) as LiveSubMode) ?? 'simulator';
}

export function setLiveSubMode(mode: LiveSubMode): void {
  localStorage.setItem(SUBMODE_KEY, mode);
}

export function isSimulatorMode(): boolean {
  return getDataMode() === 'live' && getLiveSubMode() === 'simulator';
}

export function isDynamicMode(): boolean {
  return getDataMode() === 'live' && getLiveSubMode() === 'dynamic';
}
