import { render } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { Home } from "@/pages/Home";

describe("Home", () => {
  it("redirects from / to /projects", () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route
            path="/projects"
            element={<div data-testid="projects-page">projects</div>}
          />
        </Routes>
      </MemoryRouter>,
    );
    expect(container.querySelector('[data-testid="projects-page"]')).not.toBeNull();
  });
});
