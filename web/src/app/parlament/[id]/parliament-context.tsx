"use client";

import { createContext, useContext } from "react";

const ParliamentIdContext = createContext<string | null>(null);

export function ParliamentIdProvider({
  parliamentId,
  children,
}: {
  parliamentId: string;
  children: React.ReactNode;
}) {
  return (
    <ParliamentIdContext.Provider value={parliamentId}>
      {children}
    </ParliamentIdContext.Provider>
  );
}

export function useParliamentId(): string {
  const id = useContext(ParliamentIdContext);
  if (!id) {
    throw new Error("useParliamentId muss unter ParliamentIdProvider liegen");
  }
  return id;
}
