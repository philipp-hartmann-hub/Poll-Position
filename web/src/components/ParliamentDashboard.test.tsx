import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ParliamentDashboard } from "./ParliamentDashboard";

vi.mock("@/components/charts", () => ({
  Hemicycle: () => <div data-testid="hemicycle" />,
  PollAndSwingAlignedCharts: () => <div data-testid="aligned-charts" />,
  PollShareBarChart: () => <div data-testid="poll-bars" />,
}));

vi.mock("@/components/CoalitionsSection", () => ({
  CoalitionsSection: () => null,
}));
vi.mock("@/components/CoalitionCheckerSection", () => ({
  CoalitionCheckerSection: () => null,
}));
vi.mock("@/components/DataFreshnessBanner", () => ({
  DataFreshnessBanner: () => null,
}));
vi.mock("@/components/ElectionNightSection", () => ({
  ElectionNightSection: () => null,
}));
vi.mock("@/components/LastElectionSection", () => ({
  LastElectionSection: () => null,
}));
vi.mock("@/components/PartyForecast", () => ({
  PartyForecast: () => null,
}));
vi.mock("@/components/SurveysSection", () => ({
  SurveysSection: () => null,
}));
vi.mock("@/components/InfoTooltip", () => ({
  InfoTooltip: () => null,
}));

const {
  fetchLastElection,
  fetchSeats,
  fetchAverages,
  fetchGovernment,
  fetchBundesratStatus,
  fetchReelectionProbability,
} = vi.hoisted(() => ({
  fetchLastElection: vi.fn(),
  fetchSeats: vi.fn(),
  fetchAverages: vi.fn(),
  fetchGovernment: vi.fn(),
  fetchBundesratStatus: vi.fn(),
  fetchReelectionProbability: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  fetchLastElection,
  fetchSeats,
  fetchAverages,
  fetchGovernment,
  fetchBundesratStatus,
  fetchReelectionProbability,
}));

vi.mock("@/lib/parliamentCache", async () => {
  const actual = await vi.importActual<typeof import("@/lib/parliamentCache")>(
    "@/lib/parliamentCache",
  );
  return {
    ...actual,
    readOverviewCache: () => null,
    writeOverviewCache: () => undefined,
    canUseStorage: () => false,
  };
});

describe("ParliamentDashboard overview loading", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("rendert Sitze/Umfragen sofort, auch wenn Wiederwahl-Fetch verzögert ist", async () => {
    let resolveReelect!: (v: {
      probability: number | null;
      missingParties: string[];
    }) => void;
    const reelectPromise = new Promise<{
      probability: number | null;
      missingParties: string[];
    }>((resolve) => {
      resolveReelect = resolve;
    });

    fetchLastElection.mockResolvedValue({
      parliament_id: "de_bundestag",
      election_date: "2025-02-23",
      label: "BTW 2025",
      source: "",
      seats: {},
      seats_by_name: { "CDU/CSU": 208, SPD: 120 },
      vote_share_by_name: { "CDU/CSU": 28.52, SPD: 16.4 },
      total_seats: 630,
    });
    fetchSeats.mockResolvedValue({
      parliament_id: "de_bundestag",
      seats: { "de:cdu_csu": 200 },
      seats_by_name: { "CDU/CSU": 200, SPD: 100 },
      total_seats: 630,
      reason: null,
    });
    fetchAverages.mockResolvedValue({
      parliament_id: "de_bundestag",
      as_of: "2026-10-01",
      parties: [
        {
          parliament_id: "de_bundestag",
          party_id: "de:cdu_csu",
          party_name: "CDU/CSU",
          average_share: 30,
          n_polls: 5,
        },
      ],
    });
    fetchGovernment.mockResolvedValue({
      bundesregierung: {
        label: "Schwarz-Rot",
        parties: ["de:cdu_csu", "de:spd"],
      },
    });
    fetchBundesratStatus.mockResolvedValue({ laender: [] });
    fetchReelectionProbability.mockReturnValue(reelectPromise);

    render(<ParliamentDashboard parliamentId="de_bundestag" />);

    await waitFor(() => {
      expect(screen.queryByText("Lade Übersicht…")).not.toBeInTheDocument();
    });

    expect(screen.getByTestId("aligned-charts")).toBeInTheDocument();
    expect(screen.getByTestId("hemicycle")).toBeInTheDocument();
    expect(screen.getByText("Schwarz-Rot")).toBeInTheDocument();
    expect(
      screen.getByLabelText("Lade Wiederwahl-Schätzung"),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Wahrscheinlichkeit der Wiederwahl/)).toBeNull();

    resolveReelect({ probability: 0.42, missingParties: [] });

    await waitFor(() => {
      expect(screen.getByText("42 %")).toBeInTheDocument();
    });
    expect(
      screen.queryByLabelText("Lade Wiederwahl-Schätzung"),
    ).not.toBeInTheDocument();
  });

  it("blockiert die Übersicht nicht, wenn Wiederwahl-Fetch fehlschlägt", async () => {
    fetchLastElection.mockResolvedValue(null);
    fetchSeats.mockResolvedValue({
      parliament_id: "de_bundestag",
      seats: {},
      seats_by_name: { SPD: 100 },
      total_seats: 630,
      reason: null,
    });
    fetchAverages.mockResolvedValue({
      parliament_id: "de_bundestag",
      as_of: null,
      parties: [
        {
          parliament_id: "de_bundestag",
          party_id: "de:spd",
          party_name: "SPD",
          average_share: 20,
          n_polls: 3,
        },
      ],
    });
    fetchGovernment.mockResolvedValue({
      bundesregierung: { label: "Test-Koalition", parties: ["de:spd"] },
    });
    fetchBundesratStatus.mockResolvedValue({ laender: [] });
    fetchReelectionProbability.mockRejectedValue(new Error("timeout"));

    render(<ParliamentDashboard parliamentId="de_bundestag" />);

    await waitFor(() => {
      expect(screen.queryByText("Lade Übersicht…")).not.toBeInTheDocument();
    });
    expect(screen.getByTestId("poll-bars")).toBeInTheDocument();
    expect(screen.getByText("Test-Koalition")).toBeInTheDocument();
    await waitFor(() => {
      expect(
        screen.queryByLabelText("Lade Wiederwahl-Schätzung"),
      ).not.toBeInTheDocument();
    });
  });
});
