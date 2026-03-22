/**
 * NAUKRI DHABA - ADS MANAGER
 * Ads not configured yet. Paste your AdSense / custom ad code here when ready.
 *
 * All ad slots are hidden until configured.
 */
(function () {
  'use strict';
  function hideSlots() {
    document.querySelectorAll('.nd-ad, [data-ad-slot], [data-slot]').forEach(function (el) {
      el.style.display = 'none';
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', hideSlots);
  } else {
    hideSlots();
  }
})();
