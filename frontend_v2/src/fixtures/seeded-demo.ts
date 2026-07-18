export const seededDemo = {
  id: "seeded",
  profileStatus: "not-created",
  preparationMessage: "The demo starts after sign-in."
} as const;

export type SeededDemo = typeof seededDemo;
