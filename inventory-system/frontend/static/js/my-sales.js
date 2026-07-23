requireAuth(["admin", "employee"]);
const myId = API.getUserId();
document.getElementById("empName").textContent = API.getName();
document.getElementById("empRole").textContent = API.getRole() === "admin" ? "Admin" : "Employee";
document.getElementById("avatarInitial").textContent = (API.getName() || "?").trim().charAt(0).toUpperCase();

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

async function loadProfile() {
  try {
    const profile = await API.get(`/api/employees/${myId}/profile`);
    document.getElementById("statTodaySales").textContent = formatMoney(profile.today_sales);
    document.getElementById("statTodayCommission").textContent = formatMoney(profile.today_commission);
    document.getElementById("statTodayBills").textContent = profile.today_bills;
  } catch (err) {
    showToast(err.message, "danger");
  }
}

async function loadHistory() {
  try {
    const history = await API.get(`/api/employees/${myId}/sales-history`);
    const list = document.getElementById("historyList");
    document.getElementById("historyEmpty").style.display = history.length ? "none" : "block";
    list.innerHTML = history.map(h => `
      <div class="card history-item">
        <div>
          <div class="date">${formatDate(h.date)}</div>
          <div class="meta">${h.bills} bill${h.bills === 1 ? "" : "s"}</div>
        </div>
        <div class="amount">
          <div class="num">${formatMoney(h.sales)}</div>
          <span class="commission num">+${formatMoney(h.commission)} commission</span>
        </div>
      </div>
    `).join("");
  } catch (err) {
    showToast(err.message, "danger");
  }
}

async function searchByDate() {
  const date = document.getElementById("searchDate").value;
  if (!date) { showToast("Pick a date first", "danger"); return; }
  try {
    const txns = await API.get(`/api/employees/${myId}/transactions?date=${date}`);
    const container = document.getElementById("dateResults");
    if (txns.length === 0) {
      container.innerHTML = `<div class="empty-state">No bills on ${formatDate(date)}.</div>`;
      return;
    }
    const totalSales = txns.reduce((s, t) => s + t.total_amount, 0);
    const totalCommission = txns.reduce((s, t) => s + t.total_commission, 0);
    container.innerHTML = `
      <div class="card" style="padding:14px;margin-bottom:10px">
        <strong>${formatDate(date)}</strong> — ${txns.length} bill${txns.length === 1 ? "" : "s"},
        ${formatMoney(totalSales)} sales, ${formatMoney(totalCommission)} commission
      </div>
      ${txns.map(t => `
        <div class="card bill-detail-item">
          <div class="top"><span>Bill #${t.id}${t.customer_name ? " · " + escapeHtml(t.customer_name) : ""}</span><span class="num">${formatMoney(t.total_amount)}</span></div>
          <div class="sub">${new Date(t.created_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })} · ${t.payment_method.toUpperCase()} · ${t.items.length} item${t.items.length === 1 ? "" : "s"}</div>
        </div>
      `).join("")}
    `;
  } catch (err) {
    showToast(err.message, "danger");
  }
}

function clearSearch() {
  document.getElementById("searchDate").value = "";
  document.getElementById("dateResults").innerHTML = "";
}

function formatDate(isoDate) {
  const d = new Date(isoDate + "T00:00:00");
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

loadProfile();
loadHistory();
