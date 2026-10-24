import type { FileDiffProps, MultiFileDiffProps } from "@pierre/diffs/react";
import type {
  AnnotationMetadata,
  PrCommentThread,
} from "@flind/core/code-review/types";

export type {
  AnnotationMetadata,
  DiffOptions,
  PrCommentMetadata,
} from "@flind/core/code-review/types";

interface PrCommentProps {
  taskId?: string;
  prUrl?: string | null;
  commentThreads?: Map<number, PrCommentThread>;
}

export type PatchDiffProps = FileDiffProps<AnnotationMetadata> &
  PrCommentProps & {
    repoPath?: string;
    skipExpansion?: boolean;
  };

export type FilesDiffProps = MultiFileDiffProps<AnnotationMetadata> &
  PrCommentProps;

export type InteractiveFileDiffProps = PatchDiffProps | FilesDiffProps;
