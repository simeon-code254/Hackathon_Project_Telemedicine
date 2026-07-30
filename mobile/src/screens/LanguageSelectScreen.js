import React, { useContext, useEffect } from 'react';
import { View, Text } from 'react-native';
import { useTranslation } from 'react-i18next';
import { AppContext } from '../context/AppContext';
import { useSpeech } from '../hooks/useSpeech';
import SpokenScreen from '../components/SpokenScreen';
import ScreenHeader from '../components/ScreenHeader';
import ScanGroup from '../components/ScanGroup';
import en from '../i18n/en.json';

// SCREEN 1 — Language select.
// Spoken in BOTH languages on arrival (a user who only reads/hears Kiswahili must
// still understand the English prompt and vice versa). Operable pre-profile via
// forced auto-scan + large buttons.
export default function LanguageSelectScreen({ navigation }) {
  const { t } = useTranslation();
  const { theme, setLang } = useContext(AppContext);
  const { speak } = useSpeech();

  // Speak the bilingual welcome once, English then Kiswahili.
  useEffect(() => {
    const timer = setTimeout(() => {
      speak(en.language.spoken, { language: 'en-US' });
      setTimeout(() => speak(en.language.spokenSw, { language: 'sw-KE' }), 3200);
    }, 400);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const choose = async (lng) => {
    await setLang(lng);
    navigation.replace('Auth');
  };

  const items = [
    { key: 'en', label: t('language.english'), speech: 'English', variant: 'primary', onSelect: () => choose('en') },
    { key: 'sw', label: t('language.swahili'), speech: 'Kiswahili', variant: 'primary', onSelect: () => choose('sw') },
  ];

  return (
    <SpokenScreen>
      <View style={{ flex: 1, justifyContent: 'center' }}>
        <Text
          allowFontScaling
          accessibilityRole="header"
          style={{ color: theme.colors.primary, fontSize: theme.font.display, fontWeight: '900', textAlign: 'center' }}
        >
          {t('app.name')}
        </Text>
        <Text
          allowFontScaling
          style={{ color: theme.colors.textMuted, fontSize: theme.font.label, textAlign: 'center', marginBottom: theme.spacing.xl }}
        >
          {t('app.tagline')}
        </Text>
        <ScreenHeader title={t('language.title')} subtitle={t('language.hint')} />
        <ScanGroup items={items} forceScan speedMs={2200} />
      </View>
    </SpokenScreen>
  );
}
