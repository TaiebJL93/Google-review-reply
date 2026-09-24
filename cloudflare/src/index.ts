import { Container, getContainer } from "@cloudflare/containers";
import { env as workerEnv } from "cloudflare:workers";

interface Env {
  APP: DurableObjectNamespace<ReviewReplyApp>;
  SECURE_COOKIES: string;
  GEMINI_API_KEY: string;
  DATABASE_URL: string;
  SECRET_KEY: string;
  GOOGLE_CLIENT_ID?: string;
  GOOGLE_CLIENT_SECRET?: string;
  GOOGLE_REDIRECT_URI?: string;
}

const env = workerEnv as unknown as Env;

/** The FastAPI app from the repo-root Dockerfile, listening on port 8000. */
export class ReviewReplyApp extends Container<Env> {
  defaultPort = 8000;
  // Stop after 15 idle minutes to stay within the plan's included usage.
  // The next visit cold-starts it again (a few seconds).
  sleepAfter = "15m";
  // Handed to the container as environment variables; app/config.py reads them.
  envVars = {
    SECURE_COOKIES: env.SECURE_COOKIES,
    GEMINI_API_KEY: env.GEMINI_API_KEY,
    DATABASE_URL: env.DATABASE_URL,
    SECRET_KEY: env.SECRET_KEY,
    GOOGLE_CLIENT_ID: env.GOOGLE_CLIENT_ID ?? "",
    GOOGLE_CLIENT_SECRET: env.GOOGLE_CLIENT_SECRET ?? "",
    GOOGLE_REDIRECT_URI: env.GOOGLE_REDIRECT_URI ?? "",
  };
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    // Visitors always reach the Worker over HTTPS; tell uvicorn (--proxy-headers).
    const forwarded = new Request(request);
    forwarded.headers.set("X-Forwarded-Proto", "https");
    // A single named instance, so every visitor hits the same running app.
    return getContainer(env.APP, "main").fetch(forwarded);
  },
};
