// Benign url stub for @flind/agent dist bundles loaded in Storybook. The
// tsup banner only derives __filename/__dirname from it, which nothing a
// story renders ever reads.
export function fileURLToPath(url: string | URL): string {
  return String(url).replace(/^file:\/\//, "");
}

export default { fileURLToPath };
