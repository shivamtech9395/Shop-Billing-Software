requireAuth(["admin", "employee"]);
document.getElementById("empName").textContent = API.getName();

let cart = []; // { product, quantity, price_override }
let scanMode = localStorage.getItem("scan_mode") || "camera";
let html5QrCode = null;
let scanLocked = false; // true from the instant ANY code is detected until the preview is closed
let stagedProduct = null;
let stagedQty = 1;
let lastCompletedTransaction = null;

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

// ============================================================
// SETTINGS / SCAN MODE
// ============================================================
function openSettings() {
  document.querySelectorAll(".radio-option").forEach(el => el.classList.remove("selected"));
  document.querySelectorAll('input[name="scanMode"]').forEach(el => el.checked = (el.value === scanMode));
  document.getElementById("opt-" + scanMode).classList.add("selected");
  document.getElementById("settingsOverlay").classList.add("show");
}
function closeSettings() { document.getElementById("settingsOverlay").classList.remove("show"); }

function setScanMode(mode) {
  scanMode = mode;
  localStorage.setItem("scan_mode", mode);
  document.querySelectorAll(".radio-option").forEach(el => el.classList.remove("selected"));
  document.getElementById("opt-" + mode).classList.add("selected");
  document.querySelectorAll('input[name="scanMode"]').forEach(el => el.checked = (el.value === mode));
  applyScanMode();
}

function applyScanMode() {
  const tag = document.getElementById("scanModeTag");
  const subtitle = document.getElementById("scanSubtitle");
  if (scanMode === "camera") {
    tag.textContent = "Camera Mode";
    subtitle.textContent = "Point the camera at the QR label";
    document.getElementById("cameraReader").style.display = "block";
    startCamera();
    document.getElementById("scannerCaptureInput").blur();
  } else {
    tag.textContent = "Scanner Device Mode";
    subtitle.textContent = "Scan with the connected device — confirm below to add";
    document.getElementById("cameraReader").style.display = "none";
    stopCamera();
    focusScannerInput();
  }
}

// ============================================================
// CAMERA SCANNING (html5-qrcode)
// ============================================================
function startCamera() {
  if (html5QrCode) return;
  const el = document.getElementById("cameraReader");
  el.innerHTML = "";
  html5QrCode = new Html5Qrcode("cameraReader");
  html5QrCode.start(
    { facingMode: "environment" },
    { fps: 10, qrbox: { width: 220, height: 220 } },
    (decodedText) => {
      if (scanLocked) return; // ignore every extra frame while a scan is already being handled
      if (html5QrCode) html5QrCode.pause(true);
      lookupCode(decodedText);
    },
    () => { /* ignore per-frame scan misses */ }
  ).catch(() => {
    showToast("Could not access camera. Check browser permissions, or try Scanner Device mode.", "danger");
  });
}

function resumeCamera() {
  if (html5QrCode && scanMode === "camera") {
    try { html5QrCode.resume(); } catch (e) { /* already running */ }
  }
}

function stopCamera() {
  if (html5QrCode) {
    html5QrCode.stop().then(() => { html5QrCode.clear(); html5QrCode = null; }).catch(() => { html5QrCode = null; });
  }
}

// ============================================================
// HARDWARE SCANNER (keyboard-wedge devices type fast + Enter)
// ============================================================
function focusScannerInput() {
  const input = document.getElementById("scannerCaptureInput");
  input.value = "";
  input.focus();
}

document.getElementById("scannerCaptureInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const val = e.target.value.trim();
    e.target.value = "";
    if (val) lookupCode(val);
  }
});

document.addEventListener("click", () => {
  if (scanMode === "scanner" && !scanLocked) setTimeout(focusScannerInput, 50);
});

// ============================================================
// LOOKUP -> SHOW PREVIEW (confirm before adding, avoids duplicate scans)
// ============================================================
async function lookupCode(code) {
  if (!code || scanLocked) return;
  scanLocked = true; // locked the instant a code comes in -- released only when the preview closes or lookup fails
  document.getElementById("manualCode").value = "";
  try {
    const product = await API.get(`/api/scan/${encodeURIComponent(code)}`);
    if (product.quantity < 1) {
      showToast("This product is out of stock", "danger");
      releaseLock();
      return;
    }
    showPreview(product);
    if (navigator.vibrate) navigator.vibrate(60);
  } catch (err) {
    showToast(err.message, "danger");
    releaseLock();
  }
}

function releaseLock() {
  scanLocked = false;
  resumeCamera();
  if (scanMode === "scanner") focusScannerInput();
}

function showPreview(product) {
  stagedProduct = product;
  stagedQty = 1;
  document.getElementById("spName").textContent = product.name;
  document.getElementById("spMeta").textContent = `${formatMoney(product.price)} · ${product.quantity} in stock` + (product.commission_enabled ? " · earns commission" : "");
  document.getElementById("spQty").textContent = stagedQty;
  document.getElementById("scanPreview").classList.add("show");
}

function changePreviewQty(delta) {
  if (!stagedProduct) return;
  const newQty = stagedQty + delta;
  if (newQty < 1 || newQty > stagedProduct.quantity) return;
  stagedQty = newQty;
  document.getElementById("spQty").textContent = stagedQty;
}

function confirmAddToBill() {
  if (!stagedProduct) return;
  addToCart(stagedProduct, stagedQty);
  showToast(`${stagedProduct.name} added to bill`, "success");
  closePreview();
}

function cancelPreview() {
  closePreview();
}

function closePreview() {
  stagedProduct = null;
  document.getElementById("scanPreview").classList.remove("show");
  releaseLock();
}

// ============================================================
// CART
// ============================================================
function addToCart(product, qty) {
  const existing = cart.find(c => c.product.id === product.id);
  if (existing) {
    const newQty = existing.quantity + qty;
    if (newQty > product.quantity) {
      showToast(`Only ${product.quantity} left in stock`, "danger");
      return;
    }
    existing.quantity = newQty;
  } else {
    cart.push({ product, quantity: qty, price_override: product.price });
  }
  renderCart();
}

function changeQty(productId, delta) {
  const item = cart.find(c => c.product.id === productId);
  if (!item) return;
  const newQty = item.quantity + delta;
  if (newQty < 1) {
    cart = cart.filter(c => c.product.id !== productId);
  } else if (newQty > item.product.quantity) {
    showToast(`Only ${item.product.quantity} left in stock`, "danger");
    return;
  } else {
    item.quantity = newQty;
  }
  renderCart();
}

function removeFromCart(productId) {
  cart = cart.filter(c => c.product.id !== productId);
  renderCart();
}

function updatePrice(productId, value) {
  const item = cart.find(c => c.product.id === productId);
  if (!item) return;
  const price = parseFloat(value);
  item.price_override = isNaN(price) || price < 0 ? item.product.price : price;
  renderCart(true);
}

function renderCart(totalOnly) {
  const total = cart.reduce((sum, c) => sum + (c.price_override * c.quantity), 0);
  document.getElementById("cartTotal").textContent = formatMoney(total);
  document.getElementById("cartCount").textContent = `${cart.reduce((s, c) => s + c.quantity, 0)} items`;
  document.getElementById("checkoutBtn").disabled = cart.length === 0;
  document.getElementById("cartEmpty").style.display = cart.length ? "none" : "block";

  if (totalOnly) return;

  document.getElementById("cartList").innerHTML = cart.map(c => {
    const commissionNote = c.product.commission_enabled
      ? `<div class="commission-tag">💰 Earns commission</div>` : "";
    return `
      <div class="card cart-item">
        <div class="cart-item-top">
          <div>
            <div class="cart-item-name">${escapeHtml(c.product.name)}</div>
            <div class="cart-item-sub">MRP ${formatMoney(c.product.price)}</div>
            ${commissionNote}
          </div>
          <button class="cart-item-remove" onclick="removeFromCart(${c.product.id})">Remove</button>
        </div>
        <div class="cart-item-row">
          <div class="qty-control">
            <button onclick="changeQty(${c.product.id}, -1)">−</button>
            <span>${c.quantity}</span>
            <button onclick="changeQty(${c.product.id}, 1)">+</button>
          </div>
          <input type="number" class="price-input num" value="${c.price_override}" step="0.01"
                 onchange="updatePrice(${c.product.id}, this.value)"
                 oninput="updatePrice(${c.product.id}, this.value)">
          <span style="margin-left:auto;font-weight:700" class="num">${formatMoney(c.price_override * c.quantity)}</span>
        </div>
      </div>
    `;
  }).join("");
}

// ============================================================
// PAYMENT + CHECKOUT
// ============================================================
let selectedPayment = "cash";
function selectPayment(pm) {
  selectedPayment = pm;
  document.querySelectorAll(".pm-btn").forEach(b => b.classList.toggle("active", b.dataset.pm === pm));
}

function openCustomerModal() {
  if (cart.length === 0) return;
  document.getElementById("c_name").value = "";
  document.getElementById("c_phone").value = "";
  document.getElementById("customerModalOverlay").classList.add("show");
}
function closeCustomerModal() {
  document.getElementById("customerModalOverlay").classList.remove("show");
  checkout();
}

async function checkout() {
  document.getElementById("customerModalOverlay").classList.remove("show");
  if (cart.length === 0) return;
  const btn = document.getElementById("checkoutBtn");
  btn.disabled = true;
  try {
    const payload = {
      payment_method: selectedPayment,
      customer_name: document.getElementById("c_name").value.trim() || null,
      customer_phone: document.getElementById("c_phone").value.trim() || null,
      items: cart.map(c => ({
        product_id: c.product.id,
        quantity: c.quantity,
        price_override: c.price_override,
      })),
    };
    const txn = await API.post("/api/billing/checkout", payload);
    lastCompletedTransaction = txn;
    cart = [];
    renderCart();
    showSuccessModal(txn);
  } catch (err) {
    showToast(err.message, "danger");
  } finally {
    btn.disabled = cart.length === 0;
  }
}

function showSuccessModal(txn) {
  document.getElementById("successSummary").textContent =
    `Bill #${txn.id} · ${formatMoney(txn.total_amount)}` + (txn.customer_name ? ` · ${txn.customer_name}` : "");

  const whatsappBtn = document.getElementById("whatsappBtn");
  if (txn.customer_phone) {
    whatsappBtn.href = buildWhatsappLink(txn);
    whatsappBtn.style.display = "flex";
  } else {
    whatsappBtn.style.display = "none";
  }
  document.getElementById("successModalOverlay").classList.add("show");
}

function buildWhatsappLink(txn) {
  const lines = [`*Bill #${txn.id}*`, new Date(txn.created_at).toLocaleString("en-IN"), ""];
  txn.items.forEach(item => {
    lines.push(`${item.product_name_snapshot} x${item.quantity} = ${formatMoney(item.price_at_sale * item.quantity)}`);
  });
  lines.push("");
  lines.push(`Total: ${formatMoney(txn.total_amount)}`);
  lines.push("Thank you for shopping with us!");
  const message = lines.join("\n");
  const digitsOnly = (txn.customer_phone || "").replace(/\D/g, "");
  return `https://wa.me/${digitsOnly}?text=${encodeURIComponent(message)}`;
}

function closeSuccessModal() {
  document.getElementById("successModalOverlay").classList.remove("show");
  lastCompletedTransaction = null;
}

async function viewPdf(download) {
  if (!lastCompletedTransaction) return;
  try {
    const res = await fetch(`/api/billing/transactions/${lastCompletedTransaction.id}/pdf`, {
      headers: { Authorization: "Bearer " + API.getToken() },
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    if (download) {
      const a = document.createElement("a");
      a.href = url;
      a.download = `bill-${lastCompletedTransaction.id}.pdf`;
      a.click();
    } else {
      window.open(url, "_blank");
    }
  } catch (err) {
    showToast("Could not load the bill PDF", "danger");
  }
}

// ============================================================
// INIT
// ============================================================
renderCart();
applyScanMode();
