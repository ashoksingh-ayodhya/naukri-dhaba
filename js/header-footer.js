/**
 * Naukri Dhaba — Universal Header & Footer
 *
 * Single source of truth for navigation across ALL pages.
 * Works on desktop and mobile.  Detects current page from
 * window.location.pathname and highlights the active tab.
 *
 * Usage: include <script src="/js/header-footer.js" defer></script>
 *        (or with relative path ../../js/header-footer.js for detail pages)
 */
(function () {
  'use strict';

  /* ── Navigation tabs ─────────────────────────────────────── */
  var NAV = [
    { href: '/latest-jobs.html', label: '💼 Latest Jobs', key: 'jobs' },
    { href: '/results.html',     label: '📊 Results',     key: 'results' },
    { href: '/admit-cards.html', label: '🎫 Admit Cards', key: 'admit-cards' },
    { href: '/resources.html',   label: '📚 Resources',   key: 'resources' }
  ];

  /* ── Detect active tab from the current URL ───────────────── */
  function getActiveKey() {
    var path = window.location.pathname;
    if (path.indexOf('/jobs/') !== -1 || path.indexOf('latest-jobs') !== -1) return 'jobs';
    if (path.indexOf('/results') !== -1) return 'results';
    if (path.indexOf('/admit-cards') !== -1 || path.indexOf('/admit-card') !== -1) return 'admit-cards';
    if (path.indexOf('/resources') !== -1) return 'resources';
    return '';
  }

  /* ── Build header HTML ────────────────────────────────────── */
  function buildHeader() {
    var active = getActiveKey();

    var desktopLinks = NAV.map(function (t) {
      var cls = t.key === active ? ' class="active"' : '';
      return '<a href="' + t.href + '"' + cls + '>' + t.label + '</a>';
    }).join('\n      ');

    var mobileLinks = '<a href="/">🏠 Home</a>\n    ' +
      NAV.map(function (t) {
        return '<a href="' + t.href + '">' + t.label + '</a>';
      }).join('\n    ');

    return '<header class="header">' +
      '<div class="container header__container">' +
        '<a href="/" class="logo">📋 Naukri Dhaba</a>' +
        '<nav class="nav nav--desktop">' + desktopLinks + '</nav>' +
        '<div style="display:flex;gap:1rem;align-items:center;">' +
          '<button class="btn--icon" onclick="toggleDarkMode()" title="Toggle Dark Mode">🌓</button>' +
          '<button class="btn--icon menu-toggle" onclick="toggleMobileMenu()" ' +
            'aria-label="Open menu" style="display:none;font-size:1.5rem;cursor:pointer;background:none;border:none;">☰</button>' +
        '</div>' +
      '</div>' +
      '<div id="menu-overlay" onclick="closeMobileMenu()" ' +
        'style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:1000;"></div>' +
      '<nav class="nav--mobile">' +
        '<button onclick="closeMobileMenu()" ' +
          'style="position:absolute;top:1rem;right:1rem;font-size:1.5rem;cursor:pointer;background:none;border:none;color:var(--text);">✕</button>' +
        mobileLinks +
      '</nav>' +
      '<style>.menu-toggle{display:none!important}@media(max-width:768px){.nav--desktop{display:none}.menu-toggle{display:block!important}}</style>' +
    '</header>';
  }

  /* ── Build footer HTML ────────────────────────────────────── */
  function buildFooter() {
    return '<footer class="footer">' +
      '<div class="container">' +
        '<div class="footer__grid">' +
          '<div>' +
            '<h3 class="footer__title">📋 Naukri Dhaba</h3>' +
            '<p style="color:#ccc;font-size:.9rem;line-height:1.6;">Independent government job updates, result tracking, and admit card alerts for India.</p>' +
            '<a href="https://t.me/naukridhaba" class="share-btn share-btn--telegram" style="margin-top:1rem;display:inline-block;">Join Telegram</a>' +
          '</div>' +
          '<div>' +
            '<h3 class="footer__title">Quick Links</h3>' +
            '<div class="footer__links">' +
              '<a href="/latest-jobs.html">Latest Jobs</a>' +
              '<a href="/results.html">Results</a>' +
              '<a href="/admit-cards.html">Admit Cards</a>' +
              '<a href="/resources.html">Resources</a>' +
            '</div>' +
          '</div>' +
          '<div>' +
            '<h3 class="footer__title">Tools</h3>' +
            '<div class="footer__links">' +
              '<a href="/eligibility-calculator.html">Eligibility Calculator</a>' +
              '<a href="/study-planner.html">Study Planner</a>' +
              '<a href="/previous-papers.html">Previous Papers</a>' +
              '<a href="/syllabus.html">Syllabus</a>' +
              '<a href="/cut-off-marks.html">Cut-off Marks</a>' +
            '</div>' +
          '</div>' +
          '<div>' +
            '<h3 class="footer__title">State Jobs</h3>' +
            '<div class="state-list">' +
              '<a href="/state/uttar-pradesh.html">Uttar Pradesh</a>' +
              '<a href="/state/bihar.html">Bihar</a>' +
              '<a href="/state/rajasthan.html">Rajasthan</a>' +
              '<a href="/state/madhya-pradesh.html">Madhya Pradesh</a>' +
              '<a href="/state/haryana.html">Haryana</a>' +
              '<a href="/state/jharkhand.html">Jharkhand</a>' +
              '<a href="/state/delhi.html">Delhi</a>' +
              '<a href="/state/maharashtra.html">Maharashtra</a>' +
              '<a href="/state/gujarat.html">Gujarat</a>' +
              '<a href="/state/punjab.html">Punjab</a>' +
            '</div>' +
          '</div>' +
        '</div>' +
        '<div class="footer__bottom">' +
          '<p>&copy; 2026 Naukri Dhaba. All rights reserved.</p>' +
          '<p>Disclaimer: We are not affiliated with any government organization. We only provide information.</p>' +
        '</div>' +
      '</div>' +
    '</footer>';
  }

  /* ── Replace header & footer on DOMContentLoaded ──────────── */
  function replaceHeaderFooter() {
    var header = document.querySelector('header.header');
    if (header) {
      header.outerHTML = buildHeader();
    }

    /* Replace the static footer OR the old #site-footer div */
    var footer = document.querySelector('footer.footer');
    var siteFooter = document.getElementById('site-footer');
    if (footer) {
      footer.outerHTML = buildFooter();
    } else if (siteFooter) {
      siteFooter.outerHTML = buildFooter();
    }

    /* Re-bind mobile menu close on nav links */
    document.querySelectorAll('.nav--mobile a').forEach(function (a) {
      a.addEventListener('click', function () {
        if (typeof closeMobileMenu === 'function') closeMobileMenu();
      });
    });
  }

  /* Run after DOM is ready */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', replaceHeaderFooter);
  } else {
    replaceHeaderFooter();
  }
})();
