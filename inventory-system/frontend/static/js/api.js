/* Shared API helper -- used by login.js, admin.js, billing.js */
const API = {
  base: "",

  getToken() { return localStorage.getItem("token"); },
  getRole() { return localStorage.getItem("role"); },
  getName() { return localStorage.getItem("name"); },
  getUserId() { return localStorage.getItem("user_id"); },

  logout() {
    localStorage.clear();
    window.location.href = "/";
  },

  async request(method, path, body) {
    const headers = { "Content-Type": "application/json" };
    const token = this.getToken();
    if (token) headers["Authorization"] = "Bearer " + token;

    const res = await fetch(this.base + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (res.status === 401) {
      this.logout();
      throw new Error("Session khatam ho gayi, dobara login karein");
    }

    let data = null;
    try { data = await res.json(); } catch (e) { /* no body */ }

    if (!res.ok) {
      const msg = (data && data.detail) ? data.detail : "Kuch galat ho gaya";
      throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
    return data;
  },

  get(path) { return this.request("GET", path); },
  post(path, body) { return this.request("POST", path, body); },
  patch(path, body) { return this.request("PATCH", path, body); },
  del(path) { return this.request("DELETE", path); },
};

function requireAuth(allowedRoles) {
  const token = API.getToken();
  const role = API.getRole();
  if (!token || !role) {
    window.location.href = "/";
    return false;
  }
  if (allowedRoles && !allowedRoles.includes(role)) {
    window.location.href = role === "admin" ? "/admin" : "/billing";
    return false;
  }
  return true;
}

function showToast(message, type) {
  let el = document.getElementById("toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast";
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.textContent = message;
  el.className = "toast show" + (type ? " toast-" + type : "");
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove("show"), 3200);
}

function formatMoney(n) {
  return "\u20B9" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}
