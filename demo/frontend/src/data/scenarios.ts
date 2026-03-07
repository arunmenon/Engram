import type { GraphNode, GraphEdge } from '../types/graph';
import type { ChatMessage, Session } from '../types/chat';
import type { UserProfile, UserPreference, UserSkill, UserInterest } from './mockUserProfile';
import type { EnhancedPattern } from '../types/behavioral';

// ─── Sarah Chen imports ────────────────────────────────────────────────────
import { sessions as sarahSessions, messages as sarahMessages } from './mockSessions';
import { mockNodes as sarahNodes, mockEdges as sarahEdges } from './mockGraph';
import {
  sarahProfile, sarahPreferences, sarahSkills,
  sarahInterests, sarahEnhancedPatterns,
} from './mockUserProfile';

// ─── Marcus Rivera (Merchant) imports ──────────────────────────────────────
import {
  merchantSessions, merchantMessages, merchantNodes, merchantEdges,
  marcusProfile, marcusPreferences, marcusSkills,
  marcusInterests, marcusEnhancedPatterns,
} from './merchantScenario';

// ─── Priya Sharma (Travel) imports ─────────────────────────────────────────
import {
  travelSessions, travelMessages, travelNodes, travelEdges,
  priyaProfile, priyaPreferences, priyaSkills,
  priyaInterests, priyaEnhancedPatterns,
} from './travelScenario';

// ─── David Park (Real Estate) imports ──────────────────────────────────────
import {
  realtySessions, realtyMessages, realtyNodes, realtyEdges,
  davidProfile, davidPreferences, davidSkills,
  davidInterests, davidEnhancedPatterns,
} from './realEstateScenario';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface AtlasSnapshot {
  afterStepIndex: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
  userProfile: UserProfile | null;
  preferences: UserPreference[];
  skills: UserSkill[];
  interests: UserInterest[];
  patterns: EnhancedPattern[];
}

export interface SimulatorScenario {
  id: string;
  title: string;
  subtitle: string;
  description: string;
  persona: { name: string; avatar: string; color: string };
  sessions: Session[];
  messages: ChatMessage[];
  atlasSnapshots: AtlasSnapshot[];
}

// ─── Generic Snapshot Builder ───────────────────────────────────────────────

interface UserDataAtStep {
  profile: UserProfile | null;
  preferences: UserPreference[];
  skills: UserSkill[];
  interests: UserInterest[];
  patterns: EnhancedPattern[];
}

/** Rule for when a piece of user data appears */
interface UserDataRule {
  step: number;
  kind: 'profile' | 'preference' | 'skill' | 'interest' | 'pattern';
  index: number; // index into the source array
  /** For patterns: override confidence at this step */
  confidence?: number;
  /** For patterns: how many observations to show */
  obsCount?: number;
}

interface ScenarioDataPack {
  allNodes: GraphNode[];
  allEdges: GraphEdge[];
  stepNodeIds: string[][];
  profile: UserProfile;
  preferences: UserPreference[];
  skills: UserSkill[];
  interests: UserInterest[];
  patterns: EnhancedPattern[];
  userDataRules: UserDataRule[];
}

function buildGenericSnapshots(pack: ScenarioDataPack): AtlasSnapshot[] {
  const nodeMap = new Map(pack.allNodes.map(n => [n.id, n]));
  const snapshots: AtlasSnapshot[] = [];
  const cumulativeNodeIds = new Set<string>();

  for (let step = 0; step < pack.stepNodeIds.length; step++) {
    for (const id of pack.stepNodeIds[step]) {
      cumulativeNodeIds.add(id);
    }

    const nodes = [...cumulativeNodeIds]
      .map(id => nodeMap.get(id))
      .filter((n): n is GraphNode => !!n);

    const edges = pack.allEdges.filter(
      e => cumulativeNodeIds.has(e.source) && cumulativeNodeIds.has(e.target),
    );

    // Build user data from rules
    const userData: { userProfile: UserProfile | null; preferences: UserPreference[]; skills: UserSkill[]; interests: UserInterest[]; patterns: EnhancedPattern[] } = {
      userProfile: null,
      preferences: [],
      skills: [],
      interests: [],
      patterns: [],
    };

    for (const rule of pack.userDataRules) {
      if (step < rule.step) continue;
      switch (rule.kind) {
        case 'profile':
          userData.userProfile = pack.profile;
          break;
        case 'preference':
          if (pack.preferences[rule.index]) userData.preferences.push(pack.preferences[rule.index]);
          break;
        case 'skill':
          if (pack.skills[rule.index]) userData.skills.push(pack.skills[rule.index]);
          break;
        case 'interest':
          if (pack.interests[rule.index]) userData.interests.push(pack.interests[rule.index]);
          break;
        case 'pattern': {
          const base = pack.patterns[rule.index];
          if (!base) break;
          userData.patterns.push({
            ...base,
            confidence: rule.confidence ?? base.confidence,
            observations: base.observations.slice(0, rule.obsCount ?? base.observations.length),
          });
          break;
        }
      }
    }

    snapshots.push({
      afterStepIndex: step,
      nodes,
      edges,
      ...userData,
    });
  }

  return snapshots;
}

// ─── Sarah Chen — SaaS Support ─────────────────────────────────────────────

const sarahPack: ScenarioDataPack = {
  allNodes: sarahNodes,
  allEdges: sarahEdges,
  stepNodeIds: [
    ['evt-1-start', 'evt-1-1', 'entity-sarah', 'entity-nimbus', 'entity-billing'],
    ['evt-1-2'],
    [],
    ['evt-1-3', 'evt-1-4', 'entity-refund'],
    ['evt-1-5', 'pref-email', 'profile-sarah'],
    ['evt-1-end', 'summary-s1', 'skill-leadership'],
    ['evt-2-start', 'evt-2-1', 'entity-kanban'],
    ['evt-2-2', 'skill-kanban', 'pref-kanban'],
    ['evt-2-3', 'entity-swimlanes'],
    [],
    ['evt-2-4', 'entity-taskflow', 'pref-taskflow'],
    ['evt-2-end', 'summary-s2'],
    ['evt-3-start', 'evt-3-1', 'entity-sprint-data', 'pref-nimbus'],
    ['evt-3-2', 'evt-3-3', 'pattern-escalation'],
    [],
    ['evt-3-4'],
    [],
    ['evt-3-end'],
  ],
  profile: sarahProfile,
  preferences: sarahPreferences,
  skills: sarahSkills,
  interests: sarahInterests,
  patterns: sarahEnhancedPatterns,
  userDataRules: [
    { step: 4, kind: 'profile', index: 0 },
    { step: 4, kind: 'preference', index: 0 },
    { step: 7, kind: 'preference', index: 1 },
    { step: 10, kind: 'preference', index: 3 },
    { step: 12, kind: 'preference', index: 2 },
    { step: 5, kind: 'skill', index: 0 },
    { step: 7, kind: 'skill', index: 1 },
    { step: 6, kind: 'interest', index: 0 },
    { step: 8, kind: 'interest', index: 1 },
    { step: 10, kind: 'interest', index: 2 },
    { step: 12, kind: 'interest', index: 3 },
    { step: 5, kind: 'pattern', index: 1, confidence: 0.80, obsCount: 1 },
    { step: 13, kind: 'pattern', index: 0, confidence: 0.55, obsCount: 1 },
  ],
};

export const sarahChenScenario: SimulatorScenario = {
  id: 'sarah-chen-saas',
  title: 'Sarah Chen — SaaS Support',
  subtitle: 'Billing, features & escalation across 3 sessions',
  description: 'A customer support story spanning billing disputes, feature requests, and data loss escalation. Watch the context graph capture entities, preferences, skills, and churn-risk patterns.',
  persona: { name: 'Sarah Chen', avatar: 'SC', color: '#8b5cf6' },
  sessions: sarahSessions,
  messages: sarahMessages,
  atlasSnapshots: buildGenericSnapshots(sarahPack),
};

// ─── Marcus Rivera — PayPal Merchant SMB ────────────────────────────────────

const marcusPack: ScenarioDataPack = {
  allNodes: merchantNodes,
  allEdges: merchantEdges,
  stepNodeIds: [
    // S1: Chargeback
    ['merch-evt-1-start', 'merch-evt-1-1', 'merch-entity-marcus', 'merch-entity-paypal', 'merch-entity-chargeback'],
    ['merch-evt-1-2'],
    [],
    ['merch-evt-1-3', 'merch-entity-fedex'],
    ['merch-evt-1-4', 'merch-pref-sms', 'merch-profile-marcus'],
    ['merch-evt-1-end', 'merch-summary-s1', 'merch-skill-ecommerce'],
    // S2: Webhook
    ['merch-evt-2-start', 'merch-evt-2-1', 'merch-entity-shopify'],
    ['merch-evt-2-2', 'merch-entity-webhook', 'merch-entity-rest-api', 'merch-skill-api'],
    [],
    ['merch-evt-2-3', 'merch-entity-stripe', 'merch-pref-stripe'],
    [],
    ['merch-evt-2-end', 'merch-summary-s2'],
    // S3: Settlement
    ['merch-evt-3-start', 'merch-evt-3-1', 'merch-entity-settlement', 'merch-pref-paypal'],
    ['merch-evt-3-2', 'merch-evt-3-3', 'merch-pattern-cashflow', 'merch-pref-cashflow'],
    [],
    ['merch-evt-3-4'],
    [],
    ['merch-evt-3-end'],
  ],
  profile: marcusProfile,
  preferences: marcusPreferences,
  skills: marcusSkills,
  interests: marcusInterests,
  patterns: marcusEnhancedPatterns,
  userDataRules: [
    { step: 4, kind: 'profile', index: 0 },
    { step: 4, kind: 'preference', index: 0 },   // SMS
    { step: 9, kind: 'preference', index: 2 },    // Stripe
    { step: 12, kind: 'preference', index: 3 },   // PayPal frustration
    { step: 13, kind: 'preference', index: 1 },   // Cash flow
    { step: 5, kind: 'skill', index: 0 },          // ecommerce
    { step: 7, kind: 'skill', index: 1 },          // API
    { step: 6, kind: 'interest', index: 0 },       // Shopify
    { step: 7, kind: 'interest', index: 1 },       // Webhooks
    { step: 9, kind: 'interest', index: 2 },       // Stripe
    { step: 12, kind: 'interest', index: 3 },      // Settlements
    { step: 4, kind: 'pattern', index: 1, confidence: 0.80, obsCount: 1 },  // SMS pattern
    { step: 13, kind: 'pattern', index: 0, confidence: 0.55, obsCount: 1 }, // Cash flow
  ],
};

export const marcusRiveraScenario: SimulatorScenario = {
  id: 'marcus-rivera-merchant',
  title: 'Marcus Rivera — PayPal Merchant',
  subtitle: 'Chargebacks, integrations & settlement holds',
  description: 'A small business owner navigating PayPal payment challenges: chargeback disputes, webhook API integration, and settlement delays. Watch cash flow sensitivity and churn risk patterns emerge.',
  persona: { name: 'Marcus Rivera', avatar: 'MR', color: '#f59e0b' },
  sessions: merchantSessions,
  messages: merchantMessages,
  atlasSnapshots: buildGenericSnapshots(marcusPack),
};

// ─── Priya Sharma — Emirates Travel ─────────────────────────────────────────

const priyaPack: ScenarioDataPack = {
  allNodes: travelNodes,
  allEdges: travelEdges,
  stepNodeIds: [
    // S1: Rebooking
    ['travel-evt-1-start', 'travel-evt-1-1', 'travel-entity-priya', 'travel-entity-emirates', 'travel-entity-ek029', 'travel-entity-heathrow'],
    ['travel-evt-1-2'],
    [],
    ['travel-evt-1-3', 'travel-entity-skywards'],
    ['travel-evt-1-4', 'travel-pref-whatsapp', 'travel-pref-window', 'travel-profile-priya'],
    ['travel-evt-1-end', 'travel-summary-s1', 'travel-skill-travel'],
    // S2: Upgrade
    ['travel-evt-2-start', 'travel-evt-2-1', 'travel-entity-mumbai-route'],
    ['travel-evt-2-2', 'travel-skill-miles', 'travel-pref-business'],
    [],
    ['travel-evt-2-3'],
    [],
    ['travel-evt-2-end', 'travel-summary-s2'],
    // S3: Lost luggage
    ['travel-evt-3-start', 'travel-evt-3-1', 'travel-entity-luggage'],
    ['travel-evt-3-2', 'travel-evt-3-3', 'travel-pattern-frequent'],
    ['travel-entity-etihad', 'travel-pref-etihad'],
    ['travel-evt-3-4'],
    [],
    ['travel-evt-3-end'],
  ],
  profile: priyaProfile,
  preferences: priyaPreferences,
  skills: priyaSkills,
  interests: priyaInterests,
  patterns: priyaEnhancedPatterns,
  userDataRules: [
    { step: 4, kind: 'profile', index: 0 },
    { step: 4, kind: 'preference', index: 0 },   // WhatsApp
    { step: 4, kind: 'preference', index: 1 },    // Window seat
    { step: 7, kind: 'preference', index: 2 },    // Business class
    { step: 14, kind: 'preference', index: 3 },   // Etihad
    { step: 5, kind: 'skill', index: 1 },          // Frequent travel
    { step: 7, kind: 'skill', index: 0 },          // Miles optimization
    { step: 3, kind: 'interest', index: 0 },       // Skywards
    { step: 6, kind: 'interest', index: 1 },       // Mumbai route
    { step: 14, kind: 'interest', index: 2 },      // Etihad
    { step: 12, kind: 'interest', index: 3 },      // Luggage
    { step: 4, kind: 'pattern', index: 1, confidence: 0.80, obsCount: 1 },  // WhatsApp pattern
    { step: 13, kind: 'pattern', index: 0, confidence: 0.55, obsCount: 1 }, // Frequent flyer
  ],
};

export const priyaSharmaScenario: SimulatorScenario = {
  id: 'priya-sharma-travel',
  title: 'Priya Sharma — Emirates Travel',
  subtitle: 'Rebooking, upgrades & lost luggage',
  description: 'A frequent business traveler on the Mumbai-Dubai corridor dealing with missed connections, miles-based upgrades, and lost luggage. See loyalty patterns, seating preferences, and competitor mentions tracked.',
  persona: { name: 'Priya Sharma', avatar: 'PS', color: '#3b82f6' },
  sessions: travelSessions,
  messages: travelMessages,
  atlasSnapshots: buildGenericSnapshots(priyaPack),
};

// ─── David Park — Real Estate ───────────────────────────────────────────────

const davidPack: ScenarioDataPack = {
  allNodes: realtyNodes,
  allEdges: realtyEdges,
  stepNodeIds: [
    // S1: Property Search
    ['realty-evt-1-start', 'realty-evt-1-1', 'realty-entity-david', 'realty-entity-austin', 'realty-entity-condo'],
    ['realty-evt-1-2'],
    [],
    ['realty-evt-1-3', 'realty-entity-742elm', 'realty-entity-1200congress'],
    ['realty-evt-1-4', 'realty-pref-email', 'realty-pref-firstbuyer', 'realty-pref-modern', 'realty-profile-david'],
    ['realty-evt-1-end', 'realty-summary-s1', 'realty-skill-tech'],
    // S2: Mortgage
    ['realty-evt-2-start', 'realty-evt-2-1'],
    ['realty-evt-2-2', 'realty-entity-mortgage', 'realty-skill-finance'],
    [],
    ['realty-evt-2-3', 'realty-entity-zillow', 'realty-pref-zillow'],
    [],
    ['realty-evt-2-end', 'realty-summary-s2'],
    // S3: Inspection
    ['realty-evt-3-start', 'realty-evt-3-1', 'realty-entity-inspection'],
    ['realty-evt-3-2', 'realty-evt-3-3', 'realty-pattern-cautious'],
    [],
    ['realty-evt-3-4'],
    [],
    ['realty-evt-3-end'],
  ],
  profile: davidProfile,
  preferences: davidPreferences,
  skills: davidSkills,
  interests: davidInterests,
  patterns: davidEnhancedPatterns,
  userDataRules: [
    { step: 4, kind: 'profile', index: 0 },
    { step: 4, kind: 'preference', index: 0 },   // Email
    { step: 4, kind: 'preference', index: 1 },    // First-time buyer
    { step: 4, kind: 'preference', index: 2 },    // Modern construction
    { step: 9, kind: 'preference', index: 3 },    // Zillow comparison
    { step: 5, kind: 'skill', index: 0 },          // Software engineering
    { step: 7, kind: 'skill', index: 1 },          // Financial analysis
    { step: 3, kind: 'interest', index: 0 },       // 742 Elm
    { step: 3, kind: 'interest', index: 1 },       // 1200 Congress
    { step: 7, kind: 'interest', index: 2 },       // Mortgage
    { step: 12, kind: 'interest', index: 3 },      // Inspection
    { step: 4, kind: 'pattern', index: 1, confidence: 0.75, obsCount: 1 },  // Email pattern
    { step: 13, kind: 'pattern', index: 0, confidence: 0.50, obsCount: 1 }, // Cautious buyer
  ],
};

export const davidParkScenario: SimulatorScenario = {
  id: 'david-park-realestate',
  title: 'David Park — Real Estate',
  subtitle: 'Property search, mortgage & inspection',
  description: 'A first-time home buyer in Austin navigating property search, mortgage pre-approval, and inspection issues. Watch cautious decision-making patterns and cross-platform comparison behavior emerge.',
  persona: { name: 'David Park', avatar: 'DP', color: '#22c55e' },
  sessions: realtySessions,
  messages: realtyMessages,
  atlasSnapshots: buildGenericSnapshots(davidPack),
};

// ─── All Scenarios ──────────────────────────────────────────────────────────

export const allScenarios: SimulatorScenario[] = [
  sarahChenScenario,
  marcusRiveraScenario,
  priyaSharmaScenario,
  davidParkScenario,
];
