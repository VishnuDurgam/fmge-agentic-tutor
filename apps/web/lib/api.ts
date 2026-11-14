export const BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").trim().replace(/\/+$/, "");

export function learnerId(): string {
  if (typeof window === "undefined") return "";
  let id = localStorage.getItem("fmge_learner");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("fmge_learner", id);
  }
  return id;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(BASE + path, {
    ...init,
    headers: { ...(init.body instanceof FormData ? {} : { "Content-Type": "application/json" }), "X-Learner-Id": learnerId(), "X-Access-Code": typeof window === "undefined" ? "" : localStorage.getItem("fmge_code") || "", ...(init.headers || {}) },
  });
  if (!res.ok) throw new Error((await res.text()) || res.statusText);
  return res.json();
}
