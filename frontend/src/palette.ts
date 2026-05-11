export const TOPIC_COLORS: Record<string, string> = {
  politics: "#e85a4f",
  business: "#4f9fff",
  technology: "#a878ff",
  science: "#3ad29f",
  health: "#ff9a4f",
  sports: "#ffd24f",
  entertainment: "#ff6db5",
  world: "#5fdbff",
  environment: "#6dd47e",
  general: "#7a7a88",
};

export const SOURCE_COLORS = [
  "#ff5876",
  "#4f9fff",
  "#a878ff",
  "#3ad29f",
  "#ff9a4f",
  "#ffd24f",
  "#ff6db5",
  "#5fdbff",
  "#c47fff",
  "#5fffce",
  "#ff4fa3",
  "#4fffae",
];

export function topicColor(category: string): string {
  return TOPIC_COLORS[category.toLowerCase()] ?? TOPIC_COLORS.general;
}

export function sourceColor(index: number): string {
  return SOURCE_COLORS[index % SOURCE_COLORS.length];
}
