/**
 * ============================================================
 * NAUKRI DHABA - ADS MANAGER
 * File: js/ads-manager.js
 * ============================================================
 *
 * HOW TO USE:
 * 1. Set your AdSense Publisher ID in ADSENSE_PUBLISHER_ID
 * 2. Set each slot's data-slot-id in the SLOTS section
 * 3. Enable/disable ads per page type and position
 * 4. For affiliate links, update AFFILIATE section
 *
 * AD PLACEMENTS MANAGED:
 *  - header-banner     (728x90 Leaderboard) - after hero section
 *  - sidebar-top       (300x250 Rectangle) - top of sidebar
 *  - sidebar-bottom    (300x250 Rectangle) - bottom of sidebar
 *  - content-top       (336x280 Large Rectangle) - top of article
 *  - content-mid       (728x90 or 336x280) - middle of article
 *  - content-bottom    (728x90 Leaderboard) - end of article
 *  - mobile-banner     (320x50 Mobile Banner) - mobile only
 * ============================================================
 */

(function () {
  'use strict';

  /* ═══════════════════════════════════════════════════════════
   * CONFIGURATION - Edit values below
   * ═══════════════════════════════════════════════════════════ */

  /* ----------------------------------------------------------
   * GOOGLE ADSENSE PUBLISHER ID
   * Get from: https://adsense.google.com/
   * Format: ca-pub-XXXXXXXXXXXXXXXX
   * ---------------------------------------------------------- */
  var ADSENSE_PUBLISHER_ID = 'ca-pub-XXXXXXXXXXXXXXXX';  /* <-- Replace with your Publisher ID */

  /* ----------------------------------------------------------
   * AD SLOTS CONFIGURATION
   * Each slot has:
   *   - slotId: AdSense Ad Unit ID
   *   - size: [width, height]
   *   - enabled: true/false
   *   - customCode: paste custom ad code here (overrides AdSense)
   * ---------------------------------------------------------- */
  var SLOTS = {

    /* Header Banner - 728x90 Leaderboard (desktop) / 320x50 (mobile) */
    'header-banner': {
      enabled: false,
      slotId: 'XXXXXXXXXX',  /* <-- Replace with your AdSense slot ID */
      size: [728, 90],
      mobileFallbackSize: [320, 50],
      customCode: ''  /* <code goes here> - Paste custom ad code OR leave blank for AdSense */
    },

    /* Sidebar Top - 300x250 Medium Rectangle */
    'sidebar-top': {
      enabled: false,
      slotId: 'XXXXXXXXXX',  /* <-- Replace with your AdSense slot ID */
      size: [300, 250],
      customCode: ''  /* <code goes here> */
    },

    /* Sidebar Bottom - 300x250 Medium Rectangle */
    'sidebar-bottom': {
      enabled: false,
      slotId: 'XXXXXXXXXX',  /* <-- Replace with your AdSense slot ID */
      size: [300, 250],
      customCode: ''  /* <code goes here> */
    },

    /* Content Top - 336x280 Large Rectangle (after breadcrumb) */
    'content-top': {
      enabled: false,
      slotId: 'XXXXXXXXXX',  /* <-- Replace with your AdSense slot ID */
      size: [336, 280],
      customCode: ''  /* <code goes here> */
    },

    /* Content Middle - shown halfway through article */
    'content-mid': {
      enabled: false,
      slotId: 'XXXXXXXXXX',  /* <-- Replace with your AdSense slot ID */
      size: [728, 90],
      customCode: ''  /* <code goes here> */
    },

    /* Content Bottom - 728x90 after article ends */
    'content-bottom': {
      enabled: false,
      slotId: 'XXXXXXXXXX',  /* <-- Replace with your AdSense slot ID */
      size: [728, 90],
      customCode: ''  /* <code goes here> */
    },

    /* Mobile Banner - shown only on mobile */
    'mobile-banner': {
      enabled: false,
      slotId: 'XXXXXXXXXX',  /* <-- Replace with your AdSense slot ID */
      size: [320, 50],
      mobileOnly: true,
      customCode: ''  /* <code goes here> */
    }

  };

  /* ----------------------------------------------------------
   * PAGE-LEVEL AD CONTROL
   * Control which ad positions appear on each page type
   * Page types: 'home', 'jobs-list', 'results-list',
   *             'admit-cards-list', 'job-detail',
   *             'result-detail', 'admit-card-detail', 'other'
   * ---------------------------------------------------------- */
  var PAGE_AD_RULES = {
    'home': {
      'header-banner': true,
      'sidebar-top': true,
      'sidebar-bottom': true,
      'content-top': false,
      'content-mid': false,
      'content-bottom': true,
      'mobile-banner': true
    },
    'jobs-list': {
      'header-banner': true,
      'sidebar-top': true,
      'sidebar-bottom': true,
      'content-top': false,
      'content-mid': true,
      'content-bottom': true,
      'mobile-banner': true
    },
    'results-list': {
      'header-banner': true,
      'sidebar-top': true,
      'sidebar-bottom': true,
      'content-mid': true,
      'content-bottom': true,
      'mobile-banner': true
    },
    'admit-cards-list': {
      'header-banner': true,
      'sidebar-top': true,
      'sidebar-bottom': true,
      'content-mid': true,
      'content-bottom': true,
      'mobile-banner': true
    },
    'job-detail': {
      'header-banner': true,
      'sidebar-top': true,
      'sidebar-bottom': true,
      'content-top': true,
      'content-mid': true,
      'content-bottom': true,
      'mobile-banner': true
    },
    'result-detail': {
      'header-banner': true,
      'sidebar-top': true,
      'sidebar-bottom': true,
      'content-top': false,
      'content-mid': false,
      'content-bottom': true,
      'mobile-banner': true
    },
    'admit-card-detail': {
      'header-banner': true,
      'sidebar-top': true,
      'sidebar-bottom': true,
      'content-top': false,
      'content-mid': false,
      'content-bottom': true,
      'mobile-banner': true
    },
    'other': {
      'header-banner': true,
      'sidebar-top': true,
      'sidebar-bottom': true,
      'content-bottom': true,
      'mobile-banner': true
    }
  };

  /* ----------------------------------------------------------
   * AFFILIATE MARKETING CONFIGURATION
   * Add your affiliate links here
   * ---------------------------------------------------------- */
  var AFFILIATE = {
    enabled: false,

    /* Udemy affiliate */
    udemy: {
      enabled: false,
      affiliateId: 'XXXXXXXXXX',  /* <-- Replace with your Udemy affiliate ID */
      /* Relevant course links for govt job aspirants */
      courses: [
        /* <code goes here> - Add course URLs with your affiliate tags */
      ]
    },

    /* Amazon affiliate (for books, study material) */
    amazon: {
      enabled: false,
      associatesId: 'naukridhaba-21',  /* <-- Replace with your Amazon Associates ID */
      /* Relevant book links */
      books: [
        /* <code goes here> - Add book ASINs or URLs */
      ]
    },

    /* Testbook / Unacademy / other EdTech affiliates */
    edtech: {
      enabled: false,
      /* <code goes here> - Add EdTech affiliate configurations */
      partners: []
    }
  };

  /* ═══════════════════════════════════════════════════════════
   * AD RENDERING ENGINE - Do not edit below this line
   * ═══════════════════════════════════════════════════════════ */

  /* Detect current page type */
  function getPageType() {
    var path = window.location.pathname;
    if (path === '/' || path.indexOf('index.html') > -1) return 'home';
    if (path.indexOf('latest-jobs.html') > -1) return 'jobs-list';
    if (path.indexOf('results.html') > -1 && path.indexOf('/results/') === -1) return 'results-list';
    if (path.indexOf('admit-cards.html') > -1 && path.indexOf('/admit-cards/') === -1) return 'admit-cards-list';
    if (path.indexOf('/jobs/') > -1) return 'job-detail';
    if (path.indexOf('/results/') > -1) return 'result-detail';
    if (path.indexOf('/admit-cards/') > -1) return 'admit-card-detail';
    return 'other';
  }

  var isMobile = window.innerWidth < 768;
  var pageType = getPageType();
  var pageRules = PAGE_AD_RULES[pageType] || PAGE_AD_RULES['other'];

  /* Render AdSense unit */
  function renderAdSense(container, slot) {
    if (ADSENSE_PUBLISHER_ID === 'ca-pub-XXXXXXXXXXXXXXXX') {
      renderPlaceholder(container, slot);
      return;
    }
    var size = (isMobile && slot.mobileFallbackSize) ? slot.mobileFallbackSize : slot.size;
    var ins = document.createElement('ins');
    ins.className = 'adsbygoogle';
    ins.style.display = 'inline-block';
    ins.style.width = size[0] + 'px';
    ins.style.height = size[1] + 'px';
    ins.setAttribute('data-ad-client', ADSENSE_PUBLISHER_ID);
    ins.setAttribute('data-ad-slot', slot.slotId);
    container.innerHTML = '';
    container.appendChild(ins);
    try { (window.adsbygoogle = window.adsbygoogle || []).push({}); } catch (e) { }
  }

  /* Render custom ad code */
  function renderCustomCode(container, slot) {
    container.innerHTML = slot.customCode;
    /* Execute any scripts in custom code */
    var scripts = container.querySelectorAll('script');
    scripts.forEach(function (s) {
      var ns = document.createElement('script');
      if (s.src) { ns.src = s.src; ns.async = true; }
      else { ns.textContent = s.textContent; }
      s.parentNode.replaceChild(ns, s);
    });
  }

  /* Render placeholder (when ads not configured) */
  function renderPlaceholder(container, slot) {
    var size = (isMobile && slot.mobileFallbackSize) ? slot.mobileFallbackSize : slot.size;
    container.style.minHeight = size[1] + 'px';
    container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:' + size[1] + 'px;color:#999;font-size:0.75rem;border:2px dashed #ccc;background:#f9f9f9;">Advertisement ' + size[0] + 'x' + size[1] + '</div>';
  }

  /* Main render function for each ad container */
  function renderAd(container) {
    var slotName = container.getAttribute('data-ad-slot') || container.getAttribute('data-slot');
    if (!slotName) return;

    var slot = SLOTS[slotName];
    if (!slot) return;

    /* Check page-level rules */
    if (pageRules[slotName] === false) {
      container.style.display = 'none';
      return;
    }

    /* Check mobile-only */
    if (slot.mobileOnly && !isMobile) {
      container.style.display = 'none';
      return;
    }

    /* Check if slot is enabled */
    if (!slot.enabled) {
      renderPlaceholder(container, slot);
      return;
    }

    /* Render appropriate ad type */
    if (slot.customCode && slot.customCode.trim()) {
      renderCustomCode(container, slot);
    } else {
      renderAdSense(container, slot);
    }
  }

  /* Initialize all ad containers on page */
  function init() {
    var adContainers = document.querySelectorAll('.nd-ad, [data-ad-slot], [data-slot]');
    adContainers.forEach(renderAd);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  /* Expose for manual use */
  window.NaukriAds = {
    render: renderAd,
    getPageType: getPageType,
    config: { SLOTS: SLOTS, PAGE_AD_RULES: PAGE_AD_RULES, AFFILIATE: AFFILIATE }
  };

})();
