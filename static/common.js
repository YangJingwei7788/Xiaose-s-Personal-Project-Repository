/* 公共工具：API 封装、Toast、预约弹窗、侧边栏、公共设置、品类卡片、自动轮播 */
(function () {
  'use strict';

  var isAdmin = document.body && document.body.getAttribute('data-page') === 'admin';
  var carouselImages = []; // 后台上传的自定义轮播图（URL 数组）
  var carouselCaptions = []; // 后台上传的自定义轮播文字（每张图 小标签/标题/描述）

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  /* ---------- Toast 提示 ---------- */
  function toast(msg, ok) {
    var box = document.getElementById('toast-box');
    if (!box) {
      box = document.createElement('div');
      box.id = 'toast-box';
      document.body.appendChild(box);
    }
    var t = document.createElement('div');
    t.className = 'toast ' + (ok === false ? 'err' : 'ok');
    t.textContent = msg;
    box.appendChild(t);
    requestAnimationFrame(function () { t.classList.add('show'); });
    setTimeout(function () {
      t.classList.remove('show');
      setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 300);
    }, 2600);
  }

  /* ---------- API 封装 ---------- */
  async function api(url, options) {
    options = options || {};
    var headers = Object.assign({ 'Content-Type': 'application/json' }, options.headers || {});
    var res = await fetch(url, Object.assign({}, options, { headers: headers }));
    var json = null;
    try { json = await res.json(); } catch (e) { /* 非 JSON 响应 */ }
    if (!res.ok) {
      var detail = json && json.detail;
      var msg = detail ? (typeof detail === 'string' ? detail : JSON.stringify(detail)) : ('请求失败（' + res.status + '）');
      var err = new Error(msg);
      err.status = res.status;
      err.body = json;
      throw err;
    }
    return json;
  }

  /* ---------- 品类卡片 ---------- */
  function categoryCard(c, icon, tagClass, tagText) {
    if (c && c.image) {
      return '<div class="card card-photo" style="background-image:url(\'' + c.image + '\')">' +
        '<div class="card-photo-mask"></div>' +
        '<div class="card-photo-body">' +
        '<span class="tag ' + tagClass + '">' + tagText + '</span>' +
        '<h3>' + escapeHtml(c.name) + '</h3>' +
        '</div></div>';
    }
    return '<div class="card">' +
      '<div class="icon">' + icon + '</div>' +
      '<h3>' + escapeHtml(c.name) + '</h3>' +
      '<span class="tag ' + tagClass + '">' + tagText + '</span>' +
      '</div>';
  }

  /* ---------- 预约弹窗 ---------- */
  function injectModal() {
    var wrap = document.createElement('div');
    wrap.id = 'book-modal';
    wrap.className = 'modal-overlay';
    wrap.innerHTML =
      '<div class="modal">' +
        '<button type="button" class="close" data-close aria-label="关闭">&times;</button>' +
        '<h3>预约咨询</h3>' +
        '<p class="sub">留下您的联系方式，我们将尽快与您联系</p>' +
        '<form id="book-form">' +
          '<div class="field"><label>您的姓名 *</label><input name="name" type="text" maxlength="50" required placeholder="请输入姓名"></div>' +
          '<div class="field"><label>联系电话 *</label><input name="phone" type="tel" maxlength="11" required pattern="1[3-9][0-9]{9}" placeholder="请输入 11 位手机号" title="请输入正确的手机号"></div>' +
          '<div class="field"><label>预约类型 *</label>' +
            '<div class="radio-row">' +
              '<label><input type="radio" name="book_type" value="1" checked> 回收预约</label>' +
              '<label><input type="radio" name="book_type" value="2"> 购买咨询</label>' +
            '</div>' +
          '</div>' +
          '<div class="field"><label>需求描述</label><textarea name="need_content" maxlength="500" placeholder="如：想回收一张旧沙发 / 想购买二手实木床，方便的上门时间等"></textarea></div>' +
          '<button type="submit" class="btn btn-primary" style="width:100%">提交预约</button>' +
        '</form>' +
      '</div>';
    document.body.appendChild(wrap);
    wrap.addEventListener('click', function (e) {
      if (e.target === wrap || e.target.closest('[data-close]')) closeBookModal();
    });
    document.getElementById('book-form').addEventListener('submit', submitBook);
  }

  function openBookModal(preType) {
    var wrap = document.getElementById('book-modal');
    if (!wrap) return;
    if (preType) {
      var radio = wrap.querySelector('input[name=book_type][value="' + preType + '"]');
      if (radio) radio.checked = true;
    }
    wrap.classList.add('show');
    setTimeout(function () {
      var input = wrap.querySelector('input[name=name]');
      if (input) input.focus();
    }, 80);
  }

  function closeBookModal() {
    var wrap = document.getElementById('book-modal');
    if (wrap) wrap.classList.remove('show');
  }

  async function submitBook(e) {
    e.preventDefault();
    var form = e.target;
    var btn = form.querySelector('button[type=submit]');
    btn.disabled = true;
    var typeEl = form.querySelector('input[name=book_type]:checked');
    var data = {
      name: form.name.value.trim(),
      phone: form.phone.value.trim(),
      book_type: typeEl ? parseInt(typeEl.value, 10) : 1,
      need_content: form.need_content.value.trim()
    };
    try {
      var json = await api('/api/book', { method: 'POST', body: JSON.stringify(data) });
      toast(json.message || '预约提交成功');
      form.reset();
      closeBookModal();
    } catch (err) {
      toast(err.message, false);
    } finally {
      btn.disabled = false;
    }
  }

  /* ---------- 左侧侧边栏（仅客户页面） ---------- */
  function injectSidebar() {
    var page = document.body.getAttribute('data-page');
    var sidebar = document.createElement('aside');
    sidebar.className = 'sidebar';
    sidebar.id = 'sidebar';
    sidebar.setAttribute('aria-label', '导航');
    sidebar.innerHTML =
      '<a class="sidebar-brand" href="index.html">' +
        '<span class="logo">♻</span>' +
        '<span class="logo-text" data-site="shop_name">二手家具</span>' +
      '</a>' +
      '<nav class="sidebar-nav">' +
        '<a href="index.html" data-nav="home" class="nav-item">主页</a>' +
        '<a href="recycle.html" data-nav="recycle" class="nav-item">回收</a>' +
        '<a href="sell.html" data-nav="sell" class="nav-item">售卖</a>' +
        '<button type="button" class="nav-item js-book-open" data-book-type="1">预约</button>' +
        '<a href="about.html" data-nav="about" class="nav-item">门店介绍</a>' +
      '</nav>' +
      '<div class="sidebar-foot">' +
        '<div class="sidebar-card">' +
          '<p class="muted" style="font-size:12px">服务热线</p>' +
          '<p class="sidebar-phone" data-site="phone">138-0000-0000</p>' +
          '<button type="button" class="btn btn-primary btn-sm js-book-open" data-book-type="1" style="width:100%;margin-top:10px">立即预约</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(sidebar);

    var mobileBar = document.createElement('div');
    mobileBar.className = 'mobile-bar';
    mobileBar.innerHTML =
      '<div class="mobile-top">' +
        '<span class="mobile-brand" data-site="shop_name">二手家具</span>' +
        '<button type="button" class="btn btn-primary btn-sm js-book-open" data-book-type="1">预约</button>' +
      '</div>' +
      '<nav class="mobile-nav">' +
        '<a href="index.html" data-nav="home" class="mnav-item">主页</a>' +
        '<a href="recycle.html" data-nav="recycle" class="mnav-item">回收</a>' +
        '<a href="sell.html" data-nav="sell" class="mnav-item">售卖</a>' +
        '<button type="button" class="mnav-item js-book-open" data-book-type="1">预约</button>' +
        '<a href="about.html" data-nav="about" class="mnav-item">门店介绍</a>' +
      '</nav>';
    document.body.insertBefore(mobileBar, document.body.firstChild);
    document.body.classList.add('has-sidebar');

    // 高亮当前页（桌面侧边栏 + 手机顶部导航）
    var items = document.querySelectorAll('[data-nav]');
    for (var i = 0; i < items.length; i++) {
      if (items[i].getAttribute('data-nav') === page) items[i].classList.add('active');
    }

    // 手机端导航位于顶部，无需抽屉开关
  }

  /* ---------- 轮播图 ---------- */
  var SLIDES = {
    home: [
      { img: 'img/slide-1.jpg', kicker: '上门回收 · 实惠售卖', title: '让旧家具焕发新生', text: '专业回收各类家具与家居用品，精选好物实惠售卖，让闲置重新流转。', btns: [{ label: '立即预约', type: 'book', bookType: 1 }, { label: '查看回收品类', type: 'link', href: 'recycle.html' }] },
      { img: 'img/slide-2.jpg', kicker: '品类齐全', title: '一站式回收 · 售卖服务', text: '床、柜、沙发、桌椅、家电等全屋品类，一次解决所有需求。', btns: [{ label: '查看售卖品类', type: 'link', href: 'sell.html' }, { label: '立即预约', type: 'book', bookType: 1 }] },
      { img: 'img/slide-3.jpg', kicker: '精选好物', title: '优质二手家具 放心选购', text: '在售家具均经清洁整理，成色好、性价比高，欢迎预约看货。', btns: [{ label: '预约看货', type: 'book', bookType: 2 }, { label: '门店介绍', type: 'link', href: 'about.html' }] },
      { img: 'img/slide-4.jpg', kicker: '免费上门', title: '免费上门回收', text: '市区内免费看货、上门回收，大件家具协助搬运，结算透明。', btns: [{ label: '预约回收', type: 'book', bookType: 1 }] },
      { img: 'img/slide-5.jpg', kicker: '诚信经营', title: '童叟无欺 价格公道', text: '坚持诚信经营，回收与售卖价格公开透明，让买卖都放心。', btns: [{ label: '立即预约', type: 'book', bookType: 1 }] },
      { img: 'img/slide-6.jpg', kicker: '全屋家具', title: '床、柜、沙发、桌椅 样样都收', text: '家具、家居、配套家电均可上门回收，数量不限。', btns: [{ label: '预约回收', type: 'book', bookType: 1 }] },
      { img: 'img/slide-7.jpg', kicker: '办公 / 搬家', title: '办公家具与搬家处理', text: '公司搬迁、店铺装修、出租屋清退，一站式上门处理。', btns: [{ label: '立即预约', type: 'book', bookType: 1 }] },
      { img: 'img/slide-8.jpg', kicker: '放心选购', title: '实惠好物 满意再下单', text: '到店选购或预约看货，满意再成交，售后无忧。', btns: [{ label: '预约看货', type: 'book', bookType: 2 }] }
    ],
    recycle: [
      { img: 'img/slide-2.jpg', kicker: '回收品类', title: '上门回收各类家具', text: '床、沙发、衣柜、桌椅、家电等均可上门回收。', btns: [{ label: '预约回收', type: 'book', bookType: 1 }] },
      { img: 'img/slide-5.jpg', kicker: '免费上门', title: '免费上门看货估价', text: '电话或在线预约，专人上门估价，成交即结算。', btns: [{ label: '预约回收', type: 'book', bookType: 1 }] },
      { img: 'img/slide-6.jpg', kicker: '数量不限', title: '一站式回收处理', text: '家具、家居、配套家电，数量不限、随叫随到。', btns: [{ label: '立即预约', type: 'book', bookType: 1 }] }
    ],
    sell: [
      { img: 'img/slide-8.jpg', kicker: '售卖品类', title: '品类丰富 实惠好物', text: '在售二手家具均经清洁整理，品类丰富、性价比高。', btns: [{ label: '预约看货', type: 'book', bookType: 2 }] },
      { img: 'img/slide-3.jpg', kicker: '精选床具', title: '舒适床具 成色好', text: '床架、床垫等精选好物，舒适耐用、价格实惠。', btns: [{ label: '预约看货', type: 'book', bookType: 2 }] },
      { img: 'img/slide-1.jpg', kicker: '客厅家具', title: '客厅家具一应俱全', text: '沙发、茶几、电视柜等客厅好物，欢迎到店选购。', btns: [{ label: '立即预约', type: 'book', bookType: 2 }] }
    ],
    about: [
      { img: 'img/slide-4.jpg', kicker: '关于我们', title: '专注二手家具 诚信经营', text: '多年回收与售卖经验，童叟无欺，服务贴心。', btns: [{ label: '立即预约', type: 'book', bookType: 1 }] },
      { img: 'img/slide-7.jpg', kicker: '上门服务', title: '市区免费上门服务', text: '免费上门看货、回收，大件家具协助搬运。', btns: [{ label: '立即预约', type: 'book', bookType: 1 }] },
      { img: 'img/slide-5.jpg', kicker: '服务流程', title: '预约 → 估价 → 成交 → 结算', text: '流程透明高效，回收结算快速放心。', btns: [{ label: '立即预约', type: 'book', bookType: 1 }] }
    ]
  };

  function renderCarousel() {
    var el = document.querySelector('[data-carousel]');
    if (!el) return;
    el.innerHTML = '';
    el.classList.remove('is-small');
    var page = document.body.getAttribute('data-page');
    if (page !== 'home') el.classList.add('is-small');

    var defaults = SLIDES[page] || SLIDES.home;
    var images = carouselImages.length ? carouselImages : defaults.map(function (s) { return s.img; });
    var slides = images.map(function (img, i) {
      var base = defaults[i % defaults.length];
      var cap = carouselCaptions[i];
      return {
        img: img,
        kicker: cap && cap.kicker != null ? cap.kicker : (base.kicker || ''),
        title: cap && cap.title ? cap.title : base.title,
        text: cap && cap.text != null ? cap.text : (base.text || ''),
        btns: base.btns || []
      };
    });

    var track = document.createElement('div');
    track.className = 'carousel-track';
    slides.forEach(function (s) {
      var btns = (s.btns || []).map(function (b) {
        if (b.type === 'link') {
          return '<a class="btn btn-white" href="' + b.href + '">' + escapeHtml(b.label) + '</a>';
        }
        return '<button type="button" class="btn btn-glass js-book-open" data-book-type="' + b.bookType + '">' + escapeHtml(b.label) + '</button>';
      }).join('');
      var slide = document.createElement('div');
      slide.className = 'carousel-slide';
      slide.innerHTML =
        '<img src="' + s.img + '" alt="' + escapeHtml(s.title) + '" loading="lazy">' +
        '<div class="carousel-scrim"></div>' +
        '<div class="carousel-caption">' +
          (s.kicker ? '<span class="kicker">' + escapeHtml(s.kicker) + '</span>' : '') +
          '<h1>' + escapeHtml(s.title) + '</h1>' +
          (s.text ? '<p>' + escapeHtml(s.text) + '</p>' : '') +
          '<div class="btns">' + btns + '</div>' +
        '</div>';
      track.appendChild(slide);
    });
    el.appendChild(track);

    var dots = document.createElement('div');
    dots.className = 'carousel-dots';
    slides.forEach(function (_, i) {
      var d = document.createElement('button');
      d.type = 'button';
      d.className = 'carousel-dot' + (i === 0 ? ' active' : '');
      d.setAttribute('aria-label', '第 ' + (i + 1) + ' 张');
      d.addEventListener('click', function () { go(i); restart(); });
      dots.appendChild(d);
    });
    el.appendChild(dots);

    var prev = document.createElement('button');
    prev.type = 'button'; prev.className = 'carousel-arrow prev'; prev.textContent = '‹'; prev.setAttribute('aria-label', '上一张');
    var next = document.createElement('button');
    next.type = 'button'; next.className = 'carousel-arrow next'; next.textContent = '›'; next.setAttribute('aria-label', '下一张');
    prev.addEventListener('click', function () { go(cur - 1); restart(); });
    next.addEventListener('click', function () { go(cur + 1); restart(); });
    el.appendChild(prev);
    el.appendChild(next);

    var cur = 0, timer = null;
    function go(i) {
      var n = slides.length;
      cur = ((i % n) + n) % n;
      track.style.transform = 'translateX(-' + cur * 100 + '%)';
      var dotEls = el.querySelectorAll('.carousel-dot');
      for (var k = 0; k < dotEls.length; k++) dotEls[k].classList.toggle('active', k === cur);
    }
    function start() { if (!timer) timer = setInterval(function () { go(cur + 1); }, 4500); }
    function stop() { if (timer) { clearInterval(timer); timer = null; } }
    function restart() { stop(); start(); }

    start();
    el.addEventListener('mouseenter', stop);
    el.addEventListener('mouseleave', start);

    var x0 = null;
    el.addEventListener('touchstart', function (e) { x0 = e.touches[0].clientX; stop(); }, { passive: true });
    el.addEventListener('touchend', function (e) {
      if (x0 === null) return;
      var dx = e.changedTouches[0].clientX - x0;
      if (Math.abs(dx) > 40) go(dx < 0 ? cur + 1 : cur - 1);
      x0 = null;
      restart();
    }, { passive: true });
  }

  /* ---------- 公共设置 ---------- */
  async function loadCommon() {
    try {
      var json = await api('/api/settings/public');
      var site = json.data || {};
      window.SITE = site;
      document.querySelectorAll('[data-site]').forEach(function (el) {
        var key = el.getAttribute('data-site');
        if (site[key] == null) return;
        if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') { el.value = site[key]; }
        else { el.textContent = site[key]; }
      });
      var adv = document.getElementById('service-advantages-list');
      if (adv && site.service_advantages) {
        adv.innerHTML = site.service_advantages.split('\n').filter(function (s) { return s.trim(); })
          .map(function (s) { return '<li>' + escapeHtml(s.trim()) + '</li>'; }).join('');
      }
      var flow = document.getElementById('service-flow-list');
      if (flow && site.service_flow) {
        flow.innerHTML = site.service_flow.split('\n').filter(function (s) { return s.trim(); })
          .map(function (s, i) { return '<li><span class="num">' + (i + 1) + '</span>' + escapeHtml(s.trim()) + '</li>'; }).join('');
      }
      if (site.shop_name) {
        var pageTitle = document.body.getAttribute('data-title') || '业务展示';
        document.title = site.shop_name + ' - ' + pageTitle;

      }
      // 自定义轮播图：上传后重建轮播
      try {
        var arr = JSON.parse(site.carousel_images || '[]');
        carouselImages = Array.isArray(arr) ? arr.filter(function (x) { return x && x.trim(); }) : [];
      } catch (e) { carouselImages = []; }
      try {
        var caps = JSON.parse(site.carousel_captions || '[]');
        carouselCaptions = Array.isArray(caps) ? caps : [];
      } catch (e) { carouselCaptions = []; }
      if ((carouselImages.length || carouselCaptions.length) && document.querySelector('[data-carousel]')) {
        renderCarousel();
      }
    } catch (e) { /* 静默：不影响页面主体 */ }
  }

  /* ---------- 对外暴露 ---------- */
  window.FS = {
    api: api, toast: toast, openBookModal: openBookModal, closeBookModal: closeBookModal,
    loadCommon: loadCommon, isAdmin: isAdmin, escapeHtml: escapeHtml,
    renderCarousel: renderCarousel, categoryCard: categoryCard,
    homeSlides: SLIDES.home
  };

  if (isAdmin) return; // 后台页由自身脚本接管

  document.addEventListener('DOMContentLoaded', function () {
    renderCarousel();
    injectModal();
    injectSidebar();
    loadCommon();
    document.addEventListener('click', function (e) {
      var btn = e.target.closest('.js-book-open');
      if (btn) {
        e.preventDefault();
        openBookModal(btn.getAttribute('data-book-type') || 1);
      }
    });
  });
})();