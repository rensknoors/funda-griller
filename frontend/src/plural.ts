/** "1 feit", "3 feiten": Dutch counts in UI copy. */
export function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}
