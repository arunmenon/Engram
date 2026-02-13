import { ThumbsUp, ThumbsDown, Minus } from 'lucide-react';
import { ConfidenceBar } from '../shared/ConfidenceBar';
import {
  sarahProfile,
  sarahPreferences,
  sarahSkills,
  sarahInterests,
  sarahPatterns,
} from '../../data/mockUserProfile';

const polarityIcons = {
  positive: <ThumbsUp className="w-3.5 h-3.5 text-green-400" />,
  negative: <ThumbsDown className="w-3.5 h-3.5 text-red-400" />,
  neutral: <Minus className="w-3.5 h-3.5 text-gray-500" />,
};

const proficiencyColors: Record<string, string> = {
  Management: 'bg-accent-purple',
  Methodology: 'bg-accent-blue',
};

export function UserTab() {
  return (
    <div className="space-y-5">
      {/* Profile Card */}
      <div>
        <h3 className="text-lg font-semibold text-gray-100">{sarahProfile.name}</h3>
        <div className="flex items-center gap-2 mt-1.5">
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-accent-purple/20 text-accent-purple">
            {sarahProfile.role}
          </span>
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-accent-blue/20 text-accent-blue">
            {sarahProfile.tech_level}
          </span>
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-surface-hover text-muted-light">
            {sarahProfile.communication_style}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-3 text-xs text-muted-light">
          <span>Sessions: <span className="text-gray-200 font-medium">{sarahProfile.session_count}</span></span>
          <span>Interactions: <span className="text-gray-200 font-medium">{sarahProfile.total_interactions}</span></span>
          <span>First seen: <span className="text-gray-200 font-mono text-[10px]">{new Date(sarahProfile.first_seen).toLocaleDateString()}</span></span>
          <span>Last seen: <span className="text-gray-200 font-mono text-[10px]">{new Date(sarahProfile.last_seen).toLocaleDateString()}</span></span>
        </div>
      </div>

      {/* Preferences */}
      <div>
        <h4 className="text-xs font-semibold text-muted-light uppercase tracking-wider mb-2">Preferences</h4>
        <div className="border-t border-muted-dark/30 pt-2 space-y-2.5">
          {sarahPreferences.map(pref => (
            <div key={pref.id} className="space-y-1">
              <div className="flex items-center gap-2">
                {polarityIcons[pref.polarity]}
                <span className="text-sm text-gray-200 flex-1">{pref.value}</span>
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-surface-hover text-muted-light">
                  {pref.category}
                </span>
              </div>
              <ConfidenceBar value={pref.confidence} />
              <p className="text-[10px] text-accent-blue/70">
                Source: {pref.source_event_ids.join(', ')}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Skills */}
      <div>
        <h4 className="text-xs font-semibold text-muted-light uppercase tracking-wider mb-2">Skills</h4>
        <div className="border-t border-muted-dark/30 pt-2 space-y-2.5">
          {sarahSkills.map(skill => (
            <div key={skill.id}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-gray-200">{skill.name}</span>
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-surface-hover text-muted-light">
                  {skill.category}
                </span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-surface-darker overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${proficiencyColors[skill.category] || 'bg-accent-teal'}`}
                  style={{ width: `${skill.proficiency * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Interests */}
      <div>
        <h4 className="text-xs font-semibold text-muted-light uppercase tracking-wider mb-2">Interests</h4>
        <div className="border-t border-muted-dark/30 pt-2 flex flex-wrap gap-1.5">
          {sarahInterests.map(interest => (
            <span
              key={interest.entity_id}
              className="inline-flex items-center px-2 py-1 rounded-lg text-xs font-medium bg-accent-teal/15 text-accent-teal"
              style={{ opacity: 0.4 + interest.weight * 0.6, fontSize: `${11 + interest.weight * 3}px` }}
            >
              {interest.entity_name}
            </span>
          ))}
        </div>
      </div>

      {/* Behavioral Patterns */}
      <div>
        <h4 className="text-xs font-semibold text-muted-light uppercase tracking-wider mb-2">Behavioral Patterns</h4>
        <div className="border-t border-muted-dark/30 pt-2 space-y-2.5">
          {sarahPatterns.map(pattern => (
            <div key={pattern.id} className="p-3 rounded-lg bg-surface-card border border-muted-dark/30">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-gray-200">{pattern.pattern_type}</span>
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-accent-amber/15 text-accent-amber">
                  {pattern.observation_count} obs
                </span>
              </div>
              <p className="text-xs text-muted-light mb-2">{pattern.description}</p>
              <ConfidenceBar value={pattern.confidence} className="mb-2" />
              <ul className="space-y-0.5">
                {pattern.examples.map((ex, i) => (
                  <li key={i} className="text-[10px] text-muted flex items-start gap-1">
                    <span className="text-muted-light mt-0.5">&bull;</span>
                    {ex}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
