import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Button } from "./Button";
import { SuspicionMeter } from "./SuspicionMeter";

describe("Button", () => {
  it("renders its label and handles clicks", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Confirm rule</Button>);
    const button = screen.getByRole("button", { name: "Confirm rule" });
    fireEvent.click(button);
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("applies the secondary outline style", () => {
    render(<Button variant="secondary">Reject</Button>);
    expect(screen.getByRole("button", { name: "Reject" }).className).toContain(
      "border-hairline",
    );
  });

  it("can be disabled", () => {
    render(<Button disabled>Save</Button>);
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });
});

describe("SuspicionMeter", () => {
  it("shows the score as text and an accessible progressbar", () => {
    render(<SuspicionMeter score={0.9} />);
    expect(screen.getByText("0.90")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute(
      "aria-valuenow",
      "90",
    );
  });

  it("clamps out-of-range scores", () => {
    render(<SuspicionMeter score={1.7} />);
    expect(screen.getByText("1.00")).toBeInTheDocument();
  });
});
