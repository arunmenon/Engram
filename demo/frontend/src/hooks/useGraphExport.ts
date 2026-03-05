import { useCallback } from 'react';
import { useGraphStore } from '../stores/graphStore';

export function useGraphExport() {
  const sigmaRenderer = useGraphStore((s) => s.sigmaRenderer);

  const exportGraphAsPng = useCallback(() => {
    if (!sigmaRenderer) return;

    const container = sigmaRenderer.getContainer();
    const canvases = container.querySelectorAll('canvas');
    if (canvases.length === 0) return;

    const width = canvases[0].width;
    const height = canvases[0].height;

    const composite = document.createElement('canvas');
    composite.width = width;
    composite.height = height;
    const ctx = composite.getContext('2d');
    if (!ctx) return;

    ctx.fillStyle = '#0a0a0c';
    ctx.fillRect(0, 0, width, height);

    for (const canvas of canvases) {
      ctx.drawImage(canvas, 0, 0);
    }

    composite.toBlob((blob) => {
      if (!blob) return;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `engram-graph-${Date.now()}.png`;
      a.click();
      URL.revokeObjectURL(url);
    }, 'image/png');
  }, [sigmaRenderer]);

  return { exportGraphAsPng };
}
