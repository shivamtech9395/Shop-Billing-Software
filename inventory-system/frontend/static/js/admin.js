requireAuth(["admin"]);
document.getElementById("userName").textContent = API.getName();

const TAB_TITLES = {
  dashboard: ["Dashboard", "Today's overview"],
  products: ["Products", "Manage inventory and print QR labels"],
  employees: ["Employees", "Create staff logins and view their activity"],
  transactions: ["Bills", "Search and review every bill created"],
  reports: ["Reports", "Full record of sales, commission and stock"],
};

document.querySelectorAll(".nav-item[data-tab]").forEach((el) => {
  el.addEventListener("click", () => switchTab(el.dataset.tab));
});

function switchTab(tab) {
  document.querySelectorAll(".nav-item[data-tab]").forEach((el) => el.classList.toggle("active", el.dataset.tab === tab));
  document.querySelectorAll(".tab-panel").forEach((el) => el.classList.remove("active"));
  document.getElementById("tab-" + tab).classList.add("active");
  document.getElementById("pageTitle").textContent = TAB_TITLES[tab][0];
  document.getElementById("pageSub").textContent = TAB_TITLES[tab][1];

  if (tab === "dashboard") loadDashboard();
  if (tab === "products") loadProducts();
  if (tab === "employees") loadEmployees();
  if (tab === "transactions") loadTransactions();
  if (tab === "reports") loadReports();
}

// ============================================================
// DASHBOARD
// ============================================================
async function loadDashboard() {
  try {
    const [summary, lowStock, empSales, trending] = await Promise.all([
      API.get("/api/reports/daily-summary"),
      API.get("/api/reports/low-stock"),
      API.get("/api/reports/employee-sales?days=1"),
      API.get("/api/reports/product-sales?days=1"),
    ]);

    document.getElementById("statGrid").innerHTML = `
      <div class="card stat-card"><div class="label">Aaj ki Sales</div><div class="value num">${formatMoney(summary.total_sales)}</div></div>
      <div class="card stat-card"><div class="label">Aaj ke Bills</div><div class="value num">${summary.total_transactions}</div></div>
      <div class="card stat-card"><div class="label">Commission (aaj)</div><div class="value num">${formatMoney(summary.total_commission)}</div></div>
      <div class="card stat-card ${lowStock.length ? "warn" : ""}"><div class="label">Low Stock Items</div><div class="value num">${lowStock.length}</div></div>
    `;

    const lsBody = document.querySelector("#lowStockTable tbody");
    lsBody.innerHTML = lowStock.map(p => `
      <tr><td>${escapeHtml(p.name)}</td><td class="num">${p.quantity}</td><td class="num">${p.threshold}</td></tr>
    `).join("");
    document.getElementById("lowStockEmpty").style.display = lowStock.length ? "none" : "block";

    const esBody = document.querySelector("#empSalesTable tbody");
    esBody.innerHTML = empSales.map(e => `
      <tr><td>${escapeHtml(e.name)}</td><td class="num">${e.num_transactions}</td><td class="num">${formatMoney(e.total_sales)}</td><td class="num">${formatMoney(e.total_commission)}</td></tr>
    `).join("");
    document.getElementById("empSalesEmpty").style.display = empSales.length ? "none" : "block";

    const trBody = document.querySelector("#trendingTable tbody");
    trBody.innerHTML = trending.slice(0, 8).map(p => `
      <tr><td>${escapeHtml(p.name)}</td><td class="num">${p.units_sold}</td><td class="num">${formatMoney(p.revenue)}</td></tr>
    `).join("");
    document.getElementById("trendingEmpty").style.display = trending.length ? "none" : "block";
  } catch (err) {
    showToast(err.message, "danger");
  }
}

// ============================================================
// PRODUCTS
// ============================================================
let allProducts = [];

async function loadProducts() {
  try {
    allProducts = await API.get("/api/products");
    const tbody = document.querySelector("#productsTable tbody");
    tbody.innerHTML = allProducts.map(p => {
      const low = p.quantity <= p.low_stock_threshold;
      const commissionText = p.commission_enabled
        ? (p.commission_type === "percent" ? `${p.commission_value}%` : formatMoney(p.commission_value) + "/unit")
        : "—";
      return `
        <tr>
          <td><strong>${escapeHtml(p.name)}</strong><br><span style="color:var(--text-400);font-size:12px">${p.qr_code_id}</span></td>
          <td>${escapeHtml(p.category)}</td>
          <td class="num">${formatMoney(p.price)}</td>
          <td class="num">${p.quantity} ${low ? '<span class="badge badge-danger">Low</span>' : ''}</td>
          <td>${commissionText}</td>
          <td><button class="btn-ghost" onclick="showQr(${p.id})">QR dekhein</button></td>
          <td>
            <button class="btn-ghost" onclick="editProduct(${p.id})">Edit</button>
            <button class="btn-ghost" onclick="adjustStockPrompt(${p.id})">Stock +/-</button>
          </td>
        </tr>
      `;
    }).join("");
    document.getElementById("productsEmpty").style.display = allProducts.length ? "none" : "block";
  } catch (err) {
    showToast(err.message, "danger");
  }
}

function toggleCommissionFields() {
  document.getElementById("commissionFields").classList.toggle("show", document.getElementById("p_commission_enabled").checked);
}

function openProductModal(product) {
  document.getElementById("productForm").reset();
  document.getElementById("productModalTitle").textContent = product ? "Product Edit Karein" : "Naya Product";
  document.getElementById("productId").value = product ? product.id : "";
  document.getElementById("p_name").value = product ? product.name : "";
  document.getElementById("p_category").value = product ? product.category : "General";
  document.getElementById("p_price").value = product ? product.price : "";
  document.getElementById("p_quantity").value = product ? product.quantity : 0;
  document.getElementById("p_quantity").disabled = !!product; // stock changes go through Stock +/-
  document.getElementById("p_threshold").value = product ? product.low_stock_threshold : 5;
  document.getElementById("p_commission_enabled").checked = product ? product.commission_enabled : false;
  document.getElementById("p_commission_type").value = product ? product.commission_type : "percent";
  document.getElementById("p_commission_value").value = product ? product.commission_value : 0;
  document.getElementById("p_notes").value = product ? product.notes : "";
  toggleCommissionFields();
  document.getElementById("productModalOverlay").classList.add("show");
}
function closeProductModal() { document.getElementById("productModalOverlay").classList.remove("show"); }

function editProduct(id) {
  const product = allProducts.find(p => p.id === id);
  if (product) openProductModal(product);
}

document.getElementById("productForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = document.getElementById("productId").value;
  const payload = {
    name: document.getElementById("p_name").value.trim(),
    category: document.getElementById("p_category").value.trim() || "General",
    price: parseFloat(document.getElementById("p_price").value),
    quantity: parseInt(document.getElementById("p_quantity").value || 0),
    low_stock_threshold: parseInt(document.getElementById("p_threshold").value || 5),
    commission_enabled: document.getElementById("p_commission_enabled").checked,
    commission_type: document.getElementById("p_commission_type").value,
    commission_value: parseFloat(document.getElementById("p_commission_value").value || 0),
    notes: document.getElementById("p_notes").value.trim(),
  };
  try {
    if (id) {
      delete payload.quantity; // updated via stock-adjust only
      await API.patch(`/api/products/${id}`, payload);
      showToast("Product update ho gaya", "success");
    } else {
      await API.post("/api/products", payload);
      showToast("Product add ho gaya", "success");
    }
    closeProductModal();
    loadProducts();
  } catch (err) {
    showToast(err.message, "danger");
  }
});

async function adjustStockPrompt(id) {
  const product = allProducts.find(p => p.id === id);
  const input = prompt(`Current stock of "${product.name}" is ${product.quantity}.\nHow much to add (+) or remove (-)? e.g. 10 or -5`);
  if (input === null || input.trim() === "") return;
  const change = parseInt(input);
  if (isNaN(change) || change === 0) { showToast("Please enter a valid number", "danger"); return; }
  const reason = change > 0 ? "restock" : (prompt("Reason: damage, correction, or return") || "correction");
  try {
    await API.post(`/api/products/${id}/stock-adjust`, { change, reason, note: "" });
    showToast("Stock updated", "success");
    loadProducts();
  } catch (err) {
    showToast(err.message, "danger");
  }
}

async function showQr(id) {
  const product = allProducts.find(p => p.id === id);
  document.getElementById("qrProductName").textContent = product.name;
  document.getElementById("qrPrice").textContent = formatMoney(product.price);
  document.getElementById("qrImage").src = `/api/products/${id}/qr-image?t=${Date.now()}`;
  document.getElementById("qrImage").dataset.productId = id;
  document.getElementById("qrModalOverlay").classList.add("show");
}
function closeQrModal() { document.getElementById("qrModalOverlay").classList.remove("show"); }

async function printLabel() {
  const id = document.getElementById("qrImage").dataset.productId;
  const product = allProducts.find(p => p.id == id);
  const token = API.getToken();
  const res = await fetch(`/api/products/${id}/qr-image`, { headers: { Authorization: "Bearer " + token } });
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const w = window.open("", "_blank");
  w.document.write(`
    <html><head><title>Print Label</title>
    <style>
      body { font-family: sans-serif; text-align: center; padding: 20px; }
      img { width: 160px; height: 160px; }
      .name { font-weight: 700; font-size: 15px; margin-top: 6px; }
      .price { font-size: 14px; margin-top: 2px; }
      .code { font-size: 10px; color: #666; margin-top: 4px; }
    </style></head>
    <body onload="window.print()">
      <img src="${url}">
      <div class="name">${escapeHtml(product.name)}</div>
      <div class="price">₹${product.price}</div>
      <div class="code">${product.qr_code_id}</div>
    </body></html>
  `);
  w.document.close();
}

// ============================================================
// EMPLOYEES
// ============================================================
let allEmployees = [];

async function loadEmployees() {
  try {
    allEmployees = await API.get("/api/users");
    document.querySelector("#employeesTable tbody").innerHTML = allEmployees.map(u => `
      <tr>
        <td>${escapeHtml(u.name)}</td>
        <td>${escapeHtml(u.username)}</td>
        <td><span class="badge badge-neutral">${u.role}</span></td>
        <td>${u.is_active ? '<span class="badge badge-success">Active</span>' : '<span class="badge badge-danger">Inactive</span>'}</td>
        <td>
          <button class="btn-ghost" onclick="openProfileModal(${u.id})">View Profile</button>
          <button class="btn-ghost" onclick="toggleActive(${u.id})">${u.is_active ? "Deactivate" : "Activate"}</button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    showToast(err.message, "danger");
  }
}

function openEmployeeModal() {
  document.getElementById("employeeForm").reset();
  document.getElementById("employeeModalOverlay").classList.add("show");
}
function closeEmployeeModal() { document.getElementById("employeeModalOverlay").classList.remove("show"); }

document.getElementById("employeeForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await API.post("/api/users", {
      name: document.getElementById("e_name").value.trim(),
      username: document.getElementById("e_username").value.trim(),
      password: document.getElementById("e_password").value,
      role: document.getElementById("e_role").value,
    });
    showToast("Login ban gaya", "success");
    closeEmployeeModal();
    loadEmployees();
  } catch (err) {
    showToast(err.message, "danger");
  }
});

async function toggleActive(id) {
  try {
    await API.patch(`/api/users/${id}/toggle-active`);
    loadEmployees();
  } catch (err) {
    showToast(err.message, "danger");
  }
}

// ============================================================
// REPORTS
// ============================================================
async function loadReports() {
  const days = document.getElementById("reportRange").value;
  try {
    const [empSales, productSales, stockLogs] = await Promise.all([
      API.get(`/api/reports/employee-sales?days=${days}`),
      API.get(`/api/reports/product-sales?days=${days}`),
      API.get(`/api/reports/stock-logs?limit=60`),
    ]);

    const totalSales = empSales.reduce((s, e) => s + e.total_sales, 0);
    const totalCommission = empSales.reduce((s, e) => s + e.total_commission, 0);
    const totalBills = empSales.reduce((s, e) => s + e.num_transactions, 0);

    document.getElementById("reportStatGrid").innerHTML = `
      <div class="card stat-card"><div class="label">Total Sales</div><div class="value num">${formatMoney(totalSales)}</div></div>
      <div class="card stat-card"><div class="label">Total Bills</div><div class="value num">${totalBills}</div></div>
      <div class="card stat-card"><div class="label">Total Commission</div><div class="value num">${formatMoney(totalCommission)}</div></div>
    `;

    document.querySelector("#reportEmpTable tbody").innerHTML = empSales.map(e => `
      <tr><td>${escapeHtml(e.name)}</td><td class="num">${e.num_transactions}</td><td class="num">${formatMoney(e.total_sales)}</td><td class="num">${formatMoney(e.total_commission)}</td></tr>
    `).join("") || `<tr><td colspan="4" style="color:var(--text-400)">Is period mein koi sale nahi</td></tr>`;

    document.querySelector("#reportProductTable tbody").innerHTML = productSales.map(p => `
      <tr><td>${escapeHtml(p.name)}</td><td class="num">${p.units_sold}</td><td class="num">${formatMoney(p.revenue)}</td></tr>
    `).join("") || `<tr><td colspan="3" style="color:var(--text-400)">Is period mein koi sale nahi</td></tr>`;

    document.querySelector("#stockLogTable tbody").innerHTML = stockLogs.map(l => `
      <tr>
        <td style="white-space:nowrap">${new Date(l.created_at).toLocaleString("en-IN")}</td>
        <td>${escapeHtml(l.product_name)}</td>
        <td class="num" style="color:${l.change < 0 ? 'var(--danger)' : 'var(--success)'}">${l.change > 0 ? "+" : ""}${l.change}</td>
        <td><span class="badge badge-neutral">${l.reason}</span></td>
        <td style="color:var(--text-400)">${escapeHtml(l.note || "")}</td>
      </tr>
    `).join("");
  } catch (err) {
    showToast(err.message, "danger");
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

// ============================================================
// EMPLOYEE PROFILE (admin drill-down: transparency for owner + staff)
// ============================================================
let currentProfileId = null;

async function openProfileModal(userId) {
  currentProfileId = userId;
  const employee = allEmployees.find(u => u.id === userId);
  document.getElementById("profileAvatar").textContent = (employee?.name || "?").trim().charAt(0).toUpperCase();
  document.getElementById("profileName").textContent = employee?.name || "—";
  document.getElementById("profileUsername").textContent = "@" + (employee?.username || "—");
  document.getElementById("pfDateResults").innerHTML = "";
  document.getElementById("pfSearchDate").value = "";
  document.getElementById("profileModalOverlay").classList.add("show");

  try {
    const profile = await API.get(`/api/employees/${userId}/profile`);
    document.getElementById("pfTodaySales").textContent = formatMoney(profile.today_sales);
    document.getElementById("pfTodayCommission").textContent = formatMoney(profile.today_commission);
    document.getElementById("pfTodayBills").textContent = profile.today_bills;
    document.getElementById("pfMonthSales").textContent = formatMoney(profile.month_sales);
    document.getElementById("pfMonthCommission").textContent = formatMoney(profile.month_commission);
    document.getElementById("pfMonthBills").textContent = profile.month_bills;

    const history = await API.get(`/api/employees/${userId}/sales-history`);
    document.getElementById("pfHistoryList").innerHTML = history.length
      ? history.map(h => `
        <div class="history-item" style="padding:10px;margin-bottom:6px;background:var(--paper);border-radius:8px">
          <div><div class="date" style="font-size:13px">${formatDateShort(h.date)}</div><div class="meta">${h.bills} bill${h.bills === 1 ? "" : "s"}</div></div>
          <div class="amount"><div class="num" style="font-size:13px">${formatMoney(h.sales)}</div><span class="commission num">+${formatMoney(h.commission)}</span></div>
        </div>
      `).join("")
      : `<div class="empty-state">No sales recorded yet.</div>`;
  } catch (err) {
    showToast(err.message, "danger");
  }
}

function closeProfileModal() {
  document.getElementById("profileModalOverlay").classList.remove("show");
  currentProfileId = null;
}

async function searchEmployeeDate() {
  const date = document.getElementById("pfSearchDate").value;
  if (!date || !currentProfileId) return;
  try {
    const txns = await API.get(`/api/employees/${currentProfileId}/transactions?date=${date}`);
    const container = document.getElementById("pfDateResults");
    if (txns.length === 0) {
      container.innerHTML = `<div class="empty-state">No bills on ${formatDateShort(date)}.</div>`;
      return;
    }
    container.innerHTML = txns.map(t => `
      <div class="bill-item-row" style="padding:10px;border-bottom:1px solid var(--border);font-size:13px;display:flex;justify-content:space-between;cursor:pointer" onclick="closeProfileModal();viewBill(${t.id})">
        <span>Bill #${t.id}${t.customer_name ? " · " + escapeHtml(t.customer_name) : ""}</span>
        <span class="num" style="font-weight:600">${formatMoney(t.total_amount)}</span>
      </div>
    `).join("");
  } catch (err) {
    showToast(err.message, "danger");
  }
}

function formatDateShort(isoDate) {
  const d = new Date(isoDate + "T00:00:00");
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

// ============================================================
// TRANSACTIONS (searchable bill log)
// ============================================================
async function loadTransactions() {
  try {
    if (allEmployees.length === 0) allEmployees = await API.get("/api/users");
    const empSelect = document.getElementById("txn_employee");
    if (empSelect.options.length <= 1) {
      allEmployees.forEach(u => {
        const opt = document.createElement("option");
        opt.value = u.id;
        opt.textContent = u.name;
        empSelect.appendChild(opt);
      });
    }

    const params = new URLSearchParams();
    const start = document.getElementById("txn_start").value;
    const end = document.getElementById("txn_end").value;
    const emp = document.getElementById("txn_employee").value;
    const search = document.getElementById("txn_search").value.trim();
    if (start) params.set("start_date", start);
    if (end) params.set("end_date", end);
    if (emp) params.set("employee_id", emp);
    if (search) params.set("customer_search", search);

    const txns = await API.get(`/api/reports/transactions?${params.toString()}`);
    const tbody = document.querySelector("#transactionsTable tbody");
    tbody.innerHTML = txns.map(t => {
      const employee = allEmployees.find(u => u.id === t.employee_id);
      return `
        <tr style="cursor:pointer" onclick="viewBill(${t.id})">
          <td>#${t.id}</td>
          <td style="white-space:nowrap">${new Date(t.created_at).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</td>
          <td>${escapeHtml(employee?.name || "—")}</td>
          <td>${escapeHtml(t.customer_name || "—")}</td>
          <td class="num">${formatMoney(t.total_amount)}</td>
          <td class="num">${formatMoney(t.total_commission)}</td>
          <td><span class="badge badge-neutral">${t.payment_method.toUpperCase()}</span></td>
          <td><button class="btn-ghost" onclick="event.stopPropagation();viewBill(${t.id})">View</button></td>
        </tr>
      `;
    }).join("");
    document.getElementById("transactionsEmpty").style.display = txns.length ? "none" : "block";
  } catch (err) {
    showToast(err.message, "danger");
  }
}

function clearTxnFilters() {
  document.getElementById("txn_start").value = "";
  document.getElementById("txn_end").value = "";
  document.getElementById("txn_employee").value = "";
  document.getElementById("txn_search").value = "";
  loadTransactions();
}

// ============================================================
// BILL DETAIL MODAL
// ============================================================
let currentBillId = null;

async function viewBill(id) {
  currentBillId = id;
  try {
    const txn = await API.get(`/api/billing/transactions/${id}`);
    const employee = allEmployees.find(u => u.id === txn.employee_id);
    document.getElementById("billDetailContent").innerHTML = `
      <div style="font-size:13.5px;color:var(--text-600);margin-bottom:14px">
        <div><strong>Bill #${txn.id}</strong> · ${new Date(txn.created_at).toLocaleString("en-IN")}</div>
        <div>Served by: ${escapeHtml(employee?.name || "—")}</div>
        ${txn.customer_name ? `<div>Customer: ${escapeHtml(txn.customer_name)}${txn.customer_phone ? " · " + escapeHtml(txn.customer_phone) : ""}</div>` : ""}
        <div>Payment: <span class="badge badge-neutral">${txn.payment_method.toUpperCase()}</span></div>
      </div>
      <table>
        <thead><tr><th>Item</th><th>Qty</th><th>Price</th><th>Total</th></tr></thead>
        <tbody>
          ${txn.items.map(i => `
            <tr>
              <td>${escapeHtml(i.product_name_snapshot)}</td>
              <td class="num">${i.quantity}</td>
              <td class="num">${formatMoney(i.price_at_sale)}</td>
              <td class="num">${formatMoney(i.price_at_sale * i.quantity)}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
      <div style="text-align:right;margin-top:12px;font-weight:700;font-size:16px" class="num">Total: ${formatMoney(txn.total_amount)}</div>
      <div style="text-align:right;color:var(--success);font-size:13px" class="num">Commission: ${formatMoney(txn.total_commission)}</div>
    `;
    document.getElementById("billModalOverlay").classList.add("show");
  } catch (err) {
    showToast(err.message, "danger");
  }
}

function closeBillModal() {
  document.getElementById("billModalOverlay").classList.remove("show");
  currentBillId = null;
}

async function viewBillPdf() {
  if (!currentBillId) return;
  try {
    const res = await fetch(`/api/billing/transactions/${currentBillId}/pdf`, {
      headers: { Authorization: "Bearer " + API.getToken() },
    });
    const blob = await res.blob();
    window.open(URL.createObjectURL(blob), "_blank");
  } catch (err) {
    showToast("Could not load the bill PDF", "danger");
  }
}

// init
loadDashboard();
