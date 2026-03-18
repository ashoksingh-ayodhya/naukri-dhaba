/**
 * Naukri Dhaba tracking loader.
 *
 * Configure IDs in /tracking-config.json. Build scripts expose that config as
 * window.NAUKRI_DHABA_TRACKING_CONFIG on every page.
 */

(function () {
  'use strict';

  var defaults = {
    consentMode: {
      enabled: false,
      storageKey: 'nd_consent_v1',
      defaultMode: 'reject',
      waitForUpdateMs: 500,
      bannerEnabled: true
    },
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

  function ensureGtag() {
    window.dataLayer = window.dataLayer || [];
    if (!window.gtag) {
      window.gtag = function () {
        window.dataLayer.push(arguments);
      };
    }
  }

  function consentStateFromMode(mode) {
    var denied = {
      ad_storage: 'denied',
      analytics_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied',
      functionality_storage: 'granted',
      security_storage: 'granted',
      personalization_storage: 'denied'
    };
    if (mode === 'analytics') {
      return {
        ad_storage: 'denied',
        analytics_storage: 'granted',
        ad_user_data: 'denied',
        ad_personalization: 'denied',
        functionality_storage: 'granted',
        security_storage: 'granted',
        personalization_storage: 'denied'
      };
    }
    if (mode === 'all') {
      return {
        ad_storage: 'granted',
        analytics_storage: 'granted',
        ad_user_data: 'granted',
        ad_personalization: 'granted',
        functionality_storage: 'granted',
        security_storage: 'granted',
        personalization_storage: 'granted'
      };
    }
    return denied;
  }

  function readConsentMode(storageKey) {
    try {
      var raw = window.localStorage.getItem(storageKey);
      if (!raw) {
        return '';
      }
      var parsed = JSON.parse(raw);
      return parsed && parsed.mode ? parsed.mode : '';
    } catch (err) {
      return '';
    }
  }

  function writeConsentMode(storageKey, mode) {
    try {
      window.localStorage.setItem(storageKey, JSON.stringify({
        mode: mode,
        updatedAt: new Date().toISOString()
      }));
    } catch (err) {
      return;
    }
  }

  function applyConsentUpdate(mode) {
    ensureGtag();
    var state = consentStateFromMode(mode);
    window.NAUKRI_DHABA_CONSENT_MODE = mode;
    window.NAUKRI_DHABA_CONSENT_STATE = state;
    window.gtag('consent', 'update', state);
    return state;
  }

  function removeConsentBanner() {
    var banner = document.getElementById('nd-consent-banner');
    if (banner) {
      banner.remove();
    }
  }

  function renderConsentBanner(consentConfig) {
    if (!consentConfig.bannerEnabled || document.getElementById('nd-consent-banner')) {
      return;
    }

    var banner = document.createElement('div');
    banner.id = 'nd-consent-banner';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-live', 'polite');
    banner.style.cssText = [
      'position:fixed',
      'left:16px',
      'right:16px',
      'bottom:16px',
      'z-index:9999',
      'background:#111827',
      'color:#f9fafb',
      'padding:16px',
      'border-radius:12px',
      'box-shadow:0 20px 40px rgba(0,0,0,.25)',
      'max-width:720px',
      'margin:0 auto'
    ].join(';');
    banner.innerHTML = ''
      + '<div style="display:flex;gap:16px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap">'
      + '  <div style="max-width:480px">'
      + '    <strong style="display:block;font-size:16px;margin-bottom:6px">Privacy choices</strong>'
      + '    <p style="margin:0;line-height:1.6;font-size:14px;color:#d1d5db">We use Google tags to measure traffic and improve job pages. Choose whether analytics and advertising cookies can be used.</p>'
      + '  </div>'
      + '  <div style="display:flex;gap:8px;flex-wrap:wrap">'
      + '    <button type="button" data-consent-mode="reject" style="border:1px solid #4b5563;background:transparent;color:#f9fafb;padding:10px 12px;border-radius:999px;cursor:pointer">Reject</button>'
      + '    <button type="button" data-consent-mode="analytics" style="border:1px solid #2563eb;background:#1d4ed8;color:#fff;padding:10px 12px;border-radius:999px;cursor:pointer">Accept</button>'
      + '    <button type="button" data-consent-mode="all" style="border:1px solid #059669;background:#047857;color:#fff;padding:10px 12px;border-radius:999px;cursor:pointer">Accept all</button>'
      + '  </div>'
      + '</div>';

    banner.addEventListener('click', function (event) {
      var button = event.target.closest('[data-consent-mode]');
      if (!button) {
        return;
      }
      var mode = button.getAttribute('data-consent-mode');
      writeConsentMode(consentConfig.storageKey, mode);
      applyConsentUpdate(mode);
      removeConsentBanner();
    });

    document.body.appendChild(banner);
  }

  var config = mergeConfig(defaults, window.NAUKRI_DHABA_TRACKING_CONFIG || {});

  if (config.consentMode && config.consentMode.enabled) {
    ensureGtag();
    var storedMode = readConsentMode(config.consentMode.storageKey);
    var effectiveMode = storedMode || config.consentMode.defaultMode || 'reject';
    if (storedMode) {
      applyConsentUpdate(storedMode);
    }
    document.addEventListener('DOMContentLoaded', function () {
      window.NAUKRI_DHABA_CONSENT_MODE = effectiveMode;
      window.NAUKRI_DHABA_CONSENT_STATE = consentStateFromMode(effectiveMode);
      if (!storedMode) {
        renderConsentBanner(config.consentMode);
      }
    });
  }

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
