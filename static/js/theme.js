// Ripple effect on buttons
document.addEventListener('click', function (e) {
  const target = e.target.closest('.btn');
  if (!target) return;
  const rect = target.getBoundingClientRect();
  const circle = document.createElement('span');
  const diameter = Math.max(rect.width, rect.height);
  circle.classList.add('ripple');
  circle.style.width = circle.style.height = `${diameter}px`;
  circle.style.left = `${e.clientX - rect.left - diameter / 2}px`;
  circle.style.top = `${e.clientY - rect.top - diameter / 2}px`;
  circle.style.position = 'absolute';
  target.style.position = 'relative';
  target.appendChild(circle);
  setTimeout(() => circle.remove(), 600);
});

// Reveal on scroll
const revealEls = document.querySelectorAll('.reveal');
if ('IntersectionObserver' in window && revealEls.length) {
  const obs = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('reveal-visible');
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });
  revealEls.forEach((el) => obs.observe(el));
} else {
  revealEls.forEach((el) => el.classList.add('reveal-visible'));
}

// Subtle tilt effect for cards
document.querySelectorAll('.hover-tilt').forEach((card) => {
  card.addEventListener('mousemove', (e) => {
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const rotateY = ((x / rect.width) - 0.5) * 6;
    const rotateX = ((y / rect.height) - 0.5) * -6;
    card.style.transform = `perspective(600px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
  });
  card.addEventListener('mouseleave', () => {
    card.style.transform = '';
  });
});

// Navbar shrink on scroll
const nav = document.querySelector('.navbar');
const onScroll = () => {
  if (!nav) return;
  if (window.scrollY > 10) nav.classList.add('navbar-scrolled');
  else nav.classList.remove('navbar-scrolled');
};
window.addEventListener('scroll', onScroll);
onScroll();

// Voice search using Web Speech API (best effort)
function attachVoice(btnId, targetInputSelector) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.addEventListener('click', () => {
    const input = document.querySelector(targetInputSelector) || document.querySelector('form[role="search"] input[name="q"]');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Voice search not supported in this browser.');
      return;
    }
    const rec = new SpeechRecognition();
    rec.lang = 'en-IN';
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = (e) => {
      const text = e.results[0][0].transcript;
      if (input) input.value = text;
    };
    rec.start();
  });
}
attachVoice('voiceSearchBtn', 'form[role="search"] input[name="q"]');
attachVoice('voiceSearchBtnMobile', '#mobileSearchInput');

// Image search buttons: try camera first, fallback to gallery if no selection
function wireImageSearchCameraFirst(btnId, formId, galleryInputId, cameraInputId) {
  const btn = document.getElementById(btnId);
  const form = document.getElementById(formId);
  const gallery = document.getElementById(galleryInputId);
  const camera = document.getElementById(cameraInputId);
  if (!btn || !form || !gallery || !camera) return;
  const submitOn = (input) => input && input.addEventListener('change', () => form.submit());
  submitOn(gallery); submitOn(camera);
  btn.addEventListener('click', () => {
    let fallbackTimer;
    const onCameraChange = () => { if (fallbackTimer) clearTimeout(fallbackTimer); };
    camera.addEventListener('change', onCameraChange, { once: true });
    try { camera.click(); } catch (_) {}
    // Fallback to gallery if camera doesn't trigger change (e.g., no camera support)
    fallbackTimer = setTimeout(() => {
      try { gallery.click(); } catch (_) {}
    }, 1200);
  });
}
wireImageSearchCameraFirst('imageSearchBtn', 'imageSearchForm', 'imageSearchInput', 'imageSearchInputCam');
wireImageSearchCameraFirst('imageSearchBtnMobile', 'imageSearchFormMobile', 'imageSearchInputMobile', 'imageSearchInputMobileCam');
wireImageSearchCameraFirst('imageSearchBtnMobileTop', 'imageSearchFormMobileTop', 'imageSearchInputMobileTop', 'imageSearchInputMobileTopCam');

// Chip messages auto-hide and close
(function(){
  const chips = document.querySelectorAll('.chip-msg');
  function dismissChip(chip){
    if (!chip || chip.classList.contains('chip-out')) return;
    chip.classList.add('chip-out');
    const removeNow = () => chip.parentElement && chip.parentElement.removeChild(chip);
    chip.addEventListener('animationend', removeNow, { once: true });
    // Safety fallback
    setTimeout(removeNow, 900);
  }
  chips.forEach((chip) => {
    const closer = chip.querySelector('.chip-close');
    if (closer) closer.addEventListener('click', () => dismissChip(chip));
    setTimeout(() => dismissChip(chip), 3500);
  });
})();

// Theme toggle: dark/light with persistence
(function(){
  function applyTheme(theme){
    try {
      localStorage.setItem('theme', theme);
    } catch(e) {}
    document.documentElement.setAttribute('data-theme', theme);
    // Toggle Bootswatch dark stylesheet
    var darkLink = document.getElementById('bootswatchDark');
    var lightLink = document.getElementById('bootswatchLight');
    try {
      if (darkLink) darkLink.disabled = (theme === 'light');
      if (lightLink) lightLink.disabled = (theme !== 'light');
    } catch(e) {}
    // Icon reflects action: show sun when currently dark (click for light)
    var icon = document.getElementById('themeToggleIcon') || document.querySelector('#themeToggle i');
    var icons = document.querySelectorAll('#themeToggle i, #themeToggleMobile i');
    icons.forEach(function(ic){
      ic.classList.remove('bi-moon-stars','bi-brightness-high');
      ic.classList.add(theme === 'dark' ? 'bi-brightness-high' : 'bi-moon-stars');
    });
  }
  function currentTheme(){
    try { return localStorage.getItem('theme') || 'light'; } catch(e) { return 'light'; }
  }
  function toggleTheme(){ applyTheme(currentTheme() === 'dark' ? 'light' : 'dark'); }

  // Initialize
  document.addEventListener('DOMContentLoaded', function(){
    applyTheme(currentTheme());
    var t1 = document.getElementById('themeToggle');
    var t2 = document.getElementById('themeToggleMobile');
    if (t1) t1.addEventListener('click', function(e){ e.preventDefault(); toggleTheme(); });
    if (t2) t2.addEventListener('click', function(e){ e.preventDefault(); toggleTheme(); });
  });
})();

// Auto-submit cart quantity changes with debounce
(function(){
  const forms = document.querySelectorAll('form.cart-qty-form');
  forms.forEach((form) => {
    const input = form.querySelector('input[name="quantity"]');
    if (!input) return;
    let t;
    const submitNow = () => {
      try {
        const data = new FormData(form);
        fetch(form.action, {
          method: 'POST',
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          credentials: 'same-origin',
          body: data,
        }).then(r => r.json()).then(json => {
          // Update line totals (both mobile and desktop instances)
          const vid = json.vid || 0;
          document.querySelectorAll(`.lt[data-pid="${json.pid}"][data-vid="${vid}"]`).forEach(el => { el.textContent = json.item_total; });
          // Update summary
          const s = id => document.getElementById(id);
          if (s('cart-subtotal')) s('cart-subtotal').textContent = json.subtotal;
          if (s('cart-gst')) s('cart-gst').textContent = json.gst_amount;
          if (s('cart-shipping')) s('cart-shipping').textContent = json.shipping;
          if (s('cart-total')) s('cart-total').textContent = json.total;
          // Update cart badges (desktop)
          const deskBadge = document.querySelector('a.nav-link[href="/cart/"] .badge');
          if (json.cart_count > 0) {
            if (deskBadge) deskBadge.textContent = json.cart_count;
            else {
              const link = document.querySelector('a.nav-link[href="/cart/"]');
              if (link) {
                const span = document.createElement('span');
                span.className = 'badge rounded-pill bg-danger ms-1';
                span.textContent = json.cart_count;
                link.appendChild(span);
              }
            }
          } else if (deskBadge) {
            deskBadge.remove();
          }
          // Update mobile badge
          const mobBadge = document.querySelector('.mobile-bottom-nav .mobile-badge');
          if (mobBadge) {
            if (json.cart_count > 0) { mobBadge.textContent = json.cart_count; mobBadge.style.display = 'inline-block'; }
            else { mobBadge.style.display = 'none'; }
          }
        }).catch(() => {});
      } catch(e) {}
    };
    input.addEventListener('input', () => {
      if (t) clearTimeout(t);
      // Ensure at least 1
      const v = parseInt(input.value || '1', 10);
      if (isNaN(v) || v < 1) input.value = 1;
      t = setTimeout(submitNow, 450);
    });
    input.addEventListener('change', submitNow);
    form.addEventListener('submit', (e) => { e.preventDefault(); submitNow(); });
  });
})();

// Autoplay/pause videos within Bootstrap carousels
(function(){
  function handleCarousel(el){
    const playActive = () => {
      el.querySelectorAll('video').forEach(v => { try { v.pause(); } catch(_){} });
      const active = el.querySelector('.carousel-item.active video');
      if (active) { try { active.play(); } catch(_){} }
    };
    el.addEventListener('slid.bs.carousel', playActive);
    // initial
    playActive();
  }
  document.querySelectorAll('.carousel').forEach(handleCarousel);
})();

// AJAX remove cart item without reload
(function(){
  function getCsrfToken(){
    const name = 'csrftoken=';
    const parts = document.cookie.split(';');
    for (let p of parts){
      p = p.trim();
      if (p.startsWith(name)) return p.substring(name.length);
    }
    // Fallback: try to find any csrfmiddlewaretoken input
    const inp = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return inp ? inp.value : '';
  }
  document.addEventListener('click', function(e){
    const btn = e.target.closest('a.cart-remove');
    if (!btn) return;
    e.preventDefault();
    const pid = btn.getAttribute('data-pid');
    const vid = btn.getAttribute('data-vid');
    const url = btn.getAttribute('data-action') || btn.getAttribute('href');
    const fd = new FormData();
    fd.append('product_id', pid);
    if (vid && vid !== '0') fd.append('variant_id', vid);
    fd.append('csrfmiddlewaretoken', getCsrfToken());
    fetch(url, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' }, credentials: 'same-origin', body: fd })
      .then(r => r.json())
      .then(json => {
        document.querySelectorAll(`.cart-row[data-pid="${json.pid}"][data-vid="${json.vid || 0}"]`).forEach(r => r.remove());
        const s = id => document.getElementById(id);
        if (s('cart-subtotal')) s('cart-subtotal').textContent = json.subtotal;
        if (s('cart-gst')) s('cart-gst').textContent = json.gst_amount;
        if (s('cart-shipping')) s('cart-shipping').textContent = json.shipping;
        if (s('cart-total')) s('cart-total').textContent = json.total;
        // Update cart badges (desktop)
        const deskBadge = document.querySelector('a.nav-link[href="/cart/"] .badge');
        if (json.cart_count > 0) {
          if (deskBadge) deskBadge.textContent = json.cart_count;
          else {
            const link = document.querySelector('a.nav-link[href="/cart/"]');
            if (link) {
              const span = document.createElement('span');
              span.className = 'badge rounded-pill bg-danger ms-1';
              span.textContent = json.cart_count;
              link.appendChild(span);
            }
          }
        } else if (deskBadge) {
          deskBadge.remove();
        }
        // Mobile badge
        const mobBadge = document.querySelector('.mobile-bottom-nav .mobile-badge');
        if (mobBadge) {
          if (json.cart_count > 0) { mobBadge.textContent = json.cart_count; mobBadge.style.display = 'inline-block'; }
          else { mobBadge.style.display = 'none'; }
        }
        // If no items left, show empty state
        if (json.cart_count === 0) {
          const container = document.querySelector('.row.g-4');
          if (container) container.innerHTML = '<div class="text-center py-5 w-100"><h4>Your cart is empty</h4><p class="text-muted">Browse products and add your favorites to the cart.</p><a href="/" class="btn btn-primary">Start Shopping</a></div>';
        }
      })
      .catch(() => {});
  }, false);
})();

// Product image magnifier (hover zoom + wheel to adjust)
(function(){
  function attachMagnifier(img){
    if (!img || img.dataset.magnifyAttached === '1') return;
    // Disable magnifier on small screens for responsiveness
    if (window.innerWidth < 992) return;
    const container = img.closest('.carousel-item') || img.parentElement;
    if (!container) return;
    container.classList.add('magnify-container');
    const lens = document.createElement('div');
    lens.className = 'magnifier-lens';
    container.appendChild(lens);
    img.classList.add('magnify-target');
    img.dataset.magnifyAttached = '1';

    // Lens size proportional to image width
    const base = Math.max(120, Math.min(220, Math.floor(img.clientWidth * 0.25)));
    lens.style.width = base + 'px';
    lens.style.height = base + 'px';

    let zoom = 2.0;
    const minZoom = 1.5;
    const maxZoom = 4.0;

    const updateBackground = () => {
      const cw = img.clientWidth;
      const ch = img.clientHeight;
      lens.style.backgroundImage = `url('${img.src}')`;
      lens.style.backgroundSize = `${cw * zoom}px ${ch * zoom}px`;
    };

    function moveLens(e){
      const rect = img.getBoundingClientRect();
      const pageX = (e.touches ? e.touches[0].pageX : e.pageX);
      const pageY = (e.touches ? e.touches[0].pageY : e.pageY);
      const x = pageX - (window.pageXOffset + rect.left);
      const y = pageY - (window.pageYOffset + rect.top);
      const lw = lens.offsetWidth;
      const lh = lens.offsetHeight;
      let lx = x - lw/2;
      let ly = y - lh/2;
      // Clamp lens inside image
      lx = Math.max(0, Math.min(lx, img.clientWidth - lw));
      ly = Math.max(0, Math.min(ly, img.clientHeight - lh));
      lens.style.left = `${lx}px`;
      lens.style.top = `${ly}px`;
      const bgX = -(lx * zoom - lw/2);
      const bgY = -(ly * zoom - lh/2);
      lens.style.backgroundPosition = `${bgX}px ${bgY}px`;
    }

    function onEnter(){ updateBackground(); lens.style.display = 'block'; }
    function onLeave(){ lens.style.display = 'none'; }
    function onWheel(e){
      e.preventDefault();
      const delta = Math.sign(e.deltaY);
      zoom += (delta < 0 ? 0.2 : -0.2);
      zoom = Math.max(minZoom, Math.min(maxZoom, zoom));
      updateBackground();
      moveLens(e);
    }

    img.addEventListener('mouseenter', onEnter, { passive: true });
    img.addEventListener('mousemove', moveLens, { passive: true });
    img.addEventListener('mouseleave', onLeave, { passive: true });
    img.addEventListener('wheel', onWheel, { passive: false });
    // Touch support: show lens while moving finger
    img.addEventListener('touchstart', (e)=>{ onEnter(); moveLens(e); }, { passive: true });
    img.addEventListener('touchmove', moveLens, { passive: true });
    img.addEventListener('touchend', onLeave, { passive: true });

    // Keep background size synced on resize
    window.addEventListener('resize', () => {
      if (window.innerWidth < 992){ lens.style.display = 'none'; return; }
      const nw = Math.max(120, Math.min(220, Math.floor(img.clientWidth * 0.25)));
      lens.style.width = nw + 'px';
      lens.style.height = nw + 'px';
      updateBackground();
    });
  }

  function initMagnifiers(){
    document.querySelectorAll('#productMedia .carousel-item img').forEach(attachMagnifier);
    const car = document.getElementById('productMedia');
    if (car){
      car.addEventListener('slid.bs.carousel', function(){
        // Hide any visible lens when slide changes
        this.querySelectorAll('.magnifier-lens').forEach(l => l.style.display = 'none');
      });
    }
  }

  document.addEventListener('DOMContentLoaded', initMagnifiers);
})();
