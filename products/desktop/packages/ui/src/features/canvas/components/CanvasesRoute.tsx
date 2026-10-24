import { BlueprintIcon } from "@phosphor-icons/react";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@flind/quill";
import { WebsiteDashboard } from "@flind/ui/features/canvas/components/WebsiteDashboard";
import { useSelectedCanvasId } from "@flind/ui/features/canvas/hooks/useSelectedCanvasId";
import { useCanvasViewedStore } from "@flind/ui/features/canvas/stores/canvasViewedStore";
import { OpenSidebarButton } from "@flind/ui/features/sidebar/components/OpenSidebarButton";
import { useEffect } from "react";

export function CanvasesRoute() {
  const canvasId = useSelectedCanvasId();
  const markCanvasViewed = useCanvasViewedStore(
    (state) => state.markCanvasViewed,
  );
  useEffect(() => {
    if (canvasId) markCanvasViewed(canvasId, Date.now());
  }, [canvasId, markCanvasViewed]);

  if (canvasId) return <WebsiteDashboard dashboardId={canvasId} />;
  return (
    <div className="flex h-full items-center justify-center p-6">
      <Empty className="border-0">
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <BlueprintIcon />
          </EmptyMedia>
          <EmptyTitle>Pick a canvas</EmptyTitle>
          <EmptyDescription>
            Choose a canvas from the list to open it here.
          </EmptyDescription>
        </EmptyHeader>
        <EmptyContent>
          <OpenSidebarButton />
        </EmptyContent>
      </Empty>
    </div>
  );
}
