import React, { useContext, useState } from 'react';
import { View, Text, ActivityIndicator } from 'react-native';
import { useTranslation } from 'react-i18next';
import { AppContext } from '../context/AppContext';
import SpokenScreen from '../components/SpokenScreen';
import ScreenHeader from '../components/ScreenHeader';
import PriorityCard from '../components/PriorityCard';
import ScanGroup from '../components/ScanGroup';
import { api } from '../services/api';
import { announce } from '../utils/a11y';

// SCREEN 6 — Triage result. The priority, reasoning and recommended action are
// spoken aloud on arrival (voice/blind users must hear the outcome, not hunt for
// it). Colors are the clinical severity convention via PriorityCard.
export default function TriageResultScreen({ navigation, route }) {
  const { t } = useTranslation();
  const { theme, user, caregiver } = useContext(AppContext);
  const triage = route.params?.triage || {};
  const priority = triage.priority || 'medium';
  const [busy, setBusy] = useState(false);

  const priorityLabel = t(`triage.priority.${priority}`);
  const confidencePct = Math.round((triage.confidence || 0) * 100);

  // Full spoken summary for the screen's spoken path.
  const spoken = [
    t('triage.spokenPrefix'),
    `${t('triage.priorityLabel')}: ${priorityLabel}.`,
    triage.reasoning || '',
    t('triage.spokenAction', { action: triage.recommended_action || '' }),
  ].join(' ');

  const joinQueue = async () => {
    setBusy(true);
    announce(t('queue.refreshing'));
    try {
      const patientId = caregiver?.patient?.patient_id || user?.patient_id;
      const patientName = caregiver?.patient?.first_name || user?.first_name || 'Patient';
      const res = await api.joinQueue({
        patient_id: patientId,
        patient_name: patientName,
        priority,
        is_pwd: true,
      });
      navigation.navigate('Queue', { ticket: res });
    } catch (e) {
      announce(t('common.error'));
    } finally {
      setBusy(false);
    }
  };

  const items = [
    {
      key: 'join',
      label: t('triage.joinQueue'),
      speech: t('triage.joinQueue'),
      variant: 'primary',
      hint: t('triage.joinQueueHint'),
      onSelect: joinQueue,
    },
    {
      key: 'home',
      label: t('common.backHome'),
      speech: t('common.backHome'),
      variant: 'surface',
      onSelect: () => navigation.navigate('Home'),
    },
  ];

  return (
    <SpokenScreen speech={spoken}>
      <ScreenHeader title={t('triage.title')} />

      <PriorityCard
        priority={priority}
        priorityLabel={priorityLabel}
        summary={t('triage.priorityLabel')}
        confidenceText={t('triage.confidence', { pct: confidencePct })}
      />

      <Text accessibilityRole="header" allowFontScaling style={{ color: theme.colors.text, fontSize: theme.font.label, fontWeight: '800', marginBottom: theme.spacing.xs }}>
        {t('triage.reasoningHeading')}
      </Text>
      <Text allowFontScaling style={{ color: theme.colors.text, fontSize: theme.font.body, marginBottom: theme.spacing.md }}>
        {triage.reasoning}
      </Text>

      <Text accessibilityRole="header" allowFontScaling style={{ color: theme.colors.text, fontSize: theme.font.label, fontWeight: '800', marginBottom: theme.spacing.xs }}>
        {t('triage.actionHeading')}
      </Text>
      <Text allowFontScaling style={{ color: theme.colors.text, fontSize: theme.font.body, marginBottom: theme.spacing.lg }}>
        {triage.recommended_action}
      </Text>

      {busy ? (
        <ActivityIndicator size="large" color={theme.colors.primary} accessibilityLabel={t('common.loading')} />
      ) : (
        <ScanGroup items={items} />
      )}
    </SpokenScreen>
  );
}
