import { useEffect, useState } from 'react';

// UI-hide toggles are stored per user in localStorage so the pages stay
// reachable by direct link (backend kept) while the user's choice controls
// whether they appear in the shell / home pages.
export type UiHideSettings = {
  hide_research_mode: boolean;
  hide_clinical_warning: boolean;
  hide_clinic_link: boolean;
};

const STORAGE_KEY = 'rehabai-ui-hide-settings';
const EVENT_NAME = 'rehabai-ui-hide-changed';
const DEFAULTS: UiHideSettings = { hide_research_mode: false, hide_clinical_warning: false, hide_clinic_link: false };

function read(): UiHideSettings {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULTS;
    const parsed = JSON.parse(raw);
    return { ...DEFAULTS, ...parsed };
  } catch {
    return DEFAULTS;
  }
}

/** Reactive per-user UI-hide settings; re-reads on custom/storage events so
 *  the sidebar, Home and Practice update when the user toggles them in Settings. */
export function useUiHideSettings(): UiHideSettings {
  const [value, setValue] = useState<UiHideSettings>(read);
  useEffect(() => {
    const refresh = () => setValue(read());
    const onStorage = (event: StorageEvent) => { if (event.key === STORAGE_KEY || event.key === null) refresh(); };
    window.addEventListener('storage', onStorage);
    window.addEventListener(EVENT_NAME, refresh);
    return () => {
      window.removeEventListener('storage', onStorage);
      window.removeEventListener(EVENT_NAME, refresh);
    };
  }, []);
  return value;
}

/** Write from the Settings page; notifies same-tab listeners. */
export function saveUiHideSettings(next: Partial<UiHideSettings>): void {
  const merged = { ...read(), ...next };
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
    window.dispatchEvent(new CustomEvent(EVENT_NAME));
  } catch {
    /* localStorage unavailable — UI falls back to the defaults each render */
  }
}
