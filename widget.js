// Naukri Dhaba — Embeddable Latest Jobs Widget
// Usage: <script src="https://naukridhaba.in/widget.js" data-nd-limit="5"></script>
(function() {
  var script = document.currentScript || (function() {
    var s = document.getElementsByTagName('script');
    return s[s.length - 1];
  })();
  var limit = parseInt(script.getAttribute('data-nd-limit') || '5', 10);
  var theme = script.getAttribute('data-nd-theme') || 'light';

  var container = document.createElement('div');
  container.id = 'nd-widget';
  container.style.cssText = [
    'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif',
    'border:1px solid ' + (theme === 'dark' ? '#333' : '#e0e0e0'),
    'border-radius:8px',
    'overflow:hidden',
    'max-width:480px',
    'background:' + (theme === 'dark' ? '#1e1e1e' : '#fff'),
    'color:' + (theme === 'dark' ? '#eee' : '#212121'),
  ].join(';');

  var header = document.createElement('div');
  header.style.cssText = 'background:#1a237e;padding:.75rem 1rem;display:flex;justify-content:space-between;align-items:center;';
  header.innerHTML = '<a href="https://naukridhaba.in" target="_blank" style="color:#fff;text-decoration:none;font-weight:700;font-size:1rem;">📋 Naukri Dhaba</a>'
    + '<span style="color:rgba(255,255,255,.7);font-size:.75rem;">Latest Jobs</span>';
  container.appendChild(header);

  var list = document.createElement('div');
  list.style.cssText = 'padding:.5rem 0;';
  list.innerHTML = '<div style="padding:.75rem 1rem;color:#999;font-size:.85rem;">Loading latest jobs...</div>';
  container.appendChild(list);

  var footer = document.createElement('div');
  footer.style.cssText = 'padding:.5rem 1rem;border-top:1px solid ' + (theme === 'dark' ? '#333' : '#eee') + ';text-align:center;';
  footer.innerHTML = '<a href="https://naukridhaba.in/latest-jobs" target="_blank" style="color:#1a237e;font-size:.8rem;text-decoration:none;font-weight:500;">View All Government Jobs →</a>';
  container.appendChild(footer);

  script.parentNode.insertBefore(container, script.nextSibling);

  fetch('https://naukridhaba.in/api/latest.json')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var jobs = (data.jobs || []).slice(0, limit);
      if (!jobs.length) {
        list.innerHTML = '<div style="padding:.75rem 1rem;color:#999;font-size:.85rem;">No jobs available right now.</div>';
        return;
      }
      list.innerHTML = jobs.map(function(j) {
        return '<a href="' + j.url + '" target="_blank" style="display:block;padding:.65rem 1rem;text-decoration:none;border-bottom:1px solid ' + (theme === 'dark' ? '#2a2a2a' : '#f5f5f5') + ';transition:background .15s;" onmouseover="this.style.background=\'' + (theme === 'dark' ? '#2a2a2a' : '#f9f9f9') + '\'" onmouseout="this.style.background=\'\'">'
          + '<div style="font-weight:600;font-size:.875rem;color:' + (theme === 'dark' ? '#90caf9' : '#1a237e') + ';margin-bottom:.2rem;">' + j.title + '</div>'
          + '<div style="font-size:.75rem;color:#888;">' + j.dept + (j.date ? ' &nbsp;·&nbsp; ' + j.date : '') + '</div>'
          + '</a>';
      }).join('');
    })
    .catch(function() {
      list.innerHTML = '<div style="padding:.75rem 1rem;font-size:.85rem;"><a href="https://naukridhaba.in/latest-jobs" target="_blank" style="color:#1a237e;">Visit Naukri Dhaba for latest jobs →</a></div>';
    });
})();
