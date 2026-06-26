import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AddSpeciesForm } from "./AddSpeciesForm";

const mutate = vi.fn();

interface MutationStub {
  mutate: typeof mutate;
  isPending: boolean;
  isError: boolean;
  isSuccess: boolean;
  error: Error | null;
  data:
    | {
        taxon: string;
        realm: string;
        cluster_count: number;
        flagged_records: number;
      }
    | undefined;
}

let stub: MutationStub;

vi.mock("@/lib/queries", () => ({
  useAddReviewTaxon: () => stub,
}));

beforeEach(() => {
  mutate.mockReset();
  stub = {
    mutate,
    isPending: false,
    isError: false,
    isSuccess: false,
    error: null,
    data: undefined,
  };
});

describe("AddSpeciesForm", () => {
  it("submits the trimmed name and the chosen realm", () => {
    render(<AddSpeciesForm />);
    fireEvent.change(
      screen.getByLabelText("Scientific name to add to review"),
      { target: { value: "  Bufo bufo  " } },
    );
    fireEvent.change(screen.getByLabelText("Habitat realm"), {
      target: { value: "marine" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add to review" }));
    expect(mutate).toHaveBeenCalledWith(
      { name: "Bufo bufo", realm: "marine" },
      expect.anything(),
    );
  });

  it("disables the button when the name is blank", () => {
    render(<AddSpeciesForm />);
    expect(
      screen.getByRole("button", { name: "Add to review" }),
    ).toBeDisabled();
  });

  it("shows a pending state while adding", () => {
    stub.isPending = true;
    render(<AddSpeciesForm />);
    expect(screen.getByRole("button", { name: "Adding…" })).toBeDisabled();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("shows the error detail when the add fails", () => {
    stub.isError = true;
    stub.error = new Error("GBIF returned no records for 'Nope nope'.");
    render(<AddSpeciesForm />);
    expect(
      screen.getByText("GBIF returned no records for 'Nope nope'."),
    ).toBeInTheDocument();
  });

  it("reports the new clusters on success", () => {
    stub.isSuccess = true;
    stub.data = {
      taxon: "Bufo bufo",
      realm: "terrestrial",
      cluster_count: 3,
      flagged_records: 12,
    };
    render(<AddSpeciesForm />);
    expect(
      screen.getByText("Added Bufo bufo: 3 clusters from 12 flagged records."),
    ).toBeInTheDocument();
  });
});
