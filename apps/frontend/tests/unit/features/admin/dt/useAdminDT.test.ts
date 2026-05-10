/**
 * Hook-level smoke tests — query-key stability + axios glue.
 *
 * The pages exercise `useAdminDT*` end-to-end; this file directly invokes
 * the api functions against a mocked `api` instance to keep the wire-shape
 * pinned and lift the coverage on the bare API module so future refactors
 * cannot silently change the URL or the body shape.
 */
import { describe, expect, it, vi } from "vitest";

import {
  cleanupDTOrphans,
  forceDTHealthCheck,
  getDTStatus,
  listDTOrphans,
  resetDTBreaker,
} from "@/features/admin/dt/api/adminDTApi";
import {
  dtOrphansQueryKey,
  dtStatusQueryKey,
} from "@/features/admin/dt/api/useAdminDT";
import { api } from "@/lib/api";

describe("admin DT api glue", () => {
  it("getDTStatus issues GET /v1/admin/dt/status", async () => {
    const spy = vi
      .spyOn(api, "get")
      .mockResolvedValueOnce({ data: { state: "closed" } } as never);
    await getDTStatus();
    expect(spy).toHaveBeenCalledWith("/v1/admin/dt/status");
    spy.mockRestore();
  });

  it("listDTOrphans forwards the limit/offset params", async () => {
    const spy = vi
      .spyOn(api, "get")
      .mockResolvedValueOnce({ data: { items: [], total: 0, has_more: false } } as never);
    await listDTOrphans({ limit: 100, offset: 25 });
    expect(spy).toHaveBeenCalledWith("/v1/admin/dt/orphans", {
      params: { limit: 100, offset: 25 },
    });
    spy.mockRestore();
  });

  it("cleanupDTOrphans defaults to an empty uuid list when omitted", async () => {
    const spy = vi
      .spyOn(api, "post")
      .mockResolvedValueOnce({ data: { task_id: "x" } } as never);
    await cleanupDTOrphans();
    expect(spy).toHaveBeenCalledWith("/v1/admin/dt/orphans/cleanup", {
      dt_project_uuids: [],
    });
    spy.mockRestore();
  });

  it("cleanupDTOrphans forwards the requested uuid list", async () => {
    const spy = vi
      .spyOn(api, "post")
      .mockResolvedValueOnce({ data: { task_id: "x" } } as never);
    await cleanupDTOrphans({ dt_project_uuids: ["u1", "u2"] });
    expect(spy).toHaveBeenCalledWith("/v1/admin/dt/orphans/cleanup", {
      dt_project_uuids: ["u1", "u2"],
    });
    spy.mockRestore();
  });

  it("forceDTHealthCheck issues POST /v1/admin/dt/health-check", async () => {
    const spy = vi
      .spyOn(api, "post")
      .mockResolvedValueOnce({ data: { healthy: true } } as never);
    await forceDTHealthCheck();
    expect(spy).toHaveBeenCalledWith("/v1/admin/dt/health-check");
    spy.mockRestore();
  });

  it("resetDTBreaker issues POST /v1/admin/dt/breaker/reset (A4)", async () => {
    const spy = vi
      .spyOn(api, "post")
      .mockResolvedValueOnce({
        data: {
          state_before: "open",
          state_after: "closed",
          fail_count_before: 5,
          reset_at: "2026-05-10T12:00:00Z",
        },
      } as never);
    const result = await resetDTBreaker();
    expect(spy).toHaveBeenCalledWith("/v1/admin/dt/breaker/reset");
    expect(result.state_before).toBe("open");
    expect(result.state_after).toBe("closed");
    expect(result.fail_count_before).toBe(5);
    spy.mockRestore();
  });

  it("query keys roundtrip the params with stable defaults", () => {
    expect(dtStatusQueryKey()).toEqual(["admin", "dt", "status"]);
    expect(dtOrphansQueryKey({})).toEqual([
      "admin",
      "dt",
      "orphans",
      { limit: 50, offset: 0 },
    ]);
    expect(dtOrphansQueryKey({ limit: 25, offset: 10 })).toEqual([
      "admin",
      "dt",
      "orphans",
      { limit: 25, offset: 10 },
    ]);
  });
});
