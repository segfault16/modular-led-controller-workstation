import { KeyboardShortcuts, MidiNumbers } from 'react-piano';

export const firstNote = MidiNumbers.fromNote('c0');
export const lastNote = MidiNumbers.fromNote('f2');
export const keyboardShortcuts = KeyboardShortcuts.create({
  firstNote: firstNote,
  lastNote: lastNote,
  keyboardConfig: KeyboardShortcuts.HOME_ROW,
});