# AfyaConnect — mobile app

Accessibility-first telemedicine for people with disabilities in Kenya.
**"Care. Connect. Anywhere."** — Expo (SDK 52) + React Native 0.76, light theme,
bilingual (English + Kiswahili).

## Run it

```bash
cd mobile
npm install
npx expo start        # press i / a, or scan the QR with Expo Go
```

- **TTS (expo-speech)** works in Expo Go.
- **STT (expo-speech-recognition)** needs a dev build. It is feature-gated: in
  Expo Go the mic button falls back to a typed-confirmation modal. Nothing is
  faked.

## The non-negotiable: four paths on every screen

Every screen supports all four, driven entirely by `getAccessibilityTheme()` in
`src/theme/accessibility.js` (screens never hardcode a size or color):

1. **Spoken** — `SpokenScreen` announces the screen's purpose aloud on mount, in
   the user's language, and mirrors it to the screen-reader live region.
2. **Single-input** — `ScanGroup` / `useScanner` auto-highlights items, speaks
   each as it lands, and exposes one "Select highlighted" control. The scanner
   **turns itself off when a screen reader is active** (so it doesn't fight
   VoiceOver/TalkBack focus).
3. **Screen-reader** — roles, labels, states, hints, live regions, modal focus.
4. **Large-touch** — ≥48pt targets (up to 90pt per profile), `hitSlop`, spacing.

## Screens (all 12 built)

| # | Screen | Notable paths |
|---|---|---|
| 1 | LanguageSelect | spoken in **both** languages; force-scan pre-profile |
| 2 | Auth | keyboard-avoiding; live-region validation errors |
| 3 | AccessibilitySetup | force-scan + speaks options *before* profile is known |
| 4 | Home | voice-first mic vs. scanner list; bilingual command routing |
| 5 | SymptomReport | preset picker (primary for switch users) + voice + text; one scanner spans all controls; critical presets get the red border |
| 6 | TriageResult | result spoken on arrival; clinical color card |
| 7 | QueueStatus | auto-refresh; **milestone-only** announcements; teleconsult offer |
| 8 | Appointments | invitation empty state; **mocked** list (flagged) |
| 9 | Emergency | one action from any screen; red bg; force-scan; spoken every step |
| 10 | CaregiverProxy | confirmation-only entry; write actions gated by `caregiver_can_*`; audit **stubbed** (flagged) |
| 11 | Settings | re-tune language/profile/scan speed/font/dwell/contrast in the current mode |
| 12 | Profile | read-only first; edit behind an explicit action |

## Modes — honest status

- **Fully built:** voice (TTS now, STT in a dev build), the custom switch/sip-puff
  scanner, caregiver proxy, and OS-accessibility conformance (roles/labels/focus)
  — which is what lets real head-mouse / eye-tracking hardware drive the app.
- **Not faked:** no in-app camera eye-tracking, no pretend Bluetooth sip-puff
  "connection". Head-mouse / eye-tracking rely on OS accessible-pointer support
  (iOS 17+ for eye tracking; not native on Android). Our job there is conformance.

## What's real vs. mocked (the honest ledger)

`src/services/api.js` has a single `USE_MOCK = true` flag. Every mock returns the
**same shape** as the FastAPI backend (`backend/main.py`) so flipping to `false`
is the only change needed — but do **not** flip until the backend team has:

- fixed the broken `security.py` imports
- made `/patients/register` actually write to the DB
- added a password field + `preferred_language` to the Patient model
- built `/auth/login`, `/auth/register`, `/auth/me`
- built **`GET /appointments`** (screen 8 is mocked until then — flagged in-app)
- built **`POST /audit/log`** for `AuditLog` (caregiver actions are stubbed to
  console + local until then — flagged in-app)
- added Kiswahili triage keywords
- locked down CORS

Mock/stub points, all flagged in code and in the UI where user-visible:

- **Appointments** — `api.appointments()` returns fixtures (`_mock: true`); screen
  shows a demo notice.
- **Caregiver audit log** — `api.logCaregiverAction()` logs to console + returns
  `_mock: true`; screen shows a demo notice.
- **Triage** — mock keyword analyzer mirrors the backend's, incl. an autonomic
  dysreflexia (headache+sweating) critical path and EN/SW/code-switch keywords.
- **Queue** — in-memory ticket advances ~1 position per poll so the demo moves.
- **Emergency** — mock alert to caregiver + care team (no fake ambulance dispatch).

## Bilingual & safety

- All strings via `t()` from `src/i18n/en.json` / `sw.json`. TTS speaks `en-US` /
  `sw-KE`.
- **Every clinical/triage Kiswahili term is flagged for review** in
  `src/i18n/NEEDS_SW_REVIEW.md`. A wrong medical term in triage is a safety issue,
  not a typo — do not ship those translations to real patients unreviewed.
- Voice-command matching handles code-switching (`src/services/voiceCommands.js`).

## Not automatable here

The a11y checklist item "manually tested with VoiceOver and TalkBack" requires a
real device/simulator and a human. Everything else in the checklist is wired in
code; VoiceOver/TalkBack passes still need to be done before calling a screen
truly "done".
