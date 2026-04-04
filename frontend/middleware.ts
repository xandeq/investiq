import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Protected paths — require access_token cookie to be present
const PROTECTED_PATHS = ["/dashboard", "/portfolio", "/analysis", "/stock"];
const PUBLIC_PATHS = [
  "/login",
  "/register",
  "/verify-email",
  "/forgot-password",
  "/reset-password",
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isProtected = PROTECTED_PATHS.some((p) => pathname.startsWith(p));

  // Security note on CVE-2025-29927:
  // Middleware-only auth is insufficient — Next.js 15 mitigates CVE-2025-29927
  // but defense-in-depth requires Server Components to also validate.
  // The middleware handles the redirect UX; actual token validity is enforced
  // by the FastAPI backend on every API call.
  // Use Next.js >= 15.2.3 which patches the middleware bypass vulnerability.

  if (isProtected) {
    const accessToken = request.cookies.get("access_token")?.value;
    if (!accessToken) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api/).*)"],
};
