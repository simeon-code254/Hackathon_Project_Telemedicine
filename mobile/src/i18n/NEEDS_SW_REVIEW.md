# Kiswahili terms that MUST be reviewed by a fluent speaker before real use

> A wrong medical term in triage is a **safety issue, not a typo**. The strings
> below are my best-effort translations. Do not ship them to real patients until
> a fluent Kenyan Kiswahili speaker with clinical familiarity has reviewed each
> one. Non-medical UI strings are not listed here.

## Clinical / triage terms (highest priority to review)

| Key | English | My best-effort Kiswahili | Confidence | Notes |
|---|---|---|---|---|
| `symptom.presets.chest_pain` | Chest pain | Maumivu ya kifua | high | Common, widely understood. |
| `symptom.presets.headache_sweating` | Bad headache with sweating | Maumivu makali ya kichwa na jasho | medium | This preset doubles as an **autonomic dysreflexia** signal — the phrasing should make a patient recognise their own AD symptoms. Consider clinician wording. |
| `symptom.presets.fever` | Fever | Homa | high | Standard. |
| `symptom.presets.breathing` | Difficulty breathing | Ugumu wa kupumua | high | "Kupumua kwa shida" is an alternative — confirm preferred. |
| `symptom.presets.bladder` | Bladder or catheter problem | Tatizo la kibofu au mrija (catheter) | low | Left English "catheter" in parentheses on purpose; there's no universally recognised Kiswahili loanword. Confirm patients understand "mrija". |
| `symptom.presets.pressure_sore` | Pressure sore | Kidonda cha mgandamizo | low | Uncertain. May be better expressed descriptively ("kidonda cha kukaa/kulala muda mrefu"). Needs clinical review. |
| `triage.priority.critical` | Critical | Hatari kubwa | medium | Must read as clinically urgent, not merely "dangerous". |
| `triage.priority.high` | High | Juu | medium | Confirm this reads as urgency, not literal "up/above". |
| `triage.priority.medium` | Medium | Wastani | high | |
| `triage.priority.low` | Low | Chini | medium | Confirm reads as urgency level. |
| `symptom.painLevel` | Pain level | Kiwango cha maumivu | high | |

## Also worth a native-speaker pass (non-clinical but user-facing)

- `queue.youAreNext` — "Wewe ni wa pili sasa" (lit. "you are second") is used to mean "you're next after the person being seen". Confirm this is natural.
- `app.tagline` — "Huduma. Muunganiko. Popote." is a translation of "Care. Connect. Anywhere." Marketing tone may want a fluent rewrite.
- `caregiver.*` — consent/audit phrasing is legally flavoured; confirm tone is right.

## Voice command keywords (see `services/voiceCommands.js`)

Code-switching is expected ("nina chest pain kidogo"). The keyword matcher
includes both English and Kiswahili triggers. A native speaker should expand the
Kiswahili keyword lists (especially regional/colloquial symptom words).
