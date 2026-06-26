import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HelpTip } from "./HelpTip";

describe("HelpTip", () => {
  it("toggles the hint on click", () => {
    render(
      <HelpTip label="About scores" text="Higher means more suspicious." />,
    );
    const button = screen.getByRole("button", { name: "About scores" });
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();

    fireEvent.click(button);
    expect(screen.getByRole("tooltip")).toHaveTextContent(
      "Higher means more suspicious.",
    );

    fireEvent.click(button);
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });
});
