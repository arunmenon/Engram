import { GraphVisualization } from './GraphVisualization';
import { GraphControls } from './GraphControls';
import { GraphLegend } from './GraphLegend';

export function GraphPanel() {
  return (
    <div className="flex-1 min-w-[500px] min-h-[400px] relative overflow-hidden">
      <GraphVisualization />
      <GraphControls />
      <GraphLegend />
    </div>
  );
}
