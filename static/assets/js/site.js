/* ilterra.com: menu toggles and timeline scrolling. The site works without this file. */
(function () {
  "use strict";

  // ---- main menu (burger on tablets/phones)
  var toggle = document.querySelector(".nav-toggle");
  var nav = document.getElementById("main-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = toggle.getAttribute("aria-expanded") !== "true";
      toggle.setAttribute("aria-expanded", String(open));
      nav.classList.toggle("is-open", open);
    });
  }

  // ---- dropdowns: click/tap support (hover works on desktop through CSS)
  document.querySelectorAll(".submenu-toggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var item = btn.closest(".has-children");
      var open = !item.classList.contains("is-open");
      document.querySelectorAll(".has-children.is-open").forEach(function (other) {
        if (other !== item) {
          other.classList.remove("is-open");
          other.querySelector(".submenu-toggle").setAttribute("aria-expanded", "false");
        }
      });
      item.classList.toggle("is-open", open);
      btn.setAttribute("aria-expanded", String(open));
    });
  });
  document.addEventListener("click", function (e) {
    if (!e.target.closest(".has-children")) {
      document.querySelectorAll(".has-children.is-open").forEach(function (item) {
        item.classList.remove("is-open");
        item.querySelector(".submenu-toggle").setAttribute("aria-expanded", "false");
      });
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") document.activeElement && document.activeElement.blur();
  });

  // ---- timeline: arrows + start at the most recent entry
  document.querySelectorAll("[data-timeline]").forEach(function (tl) {
    var vp = tl.querySelector(".tl-viewport");
    var prev = tl.querySelector(".tl-prev");
    var next = tl.querySelector(".tl-next");
    var horizontal = function () { return window.matchMedia("(min-width: 821px)").matches; };

    function update() {
      var overflow = horizontal() && vp.scrollWidth > vp.clientWidth + 2;
      tl.classList.toggle("is-overflowing", overflow);
      prev.hidden = next.hidden = !overflow;
      if (overflow) {
        prev.disabled = vp.scrollLeft <= 2;
        next.disabled = vp.scrollLeft + vp.clientWidth >= vp.scrollWidth - 2;
      }
    }
    function step(dir) { vp.scrollBy({ left: dir * vp.clientWidth * 0.8, behavior: "smooth" }); }

    prev.addEventListener("click", function () { step(-1); });
    next.addEventListener("click", function () { step(1); });
    vp.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);

    if (horizontal()) {
      var behavior = vp.style.scrollBehavior;
      vp.style.scrollBehavior = "auto";
      vp.scrollLeft = vp.scrollWidth;
      vp.style.scrollBehavior = behavior;
    }
    update();
  });

  // ---- "On this page": highlight the section currently in view
  var spy = document.querySelector("[data-scrollspy]");
  if (spy && "IntersectionObserver" in window) {
    var links = {};
    spy.querySelectorAll('a[href^="#"]').forEach(function (a) {
      links[decodeURIComponent(a.getAttribute("href").slice(1))] = a;
    });
    var heads = Array.prototype.filter.call(
      document.querySelectorAll(".prose h2[id], .prose h3[id]"), function (h) { return links[h.id]; });
    var visible = new Set();
    var setActive = function (id) {
      Object.keys(links).forEach(function (k) { links[k].classList.toggle("is-active", k === id); });
    };
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { e.isIntersecting ? visible.add(e.target) : visible.delete(e.target); });
      var current = null;
      heads.forEach(function (h) { if (h.getBoundingClientRect().top < window.innerHeight * 0.35) current = h; });
      if (!current && visible.size) current = heads.find(function (h) { return visible.has(h); });
      if (current) {
        setActive(current.id);
        // keep the active entry visible when the list scrolls on its own
        if (spy.scrollHeight > spy.clientHeight) {
          var a = links[current.id].getBoundingClientRect(), box = spy.getBoundingClientRect();
          if (a.top < box.top || a.bottom > box.bottom) spy.scrollTop += a.top - box.top - box.height / 3;
        }
      }
    }, { rootMargin: "0px 0px -55% 0px" });
    heads.forEach(function (h) { io.observe(h); });
  }

  // ---- AdSense: request only units that are actually visible (the sidebar is hidden on phones)
  document.querySelectorAll("ins.adsbygoogle").forEach(function (ins) {
    if (ins.offsetParent === null) ins.closest(".ad").remove();
  });
  document.querySelectorAll("ins.adsbygoogle").forEach(function () {
    try { (window.adsbygoogle = window.adsbygoogle || []).push({}); } catch (e) { /* blocked or not loaded */ }
  });

  // ---- copy button on code blocks
  document.querySelectorAll(".prose pre").forEach(function (pre) {
    if (!navigator.clipboard) return;
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy-btn";
    btn.textContent = "Copy";
    btn.addEventListener("click", function () {
      var code = pre.querySelector("code") || pre;
      navigator.clipboard.writeText(code.innerText.replace(/\n$/, "")).then(function () {
        btn.textContent = "Copied";
        setTimeout(function () { btn.textContent = "Copy"; }, 1600);
      });
    });
    pre.appendChild(btn);
  });

  // ---- click on a content image to see it larger
  var zoomable = Array.prototype.filter.call(document.querySelectorAll(".prose img"), function (img) {
    return !img.closest("a") && !img.classList.contains("is-badge");
  });
  if (zoomable.length && window.HTMLDialogElement) {
    var dlg = document.createElement("dialog");
    dlg.className = "lightbox";
    dlg.innerHTML = '<button class="lightbox-close" type="button" aria-label="Close">×</button><img alt="">';
    document.body.appendChild(dlg);
    var big = dlg.querySelector("img");
    dlg.addEventListener("click", function () { dlg.close(); });
    zoomable.forEach(function (img) {
      img.setAttribute("data-zoom", "");
      img.addEventListener("click", function () {
        big.src = img.currentSrc || img.src;
        big.alt = img.alt;
        dlg.showModal();
      });
    });
  }
})();
