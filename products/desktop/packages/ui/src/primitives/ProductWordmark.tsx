import { Text } from "@flind/quill";
import Logo from "@flind/ui/primitives/Logo";

/**
 * The hedgehog mark beside the product name. Logo's own wordmark is brand
 * lettering inside the SVG, so setting only part of the name as text cannot
 * match it. The whole name is text instead.
 */
export function ProductWordmark() {
  return (
    <div className="flex items-center gap-2">
      <span className="flex [&>svg]:h-[18px] [&>svg]:w-auto">
        <Logo wordmark={false} />
      </span>
      <Text className="font-bold text-foreground text-md leading-none tracking-[-0.05em]">
        Flind Desktop
      </Text>
    </div>
  );
}
