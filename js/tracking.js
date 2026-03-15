/**
 * ============================================================
 * NAUKRI DHABA - TRACKING CODES MANAGER
 * File: js/tracking.js
 * ============================================================
 *
 * HOW TO USE:
 * 1. Find each section below and paste your tracking code/ID
 * 2. Set enabled: true for any tracker you want to activate
 * 3. This file is already included in ALL pages via <head>
 *
 * TRACKING PLACEMENT: Header (default) - loaded on every page
 * ============================================================
 */

(function () {
  'use strict';

  /* ═══════════════════════════════════════════════════════════
   * CONFIGURATION - Edit values below
   * ═══════════════════════════════════════════════════════════ */
  var CONFIG = {

    /* ----------------------------------------------------------
     * 1. GOOGLE ANALYTICS 4 (GA4)
     *    Get ID from: https://analytics.google.com/
     *    Format: G-XXXXXXXXXX
     * ---------------------------------------------------------- */
    googleAnalytics4: {
      enabled: false,
      measurementId: 'G-XXXXXXXXXX'  /* <-- Replace with your GA4 Measurement ID */
    },

    /* ----------------------------------------------------------
     * 2. GOOGLE TAG MANAGER (GTM)
     *    Get ID from: https://tagmanager.google.com/
     *    Format: GTM-XXXXXXX
     *    Note: If using GTM, you can manage GA4 through GTM instead
     * ---------------------------------------------------------- */
    googleTagManager: {
      enabled: false,
      containerId: 'GTM-XXXXXXX'  /* <-- Replace with your GTM Container ID */
    },

    /* ----------------------------------------------------------
     * 3. GOOGLE ADSENSE (Auto Ads)
     *    Get ID from: https://adsense.google.com/
     *    Format: ca-pub-XXXXXXXXXXXXXXXX
     *    Note: This enables Auto Ads sitewide. Use ads-manager.js
     *          for manual ad slot placement per page.
     * ---------------------------------------------------------- */
    googleAdSense: {
      enabled: false,
      publisherId: 'ca-pub-XXXXXXXXXXXXXXXX'  /* <-- Replace with your AdSense Publisher ID */
    },

    /* ----------------------------------------------------------
     * 4. FACEBOOK PIXEL
     *    Get ID from: https://business.facebook.com/events/manager
     *    Format: 16-digit number
     * ---------------------------------------------------------- */
    facebookPixel: {
      enabled: false,
      pixelId: 'XXXXXXXXXXXXXXXXXX'  /* <-- Replace with your Facebook Pixel ID */
    },

    /* ----------------------------------------------------------
     * 5. MICROSOFT CLARITY (Heatmaps & Session Recordings - FREE)
     *    Get ID from: https://clarity.microsoft.com/
     *    Format: alphanumeric string (e.g. abc123def4)
     * ---------------------------------------------------------- */
    microsoftClarity: {
      enabled: false,
      projectId: 'XXXXXXXXXX'  /* <-- Replace with your Clarity Project ID */
    },

    /* ----------------------------------------------------------
     * 6. GOOGLE SEARCH CONSOLE VERIFICATION
     *    Get from: https://search.google.com/search-console
     *    Add your verification meta tag content here
     * ---------------------------------------------------------- */
    googleSearchConsole: {
      enabled: false,
      verificationCode: 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'  /* <-- GSC verification code */
    },

    /* ----------------------------------------------------------
     * 7. CUSTOM ANALYTICS / OTHER TRACKING
     *    Paste any other tracking snippet here
     * ---------------------------------------------------------- */
    customTracking: {
      enabled: false,
      /* Paste your custom tracking code here: */
      code: ''  /* <code goes here> */
    }

  };

  /* ═══════════════════════════════════════════════════════════
   * LOADER FUNCTIONS - Do not edit below this line
   * ═══════════════════════════════════════════════════════════ */

  function loadScript(src, id, callback) {
    if (document.getElementById(id)) return;
    var s = document.createElement('script');
    s.id = id;
    s.async = true;
    s.src = src;
    if (callback) s.onload = callback;
    document.head.appendChild(s);
  }

  function injectMeta(name, content) {
    var m = document.createElement('meta');
    m.name = name;
    m.content = content;
    document.head.appendChild(m);
  }

  /* ----------------------------------------------------------
   * GOOGLE ANALYTICS 4
   * ---------------------------------------------------------- */
  if (CONFIG.googleAnalytics4.enabled && CONFIG.googleAnalytics4.measurementId !== 'G-XXXXXXXXXX') {
    var GA_ID = CONFIG.googleAnalytics4.measurementId;
    loadScript('https://www.googletagmanager.com/gtag/js?id=' + GA_ID, 'ga4-script', function () {
      window.dataLayer = window.dataLayer || [];
      function gtag() { window.dataLayer.push(arguments); }
      window.gtag = gtag;
      gtag('js', new Date());
      gtag('config', GA_ID, {
        page_title: document.title,
        page_location: window.location.href,
        send_page_view: true
      });
    });
  }

  /* ----------------------------------------------------------
   * GOOGLE TAG MANAGER
   * ---------------------------------------------------------- */
  if (CONFIG.googleTagManager.enabled && CONFIG.googleTagManager.containerId !== 'GTM-XXXXXXX') {
    var GTM_ID = CONFIG.googleTagManager.containerId;
    (function (w, d, s, l, i) {
      w[l] = w[l] || [];
      w[l].push({ 'gtm.start': new Date().getTime(), event: 'gtm.js' });
      var f = d.getElementsByTagName(s)[0],
        j = d.createElement(s),
        dl = l != 'dataLayer' ? '&l=' + l : '';
      j.async = true;
      j.src = 'https://www.googletagmanager.com/gtm.js?id=' + i + dl;
      f.parentNode.insertBefore(j, f);
    })(window, document, 'script', 'dataLayer', GTM_ID);

    /* GTM noscript fallback - inject after body open */
    document.addEventListener('DOMContentLoaded', function () {
      var ns = document.createElement('noscript');
      var iframe = document.createElement('iframe');
      iframe.src = 'https://www.googletagmanager.com/ns.html?id=' + GTM_ID;
      iframe.height = '0';
      iframe.width = '0';
      iframe.style.display = 'none';
      iframe.style.visibility = 'hidden';
      ns.appendChild(iframe);
      document.body.insertBefore(ns, document.body.firstChild);
    });
  }

  /* ----------------------------------------------------------
   * GOOGLE ADSENSE AUTO ADS
   * ---------------------------------------------------------- */
  if (CONFIG.googleAdSense.enabled && CONFIG.googleAdSense.publisherId !== 'ca-pub-XXXXXXXXXXXXXXXX') {
    var AS_PUB = CONFIG.googleAdSense.publisherId;
    loadScript('https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=' + AS_PUB, 'adsense-auto');
    /* Auto Ads init */
    document.addEventListener('DOMContentLoaded', function () {
      (window.adsbygoogle = window.adsbygoogle || []).push({
        google_ad_client: AS_PUB,
        enable_page_level_ads: true
      });
    });
  }

  /* ----------------------------------------------------------
   * FACEBOOK PIXEL
   * ---------------------------------------------------------- */
  if (CONFIG.facebookPixel.enabled && CONFIG.facebookPixel.pixelId !== 'XXXXXXXXXXXXXXXXXX') {
    var FB_ID = CONFIG.facebookPixel.pixelId;
    !function (f, b, e, v, n, t, s) {
      if (f.fbq) return; n = f.fbq = function () {
        n.callMethod ?
          n.callMethod.apply(n, arguments) : n.queue.push(arguments);
      };
      if (!f._fbq) f._fbq = n; n.push = n; n.loaded = !0; n.version = '2.0';
      n.queue = []; t = b.createElement(e); t.async = !0;
      t.src = v; s = b.getElementsByTagName(e)[0];
      s.parentNode.insertBefore(t, s);
    }(window, document, 'script', 'https://connect.facebook.net/en_US/fbevents.js');
    window.fbq('init', FB_ID);
    window.fbq('track', 'PageView');
  }

  /* ----------------------------------------------------------
   * MICROSOFT CLARITY
   * ---------------------------------------------------------- */
  if (CONFIG.microsoftClarity.enabled && CONFIG.microsoftClarity.projectId !== 'XXXXXXXXXX') {
    var CL_ID = CONFIG.microsoftClarity.projectId;
    (function (c, l, a, r, i, t, y) {
      c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
      t = l.createElement(r); t.async = 1;
      t.src = 'https://www.clarity.ms/tag/' + i;
      y = l.getElementsByTagName(r)[0];
      y.parentNode.insertBefore(t, y);
    })(window, document, 'clarity', 'script', CL_ID);
  }

  /* ----------------------------------------------------------
   * GOOGLE SEARCH CONSOLE VERIFICATION
   * ---------------------------------------------------------- */
  if (CONFIG.googleSearchConsole.enabled && CONFIG.googleSearchConsole.verificationCode !== 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX') {
    injectMeta('google-site-verification', CONFIG.googleSearchConsole.verificationCode);
  }

  /* ----------------------------------------------------------
   * CUSTOM TRACKING CODE
   * ---------------------------------------------------------- */
  if (CONFIG.customTracking.enabled && CONFIG.customTracking.code) {
    var div = document.createElement('div');
    div.innerHTML = CONFIG.customTracking.code;
    var scripts = div.querySelectorAll('script');
    scripts.forEach(function (s) {
      var newScript = document.createElement('script');
      if (s.src) {
        newScript.src = s.src;
        newScript.async = true;
      } else {
        newScript.textContent = s.textContent;
      }
      document.head.appendChild(newScript);
    });
  }

  /* ----------------------------------------------------------
   * PAGE VIEW EVENT HELPER
   * Used by other scripts to track events
   * ---------------------------------------------------------- */
  window.NaukriTrack = function (category, action, label) {
    if (window.gtag) {
      window.gtag('event', action, {
        event_category: category,
        event_label: label
      });
    }
    if (window.fbq) {
      window.fbq('trackCustom', action, { category: category, label: label });
    }
  };

})();
