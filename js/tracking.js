/**
 * Naukri Dhaba tracking loader.
 *
 * Configure IDs in /tracking-config.json. Build scripts expose that config as
 * window.NAUKRI_DHABA_TRACKING_CONFIG on every page.
 */

(function () {
  'use strict';

  var defaults = {
    googleAdSense: {
      enabled: false,
      publisherId: 'ca-pub-XXXXXXXXXXXXXXXX'
    },
    facebookPixel: {
      enabled: false,
      pixelId: 'XXXXXXXXXXXXXXXXXX'
    },
    microsoftClarity: {
      enabled: false,
      projectId: 'XXXXXXXXXX'
    }
  };

  function mergeConfig(base, overrides) {
    var result = {};
    Object.keys(base).forEach(function (key) {
      result[key] = Object.assign({}, base[key], overrides && overrides[key]);
    });
    return result;
  }

  function loadScript(src, id, callback) {
    if (document.getElementById(id)) {
      return;
    }

    var script = document.createElement('script');
    script.id = id;
    script.async = true;
    script.src = src;
    if (callback) {
      script.onload = callback;
    }
    document.head.appendChild(script);
  }

  var config = mergeConfig(defaults, window.NAUKRI_DHABA_TRACKING_CONFIG || {});

  if (
    config.googleAdSense.enabled &&
    config.googleAdSense.publisherId !== 'ca-pub-XXXXXXXXXXXXXXXX'
  ) {
    var publisherId = config.googleAdSense.publisherId;
    loadScript(
      'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=' + publisherId,
      'adsense-auto'
    );
    document.addEventListener('DOMContentLoaded', function () {
      (window.adsbygoogle = window.adsbygoogle || []).push({
        google_ad_client: publisherId,
        enable_page_level_ads: true
      });
    });
  }

  if (
    config.facebookPixel.enabled &&
    config.facebookPixel.pixelId !== 'XXXXXXXXXXXXXXXXXX'
  ) {
    var pixelId = config.facebookPixel.pixelId;
    !function (f, b, e, v, n, t, s) {
      if (f.fbq) return;
      n = f.fbq = function () {
        n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments);
      };
      if (!f._fbq) f._fbq = n;
      n.push = n;
      n.loaded = true;
      n.version = '2.0';
      n.queue = [];
      t = b.createElement(e);
      t.async = true;
      t.src = v;
      s = b.getElementsByTagName(e)[0];
      s.parentNode.insertBefore(t, s);
    }(window, document, 'script', 'https://connect.facebook.net/en_US/fbevents.js');
    window.fbq('init', pixelId);
    window.fbq('track', 'PageView');
  }

  if (
    config.microsoftClarity.enabled &&
    config.microsoftClarity.projectId !== 'XXXXXXXXXX'
  ) {
    var clarityId = config.microsoftClarity.projectId;
    (function (c, l, a, r, i, t, y) {
      c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
      t = l.createElement(r);
      t.async = 1;
      t.src = 'https://www.clarity.ms/tag/' + i;
      y = l.getElementsByTagName(r)[0];
      y.parentNode.insertBefore(t, y);
    })(window, document, 'clarity', 'script', clarityId);
  }

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
