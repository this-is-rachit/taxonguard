import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import About from "./page";

describe("About page", () => {
  it("renders the page heading", () => {
    render(<About />);
    expect(
      screen.getByRole("heading", { name: "How TaxonGuard works", level: 1 }),
    ).toBeInTheDocument();
  });
});
