// Text-to-speech (expo-speech, works in Expo Go) and a gated speech-to-text
// path. STT (expo-speech-recognition) needs a dev build, so we feature-detect
// it and fall back to a typed-confirmation modal in Expo Go.

import { useCallback, useContext } from 'react';
import * as Speech from 'expo-speech';
import { AppContext } from '../context/AppContext';
import { speechLocale } from '../theme/accessibility';

// Feature-detect the optional native STT module without hard-depending on it.
let SpeechRecognition = null;
try {
  // eslint-disable-next-line global-require
  SpeechRecognition = require('expo-speech-recognition');
} catch (e) {
  SpeechRecognition = null;
}

export const STT_AVAILABLE = !!(
  SpeechRecognition && SpeechRecognition.ExpoSpeechRecognitionModule
);

export function useSpeech() {
  const { lang } = useContext(AppContext);

  const speak = useCallback(
    (text, opts = {}) => {
      if (!text) return;
      Speech.stop();
      Speech.speak(text, {
        language: speechLocale(lang),
        rate: opts.rate ?? 0.98,
        pitch: opts.pitch ?? 1.0,
        ...opts,
      });
    },
    [lang]
  );

  const stop = useCallback(() => Speech.stop(), []);

  return { speak, stop, sttAvailable: STT_AVAILABLE };
}
