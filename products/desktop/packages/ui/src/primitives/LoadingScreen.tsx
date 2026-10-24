import { cn } from "@flind/quill";
import { AnimatedLogo } from "@flind/ui/primitives/AnimatedLogo";

interface LoadingScreenProps {
  logoSize?: number;
  className?: string;
}

export function LoadingScreen({
  logoSize = 72,
  className,
}: LoadingScreenProps) {
  return (
    <div
      className={cn(
        "flex h-full w-full items-center justify-center bg-(--color-background)",
        className,
      )}
    >
      <AnimatedLogo size={logoSize} data-testid="app-loading-logo" />
    </div>
  );
}
