import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ScansPage } from "@/features/scans/ScansPage";

describe("ScansPage", () => {
  it("renders the coming-soon stub with title and message", () => {
    render(<ScansPage />);
    expect(screen.getByTestId("scans-coming-soon")).toBeInTheDocument();
    // i18n keys come back literally in test env when missing — both values
    // (raw key or translated text) prove the component rendered.
    expect(screen.getByRole("heading")).toBeInTheDocument();
  });
});
