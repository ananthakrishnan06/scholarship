import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Source } from "./components";
import Dashboard from "./Dashboard";
import Assistant from "./Assistant";
import { api } from "./api";
vi.mock("./api", () => ({ api: vi.fn() }));
const citation = {
  scheme_id: "pragati",
  scheme_name: "Pragati Scholarship",
  source_name: null,
  source_url: null,
  retrieved_from: "pragati:benefits:0",
};
beforeEach(() => {
  sessionStorage.clear();
  vi.mocked(api).mockReset();
});
describe("sources and immediate assistant access", () => {
  it("shows the relevant scholarship name and preserves missing URLs", () => {
    render(<Source citation={citation} />);
    expect(screen.getByText("Pragati Scholarship")).toBeInTheDocument();
    expect(
      screen.getByText("Official source link unavailable in dataset"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "View Full Scheme" }),
    ).toHaveAttribute("href", "#/scholarships/pragati");
    expect(
      screen.queryByRole("link", { name: "Official source" }),
    ).not.toBeInTheDocument();
  });
  it("rejects unsafe source URL protocols", () => {
    render(
      <Source citation={{ ...citation, source_url: "javascript:alert(1)" }} />,
    );
    expect(
      screen.getByRole("link", { name: "View Full Scheme" }),
    ).toHaveAttribute("href", "#/scholarships/pragati");
    expect(
      screen.queryByRole("link", { name: "Official source" }),
    ).not.toBeInTheDocument();
  });
  it("allows ordinary official source links", () => {
    render(
      <Source
        citation={{
          ...citation,
          source_url: "https://example.org/scholarship",
        }}
      />,
    );
    expect(
      screen.getByRole("link", { name: "Official source" }),
    ).toHaveAttribute("href", "https://example.org/scholarship");
  });
  it("opens scholarship questions without a profile workflow", () => {
    render(<Dashboard schemes={[]} />);
    expect(
      screen.getByRole("button", { name: /Ask about scholarships/ }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Build my profile")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Confirmed rule matches"),
    ).not.toBeInTheDocument();
  });
  it("renders actual generated prose and sends no profile", async () => {
    vi.mocked(api).mockResolvedValueOnce({
      session_id: "session",
      session_token: "token",
    });
    vi.mocked(api).mockResolvedValueOnce({
      answer: "Pragati can help cover your education costs.",
      status: "success",
      sources: [citation, citation],
    });
    render(<Assistant />);
    fireEvent.change(screen.getByLabelText("Ask a scholarship question"), {
      target: { value: "Tell me about Pragati" },
    });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /Send/ })).toBeEnabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: /Send/ }));
    expect(
      await screen.findByText("Pragati can help cover your education costs."),
    ).toBeInTheDocument();
    expect(screen.getByText("Sources (1)")).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", { name: "View Full Scheme" }),
    ).toHaveLength(1);
    const sent = vi.mocked(api).mock.calls[1][1] as Record<string, unknown>;
    expect(sent).toEqual({
      question: "Tell me about Pragati",
      session_id: "session",
    });
  });
  it("shows provider failures clearly instead of fake AI excerpts", async () => {
    vi.mocked(api).mockResolvedValueOnce({
      session_id: "session",
      session_token: "token",
    });
    vi.mocked(api).mockRejectedValueOnce(
      new Error("Provider quota reached. Please try again."),
    );
    render(<Assistant />);
    fireEvent.change(screen.getByLabelText("Ask a scholarship question"), {
      target: { value: "Pragati?" },
    });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /Send/ })).toBeEnabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: /Send/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Provider quota reached",
    );
    expect(
      screen.queryByText("Showing verified dataset excerpts."),
    ).not.toBeInTheDocument();
  });
  it("passes selected scholarship context without forcing a hard filter", async () => {
    vi.mocked(api).mockResolvedValueOnce({
      session_id: "session",
      session_token: "token",
    });
    vi.mocked(api).mockResolvedValueOnce({
      answer: "The available criteria are explained here.",
      status: "success",
      sources: [citation],
    });
    render(<Assistant schemeId="selected-scholarship" />);
    fireEvent.change(screen.getByLabelText("Ask a scholarship question"), {
      target: { value: "Who is eligible?" },
    });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /Send/ })).toBeEnabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: /Send/ }));
    await screen.findByText("The available criteria are explained here.");
    expect(vi.mocked(api).mock.calls[1][1]).toEqual({
      question: "Who is eligible?",
      session_id: "session",
      context_scheme_id: "selected-scholarship",
    });
  });
});
