// Single API layer for AfyaConnect.
//
// Every function returns the SAME shape as the real FastAPI backend
// (see backend/main.py), so flipping USE_MOCK to false is the only change
// needed once the backend team ships. Until then, mocks keep the whole app
// demoable end-to-end.
//
// DO NOT flip USE_MOCK to false until the backend team has:
//   - fixed the broken security.py imports
//   - made /patients/register actually write to the DB
//   - added a password field + preferred_language to the Patient model
//   - built the auth + appointment + audit endpoints
//   - added Kiswahili triage keywords
//   - locked down CORS

import Constants from 'expo-constants';

export const USE_MOCK = true;

const BASE_URL =
  Constants?.expoConfig?.extra?.apiBaseUrl || 'http://localhost:8000';

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

const wait = (ms) => new Promise((r) => setTimeout(r, ms));

async function realRequest(path, { method = 'GET', body, token } = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => '');
    throw new Error(`API ${res.status}: ${detail || res.statusText}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Mock triage — mirrors the backend's keyword analysis, EN + SW + code-switch.
// Return shape === TriageResponse in backend/main.py.
// ---------------------------------------------------------------------------

const TRIAGE_RULES = [
  {
    priority: 'critical',
    urgency_minutes: 0,
    keywords: [
      'chest pain', 'kifua', 'maumivu ya kifua',
      'difficulty breathing', 'cannot breathe', 'kupumua', 'ugumu wa kupumua',
      'autonomic', 'dysreflexia', 'pounding headache and sweating',
      'headache and sweating', 'kichwa na jasho',
    ],
    conditions: [
      { name: 'Autonomic dysreflexia (possible)', likelihood: 'needs urgent check' },
      { name: 'Cardiac / respiratory emergency', likelihood: 'cannot rule out' },
    ],
    action: 'Seek emergency care now. Do not wait.',
    reasoning:
      'You described symptoms that can signal a medical emergency, including autonomic dysreflexia, which needs immediate attention for people with spinal cord injury.',
  },
  {
    priority: 'high',
    urgency_minutes: 30,
    keywords: [
      'fever', 'homa', 'bladder', 'kibofu', 'catheter', 'mrija',
      'pressure sore', 'kidonda', 'blood', 'damu', 'high fever',
    ],
    conditions: [
      { name: 'Infection (urinary / skin)', likelihood: 'likely' },
    ],
    action: 'A nurse should see you soon. Please join the queue.',
    reasoning:
      'Fever, catheter problems and pressure sores can become serious infections quickly for people with limited mobility, so they are prioritised.',
  },
  {
    priority: 'medium',
    urgency_minutes: 120,
    keywords: ['headache', 'kichwa', 'nausea', 'kichefuchefu', 'dizzy', 'kizunguzungu', 'tired', 'uchovu'],
    conditions: [{ name: 'General unwellness', likelihood: 'to assess' }],
    action: 'Join the queue to speak with a nurse today.',
    reasoning: 'Your symptoms should be checked but are not immediately dangerous.',
  },
];

function mockTriage(symptomsText) {
  const text = (symptomsText || '').toLowerCase();
  const matched = [];
  let rule = null;
  for (const r of TRIAGE_RULES) {
    const hits = r.keywords.filter((k) => text.includes(k));
    if (hits.length) {
      matched.push(...hits);
      rule = r;
      break; // rules are ordered most-severe first
    }
  }
  if (!rule) {
    rule = {
      priority: 'low',
      urgency_minutes: 240,
      conditions: [{ name: 'No urgent signs detected', likelihood: 'routine' }],
      action: 'You can book a routine consultation. Join the queue when ready.',
      reasoning: 'No urgent keywords were detected in your description.',
    };
  }
  return {
    priority: rule.priority,
    confidence: matched.length ? 0.86 : 0.6,
    recommended_action: rule.action,
    urgency_minutes: rule.urgency_minutes,
    reasoning: rule.reasoning,
    matched_symptoms: Array.from(new Set(matched)),
    potential_conditions: rule.conditions,
  };
}

// In-memory mock queue so status can advance believably between polls.
const mockTickets = {};

function priorityRank(p) {
  return { critical: 0, high: 1, medium: 2, low: 3 }[p] ?? 3;
}

// ---------------------------------------------------------------------------
// Public API surface
// ---------------------------------------------------------------------------

export const api = {
  // ---- AUTH ----
  async login({ phone, password }) {
    if (USE_MOCK) {
      await wait(500);
      if (!phone || !password) throw new Error('invalid_credentials');
      return {
        access_token: `mock-token-${Date.now()}`,
        token_type: 'bearer',
        patient: mockMe(phone),
      };
    }
    return realRequest('/auth/login', { method: 'POST', body: { phone, password } });
  },

  async register({ name, phone, password, preferred_language }) {
    if (USE_MOCK) {
      await wait(600);
      const [first_name, ...rest] = (name || '').trim().split(' ');
      const patient_id = `P${Date.now()}`;
      return {
        access_token: `mock-token-${Date.now()}`,
        token_type: 'bearer',
        patient: {
          ...mockMe(phone),
          patient_id,
          first_name: first_name || 'Friend',
          last_name: rest.join(' '),
          preferred_language: preferred_language || 'en',
        },
      };
    }
    // NOTE: backend endpoint is /patients/register today; a real /auth/register
    // that also writes the patient + password is pending on the backend team.
    return realRequest('/auth/register', {
      method: 'POST',
      body: { name, phone, password, preferred_language },
    });
  },

  async me({ token }) {
    if (USE_MOCK) {
      await wait(200);
      return mockMe();
    }
    return realRequest('/auth/me', { token });
  },

  // ---- TRIAGE ----
  async reportSymptoms({ patient_id, symptoms_text, pain_level, duration_hours }) {
    if (USE_MOCK) {
      await wait(700);
      return mockTriage(symptoms_text);
    }
    return realRequest('/triage/report', {
      method: 'POST',
      body: { patient_id, symptoms_text, pain_level, duration_hours },
    });
  },

  // ---- QUEUE ----
  async joinQueue({ patient_id, patient_name, priority, is_pwd = true }) {
    if (USE_MOCK) {
      await wait(500);
      const ticket_id = `T${Date.now()}`;
      // Position seeded by clinical priority; PWDs sorted up within a tier.
      const basePos = priorityRank(priority) * 3 + 2;
      mockTickets[ticket_id] = {
        ticket_id,
        priority,
        is_pwd,
        position: basePos,
        total_waiting: basePos + 4,
        lastPolled: Date.now(),
      };
      const estimated_wait_minutes = basePos * 8;
      const teleconsult_offered =
        estimated_wait_minutes > 45 && ['low', 'medium'].includes(priority);
      return {
        ticket_id,
        position: basePos,
        total_waiting: basePos + 4,
        estimated_wait_minutes,
        eta: new Date(Date.now() + estimated_wait_minutes * 60000).toISOString(),
        clinical_priority: priority,
        is_pwd,
        teleconsult_offered,
        message: `You are position ${basePos} of ${basePos + 4}. Estimated wait: ${estimated_wait_minutes} minutes.`,
      };
    }
    return realRequest('/queue/join', {
      method: 'POST',
      body: { patient_id, patient_name, priority, is_pwd },
    });
  },

  async queueStatus({ ticket_id }) {
    if (USE_MOCK) {
      await wait(300);
      const t = mockTickets[ticket_id];
      if (!t) throw new Error('Ticket not found');
      // Advance ~1 position every poll so the demo visibly progresses.
      const elapsed = Date.now() - t.lastPolled;
      if (elapsed > 1500 && t.position > 1) {
        t.position -= 1;
        t.total_waiting = Math.max(t.total_waiting - 1, t.position);
        t.lastPolled = Date.now();
      }
      const estimated_wait_minutes = t.position * 8;
      const teleconsult_offered =
        estimated_wait_minutes > 45 && ['low', 'medium'].includes(t.priority);
      return {
        ticket_id,
        position: t.position,
        total_waiting: t.total_waiting,
        estimated_wait_minutes,
        eta: new Date(Date.now() + estimated_wait_minutes * 60000).toISOString(),
        clinical_priority: t.priority,
        is_pwd: t.is_pwd,
        teleconsult_offered,
        message: `You are position ${t.position} of ${t.total_waiting}. Estimated wait: ${estimated_wait_minutes} minutes.`,
      };
    }
    return realRequest(`/queue/status/${ticket_id}`);
  },

  async acceptTeleconsult({ ticket_id }) {
    if (USE_MOCK) {
      await wait(500);
      delete mockTickets[ticket_id];
      return {
        success: true,
        message: 'Teleconsult accepted. You will receive a video call link via SMS.',
        next_steps: [
          'Check SMS for meeting link',
          'Test camera and microphone',
          'Have medications list ready',
          'Caregiver can join if needed',
        ],
      };
    }
    return realRequest(`/queue/teleconsult/accept/${ticket_id}`, { method: 'POST' });
  },

  // ---- APPOINTMENTS (backend endpoint PENDING — mocked, flagged) ----
  async appointments({ patient_id }) {
    if (USE_MOCK) {
      await wait(400);
      return { appointments: MOCK_APPOINTMENTS, _mock: true };
    }
    // TODO(backend): GET /appointments does not exist yet.
    return realRequest('/appointments');
  },

  // ---- CAREGIVER AUDIT LOG (backend endpoint PENDING — stubbed, flagged) ----
  async logCaregiverAction({ caregiver_id, patient_id, action, meta }) {
    const entry = {
      caregiver_id,
      patient_id,
      action,
      meta: meta || {},
      timestamp: new Date().toISOString(),
    };
    if (USE_MOCK) {
      // TODO(backend): POST /audit/log (AuditLog) does not exist yet.
      // Kept as a local record so the flow is honest and testable.
      console.log('[AUDIT:MOCK]', entry);
      return { logged: true, _mock: true, entry };
    }
    return realRequest('/audit/log', { method: 'POST', body: entry });
  },

  // ---- VOICE ----
  async voiceCommand({ patient_id, audio_data, command_type }) {
    if (USE_MOCK) {
      await wait(300);
      return { action: command_type, message: 'Command received', _mock: true };
    }
    return realRequest('/voice/command', {
      method: 'POST',
      body: { patient_id, audio_data, command_type },
    });
  },
};

// ---------------------------------------------------------------------------
// Mock fixtures
// ---------------------------------------------------------------------------

function mockMe(phone = '+254712345678') {
  return {
    patient_id: 'P20260729',
    first_name: 'Amina',
    last_name: 'Wanjiru',
    phone_primary: phone,
    phone_emergency: '+254733111222',
    disability_type: 'quadriplegia',
    primary_assistive_tech: 'switch',
    preferred_language: 'en',
    has_caregiver: true,
    caregiver_name: 'Joseph Mwangi',
    caregiver_phone: '+254799888777',
    caregiver_can_schedule: true,
    caregiver_can_consent: false,
    conditions: ['Spinal cord injury (C5)', 'Neurogenic bladder'],
    medications: ['Baclofen', 'Oxybutynin'],
    allergies: ['Penicillin'],
    address_line1: 'House 12, Jamii Estate',
    city: 'Nairobi',
    region: 'Nairobi',
  };
}

const MOCK_APPOINTMENTS = [
  {
    id: 'A1001',
    type: 'teleconsult',
    provider: 'Dr. Otieno (Rehab Medicine)',
    starts_at: new Date(Date.now() + 2 * 3600 * 1000).toISOString(),
    joinable: true,
  },
  {
    id: 'A1002',
    type: 'home_visit',
    provider: 'Nurse Faith — wound care',
    starts_at: new Date(Date.now() + 2 * 86400 * 1000).toISOString(),
    joinable: false,
  },
  {
    id: 'A1003',
    type: 'hospital',
    provider: 'Kenyatta National Hospital — Urology',
    starts_at: new Date(Date.now() + 6 * 86400 * 1000).toISOString(),
    joinable: false,
  },
];
