import {
  BreadcrumbSegment,
  BreadcrumbSeparator,
} from "@flind/ui/primitives/Breadcrumb";
import { LoopIcon } from "@flind/ui/primitives/LoopIcon";
import { navigateToLoops } from "@flind/ui/router/navigationBridge";

export function LoopHeaderTitle({ label }: { label: string }) {
  return (
    <div className="flex w-full min-w-0 items-center gap-0.5">
      <BreadcrumbSegment
        icon={<LoopIcon size={12} className="shrink-0 text-gray-10" />}
        label="Loops"
        strong
        onClick={() => navigateToLoops()}
      />
      <BreadcrumbSeparator />
      <BreadcrumbSegment label={label} />
    </div>
  );
}
