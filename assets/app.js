/* Zaykaveda shared script: API helper, cart, nav, footer, WhatsApp icon */
(function () {
  const C = window.ZAYKAVEDA;
  const Z = (window.Z = {});
  Z.cfg = { upi_id: "", upi_name: C.BRAND, whatsapp: C.WHATSAPP, owner_name: "Arish Shah" };

  Z.esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  Z.rs = (n) => "₹" + Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });

  Z.api = async (path, opts = {}) => {
    const headers = { "Content-Type": "application/json" };
    const tok = opts.token;
    if (tok) headers.Authorization = "Bearer " + tok;
    let res;
    try {
      res = await fetch(C.API_URL + path, {
        method: opts.method || "GET",
        headers,
        body: opts.body ? JSON.stringify(opts.body) : undefined,
      });
    } catch (e) {
      throw new Error("Cannot reach the server. Please check your internet or try again in a minute.");
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = new Error(data.error || "Something went wrong");
      err.status = res.status;
      throw err;
    }
    return data;
  };

  Z.toast = (msg) => {
    let t = document.querySelector(".toast");
    if (!t) { t = document.createElement("div"); t.className = "toast"; document.body.appendChild(t); }
    t.textContent = msg; t.classList.add("show");
    clearTimeout(Z._tt); Z._tt = setTimeout(() => t.classList.remove("show"), 2200);
  };

  /* ---------- cart (localStorage) ---------- */
  const KEY = "zaykaveda_cart_v1";
  Z.cart = {
    get() { try { return JSON.parse(localStorage.getItem(KEY)) || []; } catch { return []; } },
    save(c) { try { localStorage.setItem(KEY, JSON.stringify(c)); } catch {} Z.renderCart(); },
    add(d, qty = 1) {
      const c = this.get(); const f = c.find((x) => x.id === d.id);
      if (f) f.qty += qty; else c.push({ id: d.id, name: d.name, price: d.price, qty });
      this.save(c);
    },
    set(id, qty) {
      let c = this.get();
      c = qty <= 0 ? c.filter((x) => x.id !== id) : c.map((x) => (x.id === id ? { ...x, qty } : x));
      this.save(c);
    },
    clear() { this.save([]); },
    count() { return this.get().reduce((s, x) => s + x.qty, 0); },
    total() { return this.get().reduce((s, x) => s + x.qty * x.price, 0); },
  };

  const WA_SVG = '<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16.003 3C9.373 3 4 8.373 4 15c0 2.385.697 4.607 1.894 6.48L4 29l7.7-1.857A11.94 11.94 0 0 0 16.003 27C22.633 27 28 21.627 28 15S22.633 3 16.003 3zm0 2.2c5.41 0 9.797 4.39 9.797 9.8 0 5.41-4.387 9.8-9.797 9.8a9.77 9.77 0 0 1-4.98-1.36l-.357-.213-4.57 1.103 1.12-4.45-.233-.37A9.75 9.75 0 0 1 6.2 15c0-5.41 4.39-9.8 9.803-9.8zm-3.54 4.9c-.2 0-.52.075-.79.37-.27.3-1.03 1.01-1.03 2.46 0 1.45 1.055 2.85 1.2 3.045.15.2 2.07 3.3 5.1 4.5 2.52.99 3.03.79 3.58.74.55-.05 1.77-.72 2.02-1.42.25-.7.25-1.3.175-1.42-.075-.125-.275-.2-.575-.35-.3-.15-1.77-.875-2.045-.975-.275-.1-.475-.15-.675.15-.2.3-.775.975-.95 1.175-.175.2-.35.225-.65.075-.3-.15-1.27-.47-2.42-1.495-.895-.8-1.5-1.785-1.675-2.085-.175-.3-.02-.46.13-.61.135-.135.3-.35.45-.525.15-.175.2-.3.3-.5.1-.2.05-.375-.025-.525-.075-.15-.675-1.62-.925-2.22-.24-.585-.49-.505-.675-.515-.175-.01-.375-.01-.575-.01z"/></svg>';
  Z.waLink = (msg) => "https://wa.me/" + Z.cfg.whatsapp + (msg ? "?text=" + encodeURIComponent(msg) : "");
  Z.waSvg = WA_SVG;

  /* ---------- layout injection ---------- */
  const PAGES = [["index.html", "Home"], ["menu.html", "Menu"], ["about.html", "About"], ["contact.html", "Contact"]];

  Z.init = (active) => {
    const nav = document.createElement("header");
    nav.className = "nav";
    nav.innerHTML = `<div class="wrap">
      <a class="logo" href="index.html">Zayka<span>veda</span></a>
      <nav class="links" id="links">${PAGES.map(([h, n]) => `<a href="${h}" class="${h === active ? "on" : ""}">${n}</a>`).join("")}</nav>
      <div class="nav-right">
        <button class="cart-btn" id="openCart" aria-label="Open cart">Cart<b id="cartCount">0</b></button>
        <button class="burger" id="burger" aria-label="Menu">☰</button>
      </div></div>`;
    document.body.prepend(nav);

    const foot = document.createElement("footer");
    foot.className = "site";
    foot.innerHTML = `<div class="wrap"><div class="cols">
      <div><a class="logo" href="index.html" style="display:inline">Zayka<span>veda</span></a>
        <p style="color:var(--muted);font-size:.92rem;margin-top:8px;max-width:36ch">Indian classics and India's favourite Chinese, cooked fresh and served with care.</p></div>
      <div><h4>Explore</h4>${PAGES.map(([h, n]) => `<a href="${h}">${n}</a>`).join("")}</div>
      <div><h4>Talk to us</h4><a href="contact.html">Send a message</a>
        <a href="${Z.waLink("Hello Zaykaveda!")}" target="_blank" rel="noopener" class="wa-inline">${WA_SVG} WhatsApp us</a>
        <a href="admin/index.html">Staff login</a></div></div>
      <div class="copy">© ${new Date().getFullYear()} Zaykaveda. All rights reserved. The Zaykaveda name, logo, menu descriptions and website content are the property of the restaurant owner and may not be copied or reused without written permission.</div></div>`;
    document.body.appendChild(foot);

    const wa = document.createElement("a");
    wa.className = "wa"; wa.id = "waFloat"; wa.target = "_blank"; wa.rel = "noopener";
    wa.href = Z.waLink("Hello Zaykaveda!"); wa.setAttribute("aria-label", "Chat on WhatsApp");
    wa.innerHTML = WA_SVG;
    document.body.appendChild(wa);

    const bg = document.createElement("div"); bg.className = "drawer-bg"; bg.id = "dbg";
    const dr = document.createElement("aside"); dr.className = "drawer"; dr.id = "drawer";
    dr.innerHTML = `<header><h3>Your cart</h3><button class="x" id="closeCart" aria-label="Close">×</button></header>
      <div class="body" id="cartBody"></div>
      <footer><div class="total"><span>Total</span><span id="cartTotal">₹0</span></div>
      <a class="btn btn-primary" id="checkoutBtn" href="checkout.html" style="width:100%">Checkout &amp; pay with UPI</a></footer>`;
    document.body.append(bg, dr);

    const toggle = (o) => { dr.classList.toggle("open", o); bg.classList.toggle("open", o); };
    document.getElementById("openCart").onclick = () => toggle(true);
    document.getElementById("closeCart").onclick = () => toggle(false);
    bg.onclick = () => toggle(false);
    document.getElementById("burger").onclick = () => document.getElementById("links").classList.toggle("open");
    Z.openCart = () => toggle(true);
    Z.renderCart();

    // fresh owner config (WhatsApp number etc.) from backend; fails silently
    Z.api("/api/config").then((c) => {
      Z.cfg = { ...Z.cfg, ...c };
      document.querySelectorAll('a[href^="https://wa.me/"]').forEach((a) => {
        const q = a.href.split("?")[1];
        a.href = "https://wa.me/" + Z.cfg.whatsapp + (q ? "?" + q : "");
      });
      if (Z.onConfig) Z.onConfig(Z.cfg);
    }).catch(() => {});
  };

  Z.renderCart = () => {
    const body = document.getElementById("cartBody");
    const cnt = document.getElementById("cartCount");
    if (cnt) cnt.textContent = Z.cart.count();
    if (!body) return;
    const c = Z.cart.get();
    document.getElementById("cartTotal").textContent = Z.rs(Z.cart.total());
    const btn = document.getElementById("checkoutBtn");
    btn.style.pointerEvents = c.length ? "" : "none"; btn.style.opacity = c.length ? "" : ".5";
    body.innerHTML = c.length
      ? c.map((x) => `<div class="line"><div><strong>${Z.esc(x.name)}</strong><br><small>${Z.rs(x.price)} each</small></div>
          <div class="qty"><button data-d="${x.id}" data-q="${x.qty - 1}">−</button><span>${x.qty}</span><button data-d="${x.id}" data-q="${x.qty + 1}">+</button></div></div>`).join("")
      : '<p class="empty">Your cart is empty.<br>Add something delicious!</p>';
    body.querySelectorAll("button[data-d]").forEach((b) => (b.onclick = () => Z.cart.set(+b.dataset.d, +b.dataset.q)));
    if (Z.onCartChange) Z.onCartChange();
  };
})();
