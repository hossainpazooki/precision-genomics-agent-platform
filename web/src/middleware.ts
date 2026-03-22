import { NextRequest, NextResponse } from "next/server";
import { jwtVerify } from "jose";

const SKIP_PATHS = new Set([
  "/api/health",
  "/api",
  "/_next",
  "/favicon.ico",
]);

const API_KEY_HEADER = "x-api-key";
const AUTH_HEADER = "authorization";

export async function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;

  // Skip auth for non-API routes and health checks
  if (!path.startsWith("/api") || SKIP_PATHS.has(path)) {
    return addAuditHeaders(request, NextResponse.next());
  }

  const requireAuth = process.env.REQUIRE_AUTH === "true";
  if (!requireAuth) {
    return addAuditHeaders(request, NextResponse.next());
  }

  // Try API key first
  const apiKey = request.headers.get(API_KEY_HEADER);
  if (apiKey) {
    const validKeys = parseApiKeys(process.env.API_KEYS);
    if (validKeys.has(apiKey)) {
      return addAuditHeaders(request, NextResponse.next());
    }
    return NextResponse.json({ detail: "Invalid API key" }, { status: 403 });
  }

  // Try JWT
  const authHeader = request.headers.get(AUTH_HEADER);
  if (authHeader?.startsWith("Bearer ")) {
    const token = authHeader.slice(7);
    const jwtSecret = process.env.JWT_SECRET;
    if (!jwtSecret) {
      return NextResponse.json(
        { detail: "JWT not configured" },
        { status: 500 },
      );
    }
    try {
      const secret = new TextEncoder().encode(jwtSecret);
      await jwtVerify(token, secret);
      return addAuditHeaders(request, NextResponse.next());
    } catch {
      return NextResponse.json({ detail: "Invalid token" }, { status: 401 });
    }
  }

  return NextResponse.json({ detail: "Missing API key" }, { status: 401 });
}

function parseApiKeys(keys: string | undefined): Set<string> {
  if (!keys) return new Set();
  return new Set(
    keys
      .split(",")
      .map((k) => k.trim())
      .filter(Boolean),
  );
}

function addAuditHeaders(
  request: NextRequest,
  response: NextResponse,
): NextResponse {
  // Audit logging via response headers
  response.headers.set("x-request-id", crypto.randomUUID());
  response.headers.set("x-request-path", request.nextUrl.pathname);
  response.headers.set("x-request-method", request.method);
  return response;
}

export const config = {
  matcher: ["/api/:path*"],
};
