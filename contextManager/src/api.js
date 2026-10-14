// localhost (not 127.0.0.1) keeps the backend same-site with the Vite page, so auth cookies are sent
export const API_URL = "http://localhost:5000";

export async function api(path, { method = "GET", body } = {}) {
  const res = await fetch(API_URL + path, {
    method,
    credentials: "include",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}
