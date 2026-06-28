function initIcons() {
  if (window.lucide) {
    window.lucide.createIcons();
  } else {
    window.setTimeout(initIcons, 80);
  }
}

function initNavigation() {
  const toggle = document.querySelector("[data-nav-toggle]");
  const nav = document.querySelector("[data-nav]");
  if (!toggle || !nav) return;

  toggle.addEventListener("click", () => {
    const isOpen = nav.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", String(isOpen));
  });

  nav.addEventListener("click", (event) => {
    if (event.target.closest("a")) {
      nav.classList.remove("is-open");
      toggle.setAttribute("aria-expanded", "false");
    }
  });
}

function initToolFilters() {
  const search = document.querySelector("[data-tool-search]");
  const cards = Array.from(document.querySelectorAll("[data-tool-card]"));
  const chips = Array.from(document.querySelectorAll("[data-category]"));
  const count = document.querySelector("[data-result-count]");
  const emptyState = document.querySelector("[data-empty-state]");
  if (!search || !cards.length) return;

  let activeCategory = "todos";
  const normalize = (value) =>
    value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");

  const applyFilters = () => {
    const query = normalize(search.value.trim());
    let visible = 0;

    cards.forEach((card) => {
      const haystack = normalize(card.dataset.search || "");
      const category = card.dataset.category;
      const matchesQuery = !query || haystack.includes(query);
      const matchesCategory = activeCategory === "todos" || category === activeCategory;
      const shouldShow = matchesQuery && matchesCategory;
      card.hidden = !shouldShow;
      if (shouldShow) visible += 1;
    });

    if (count) count.textContent = String(visible);
    if (emptyState) emptyState.hidden = visible !== 0;
  };

  search.addEventListener("input", applyFilters);
  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      activeCategory = chip.dataset.category;
      chips.forEach((item) => item.classList.toggle("is-active", item === chip));
      applyFilters();
    });
  });
}

function initReveal() {
  const items = Array.from(document.querySelectorAll(".reveal"));
  if (!items.length) return;

  if (!("IntersectionObserver" in window)) {
    items.forEach((item) => item.classList.add("is-visible"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.12 }
  );

  items.forEach((item) => observer.observe(item));
}

function initConfirmations() {
  document.querySelectorAll("[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const message = form.dataset.confirm || "Confirmar ação?";
      if (!window.confirm(message)) {
        event.preventDefault();
      }
    });
  });
}

function initParticles() {
  const canvas = document.querySelector("[data-particles]");
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!canvas || prefersReducedMotion) return;

  const context = canvas.getContext("2d");
  const points = [];
  const amount = 54;
  let width = 0;
  let height = 0;
  let animationFrame = 0;

  const resize = () => {
    const ratio = window.devicePixelRatio || 1;
    width = canvas.offsetWidth;
    height = canvas.offsetHeight;
    canvas.width = Math.max(1, Math.floor(width * ratio));
    canvas.height = Math.max(1, Math.floor(height * ratio));
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
  };

  const makePoint = () => ({
    x: Math.random() * width,
    y: Math.random() * height,
    vx: (Math.random() - 0.5) * 0.28,
    vy: (Math.random() - 0.5) * 0.28,
    radius: 1 + Math.random() * 1.7,
  });

  const reset = () => {
    resize();
    points.length = 0;
    for (let i = 0; i < amount; i += 1) points.push(makePoint());
  };

  const draw = () => {
    context.clearRect(0, 0, width, height);
    context.fillStyle = "rgba(53, 208, 255, 0.72)";
    context.strokeStyle = "rgba(124, 247, 200, 0.12)";
    context.lineWidth = 1;

    points.forEach((point) => {
      point.x += point.vx;
      point.y += point.vy;
      if (point.x < 0 || point.x > width) point.vx *= -1;
      if (point.y < 0 || point.y > height) point.vy *= -1;
      context.beginPath();
      context.arc(point.x, point.y, point.radius, 0, Math.PI * 2);
      context.fill();
    });

    for (let i = 0; i < points.length; i += 1) {
      for (let j = i + 1; j < points.length; j += 1) {
        const a = points[i];
        const b = points[j];
        const distance = Math.hypot(a.x - b.x, a.y - b.y);
        if (distance < 150) {
          context.globalAlpha = 1 - distance / 150;
          context.beginPath();
          context.moveTo(a.x, a.y);
          context.lineTo(b.x, b.y);
          context.stroke();
          context.globalAlpha = 1;
        }
      }
    }

    animationFrame = window.requestAnimationFrame(draw);
  };

  reset();
  draw();
  window.addEventListener("resize", () => {
    window.cancelAnimationFrame(animationFrame);
    reset();
    draw();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initIcons();
  initNavigation();
  initToolFilters();
  initReveal();
  initConfirmations();
  initParticles();
});
