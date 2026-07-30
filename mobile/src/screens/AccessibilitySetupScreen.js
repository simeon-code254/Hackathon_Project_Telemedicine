import React, { useContext } from 'react';
import { useTranslation } from 'react-i18next';
import { AppContext } from '../context/AppContext';
import { useSpeech } from '../hooks/useSpeech';
import SpokenScreen from '../components/SpokenScreen';
import ScreenHeader from '../components/ScreenHeader';
import ScanGroup from '../components/ScanGroup';
import { announce } from '../utils/a11y';

// SCREEN 3 — Accessibility setup (the chicken-and-egg screen).
// It auto-scans and speaks the options so it is operable BEFORE we know the
// user's profile. Choosing an option sets the profile, which re-themes the app.
const PROFILES = ['voice', 'switch', 'sip_puff', 'eye_tracking', 'head_mouse', 'none'];

export default function AccessibilitySetupScreen({ navigation }) {
  const { t } = useTranslation();
  const { setAssistiveTech } = useContext(AppContext);
  const { speak } = useSpeech();

  const choose = async (tech) => {
    await setAssistiveTech(tech);
    announce(t('access.saved'));
    speak(t('access.saved'));
    navigation.reset({ index: 0, routes: [{ name: 'Home' }] });
  };

  const items = PROFILES.map((key) => ({
    key,
    label: t(`access.${key}`),
    sublabel: t(`access.${key}Desc`),
    speech: `${t(`access.${key}`)}. ${t(`access.${key}Desc`)}`,
    variant: 'surface',
    hint: t(`access.${key}Desc`),
    onSelect: () => choose(key),
  }));

  return (
    <SpokenScreen speech={t('access.spoken')}>
      <ScreenHeader title={t('access.title')} subtitle={t('access.hint')} />
      {/* forceScan: this screen must scan regardless of profile, since the
          profile is exactly what we're choosing. */}
      <ScanGroup items={items} forceScan speedMs={2400} />
    </SpokenScreen>
  );
}
