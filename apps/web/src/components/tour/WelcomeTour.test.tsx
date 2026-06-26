import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { startSiteTour } from "@/lib/tour";

import { WelcomeTour } from "./WelcomeTour";

vi.mock("@/lib/tour", () => ({ startSiteTour: vi.fn() }));

const SEEN_KEY = "taxonguard.tour.seen";

describe("WelcomeTour", () => {
  beforeEach(() => {
    vi.mocked(startSiteTour).mockReset();
    window.localStorage.clear();
    window.history.replaceState(null, "", "/");
  });

  it("offers the tour on a first visit", () => {
    render(<WelcomeTour />);
    expect(
      screen.getByRole("button", { name: "Take the tour" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Skip tour" }),
    ).toBeInTheDocument();
  });

  it("starts the tour and remembers the visit when taken", () => {
    render(<WelcomeTour />);
    fireEvent.click(screen.getByRole("button", { name: "Take the tour" }));
    expect(startSiteTour).toHaveBeenCalledTimes(1);
    expect(window.localStorage.getItem(SEEN_KEY)).toBe("1");
    expect(
      screen.queryByRole("button", { name: "Take the tour" }),
    ).not.toBeInTheDocument();
  });

  it("remembers the visit when skipped", () => {
    render(<WelcomeTour />);
    fireEvent.click(screen.getByRole("button", { name: "Skip tour" }));
    expect(startSiteTour).not.toHaveBeenCalled();
    expect(window.localStorage.getItem(SEEN_KEY)).toBe("1");
    expect(
      screen.queryByRole("button", { name: "Take the tour" }),
    ).not.toBeInTheDocument();
  });

  it("does not show the card on a later visit", () => {
    window.localStorage.setItem(SEEN_KEY, "1");
    render(<WelcomeTour />);
    expect(
      screen.queryByRole("button", { name: "Take the tour" }),
    ).not.toBeInTheDocument();
  });
});
