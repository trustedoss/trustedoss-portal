/**
 * RFC 7807 Problem Details — shared error type used by every HTTP layer.
 *
 * Originally lived in `lib/authApi.ts` (PR #6 / 1.6, fetch-based). Promoted
 * out so the axios surface in `lib/api.ts` (PR #6 / 1.7) can throw the same
 * shape and the auth pages don't have to learn a second error class.
 *
 * Contract:
 *   - `status === 0` is reserved for transport-level failures (network, CORS,
 *     DNS, aborted). The backend never returns 0.
 *   - `detail` is always populated (falls back to `title`) so the UI can
 *     render `err.detail` without further branching.
 *   - `problem` is the parsed JSON when the server returned `application/
 *     problem+json`; `null` when the body wasn't JSON or the request never
 *     reached the server.
 */

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance?: string;
  /**
   * RFC 7807 §3.2 allows arbitrary "extension members" alongside the standard
   * fields. The backend uses snake_case extension fields to surface domain
   * invariants — e.g. ``last_super_admin_protected: true``,
   * ``cannot_modify_self: true``, ``team_has_active_scans: true``. We carry
   * them through verbatim via an index signature so callers don't have to
   * cast the whole problem to ``Record<string, unknown>`` to read one field.
   */
  [extension: string]: unknown;
}

export class ProblemError extends Error {
  readonly status: number;
  readonly title: string;
  readonly detail: string;
  readonly problem: ProblemDetails | null;

  constructor(
    message: string,
    options: {
      status: number;
      title: string;
      detail: string;
      problem: ProblemDetails | null;
    },
  ) {
    super(message);
    this.name = "ProblemError";
    this.status = options.status;
    this.title = options.title;
    this.detail = options.detail;
    this.problem = options.problem;
  }
}

/**
 * Parse an arbitrary JSON-ish body into a {@link ProblemDetails} when the
 * shape matches RFC 7807. Returns null if the body isn't an object.
 *
 * Used by both the fetch-based legacy path (`lib/authApi.ts`) and the axios
 * response interceptor (`lib/api.ts`).
 */
export function parseProblemBody(
  data: unknown,
  fallback: { status: number; statusText?: string },
): { problem: ProblemDetails | null; title: string; detail: string } {
  let title = fallback.statusText || `HTTP ${fallback.status}`;
  let detail = "";
  let problem: ProblemDetails | null = null;
  if (data && typeof data === "object") {
    const obj = data as Record<string, unknown>;
    if (typeof obj.title === "string") title = obj.title;
    if (typeof obj.detail === "string") detail = obj.detail;
    // Carry RFC 7807 extension members (e.g. snake_case domain flags) through
    // verbatim. The standard fields are normalized below; everything else is
    // copied as-is so callers can read ``problem.cannot_modify_self`` etc.
    const RESERVED = new Set(["type", "title", "status", "detail", "instance"]);
    const extensions: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(obj)) {
      if (!RESERVED.has(key)) extensions[key] = value;
    }
    problem = {
      ...extensions,
      type: typeof obj.type === "string" ? obj.type : "about:blank",
      title,
      status: typeof obj.status === "number" ? obj.status : fallback.status,
      detail: detail || title,
      instance: typeof obj.instance === "string" ? obj.instance : undefined,
    };
  }
  return { problem, title, detail: detail || title };
}
