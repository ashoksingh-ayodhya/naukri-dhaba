"""
End-to-end pipeline test using a local mock HTTP server.
Simulates sarkariresult.com listing + detail pages.
Verifies: fetch → parse_listing → parse_detail → generate_mdx
"""
import sys, os, pathlib, json, threading, time
sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from http.server import HTTPServer, BaseHTTPRequestHandler

# ── Mock HTML pages ────────────────────────────────────────────────────────────

LISTING_HTML = """<!DOCTYPE html>
<html><head><title>Latest Jobs - Sarkari Result</title></head>
<body>
<div class="TableLi">
<table>
<tr>
  <td><b style="color:red">New</b>
    <a href="/railway-group-d-2026/">Railway Group D Recruitment 2026</a>
  </td>
  <td>09/05/2026</td>
</tr>
<tr>
  <td><a href="/ssc-cpo-2026/">SSC CPO SI ASI Online Form 2026</a></td>
  <td>08/05/2026</td>
</tr>
<tr>
  <td><a href="/upsc-civil-2026/">UPSC Civil Services Preliminary 2026</a></td>
  <td>07/05/2026</td>
</tr>
<tr>
  <td><a href="/ibps-po-2026/">IBPS PO Recruitment 2026</a></td>
  <td>06/05/2026</td>
</tr>
</table>
</div>
</body></html>"""

DETAIL_HTML = """<!DOCTYPE html>
<html><head><title>Railway Group D 2026 - Sarkari Result</title></head>
<body>
<div id="pcontent">
<h1>Railway Group D Recruitment 2026 — 32000 Posts</h1>
<p>Railway Recruitment Board has released a notification for Group D posts.</p>
<table>
<tr><th colspan="2">Important Dates</th></tr>
<tr><td>Apply Begin</td><td>15/05/2026</td></tr>
<tr><td>Last Date for Apply Online</td><td>14/06/2026</td></tr>
<tr><td>Exam Date</td><td>September 2026</td></tr>
</table>
<table>
<tr><th colspan="2">Application Fee</th></tr>
<tr><td>General / OBC / EWS</td><td>500/-</td></tr>
<tr><td>SC / ST / PH</td><td>250/-</td></tr>
<tr><td>Pay the Examination Fee Through</td><td>Online</td></tr>
</table>
<table>
<tr><th colspan="2">Vacancy Details</th></tr>
<tr><td>Total Post</td><td>32000</td></tr>
</table>
<table>
<tr><th colspan="2">Important Links</th></tr>
<tr><td>Apply Online</td><td><a href="https://rrbapply.gov.in/">Click Here</a></td></tr>
<tr><td>Notification</td><td><a href="https://rrb.gov.in/notif.pdf">Click Here</a></td></tr>
<tr><td>Official Website</td><td><a href="https://rrb.gov.in/">Click Here</a></td></tr>
</table>
</div>
</body></html>"""

RESULT_HTML = """<!DOCTYPE html>
<html><head><title>Latest Results - Sarkari Result</title></head>
<body>
<div class="TableLi">
<table>
<tr>
  <td><a href="/ssc-cgl-result-2025/">SSC CGL Result 2025 Final</a></td>
  <td>05/05/2026</td>
</tr>
</table>
</div>
</body></html>"""

ADMIT_HTML = """<!DOCTYPE html>
<html><head><title>Admit Cards - Sarkari Result</title></head>
<body>
<div class="TableLi">
<table>
<tr>
  <td><a href="/railway-group-d-admit-2026/">Railway Group D Admit Card 2026</a></td>
  <td>03/05/2026</td>
</tr>
</table>
</div>
</body></html>"""

PAGES = {
    '/latestjob.php': LISTING_HTML,
    '/result.php': RESULT_HTML,
    '/admitcard.php': ADMIT_HTML,
    '/railway-group-d-2026/': DETAIL_HTML,
    '/ssc-cpo-2026/': DETAIL_HTML,
    '/upsc-civil-2026/': DETAIL_HTML,
    '/ibps-po-2026/': DETAIL_HTML,
    '/ssc-cgl-result-2025/': DETAIL_HTML,
    '/railway-group-d-admit-2026/': DETAIL_HTML,
}

class MockHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = PAGES.get(self.path)
        if body is None:
            self.send_response(404)
            self.end_headers()
            return
        data = body.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass  # suppress access log noise

def start_mock_server(port=18765):
    srv = HTTPServer(('127.0.0.1', port), MockHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, f'http://127.0.0.1:{port}'

# ── Run the test ───────────────────────────────────────────────────────────────

def main():
    import site_config
    import sarkari_scraper as sc
    from detail_parser import parse_detail_page
    from mdx_generator import generate_mdx
    import mdx_generator as mg
    from bs4 import BeautifulSoup

    # Point MDX output to /tmp
    tmp_content = pathlib.Path('/tmp/test_content')
    mg.CONTENT_ROOT = tmp_content
    if tmp_content.exists():
        import shutil; shutil.rmtree(tmp_content)

    srv, base = start_mock_server()
    print(f'Mock server: {base}')

    errors = []

    # ── 1. Test parse_listing ──────────────────────────────────────────────────
    import urllib.request
    raw = urllib.request.urlopen(f'{base}/latestjob.php').read()
    soup = BeautifulSoup(raw, 'lxml')
    items = sc.parse_listing(soup, 'job', source_base=base)
    print(f'\n[1] parse_listing → {len(items)} items')
    for it in items:
        print(f'    {it["title"][:50]}  |  {it.get("post_date","?")}  |  {it.get("detail_url","?")}')
    if len(items) < 4:
        errors.append(f'Expected 4 listings, got {len(items)}')

    # ── 2. Test parse_detail_page ──────────────────────────────────────────────
    raw_detail = urllib.request.urlopen(f'{base}/railway-group-d-2026/').read()
    soup_detail = BeautifulSoup(raw_detail, 'lxml')
    item = items[0] if items else {'title': 'Railway Group D 2026', 'dept': 'Railway',
                                    'detail_url': f'{base}/railway-group-d-2026/', 'post_date': '09/05/2026'}
    detail = parse_detail_page(soup_detail, item, source_name='sarkariresult')
    print(f'\n[2] parse_detail_page →')
    print(f'    title     : {detail.title}')
    print(f'    total_posts: {detail.total_posts}')
    print(f'    apply_url : {detail.apply_url}')
    print(f'    dates     : {detail.dates}')
    print(f'    fees      : {detail.fees}')
    if not detail.title:
        errors.append('Detail parse: empty title')
    if not detail.apply_url:
        errors.append('Detail parse: empty apply_url')

    # ── 3. Test generate_mdx ───────────────────────────────────────────────────
    detail.slug = 'railway-group-d-recruitment-2026'
    detail.page_type = 'job'
    detail.source = 'sarkariresult'
    detail.post_date = '09/05/2026'
    out = generate_mdx(detail)
    print(f'\n[3] generate_mdx → {out}')
    if out and out.exists():
        content = out.read_text()
        print('    First 500 chars of MDX:')
        print('    ' + '\n    '.join(content[:500].splitlines()))
        if 'title:' not in content:
            errors.append('MDX missing title field')
        if 'applyUrl:' not in content:
            errors.append('MDX missing applyUrl field')
    else:
        errors.append('generate_mdx returned None or file not created')

    # ── 4. Test result + admit listings ───────────────────────────────────────
    raw_r = urllib.request.urlopen(f'{base}/result.php').read()
    result_items = sc.parse_listing(BeautifulSoup(raw_r, 'lxml'), 'result', source_base=base)
    print(f'\n[4] result listing → {len(result_items)} items')
    if not result_items:
        errors.append('Result listing parsed 0 items')

    # ── 5. Verify curl_cffi is available ──────────────────────────────────────
    try:
        from curl_cffi import requests as cffi_requests
        s = cffi_requests.Session(impersonate='chrome124')
        r = s.get(f'{base}/latestjob.php')
        curl_items = sc.parse_listing(BeautifulSoup(r.content, 'lxml'), 'job', source_base=base)
        print(f'\n[5] curl_cffi fetch + parse → {len(curl_items)} items  ✓')
        if not curl_items:
            errors.append('curl_cffi fetch parsed 0 items')
    except Exception as e:
        errors.append(f'curl_cffi failed: {e}')

    srv.shutdown()

    # ── Summary ────────────────────────────────────────────────────────────────
    print('\n' + '─' * 60)
    if errors:
        print(f'FAILED — {len(errors)} error(s):')
        for e in errors:
            print(f'  ✗ {e}')
        sys.exit(1)
    else:
        print('ALL TESTS PASSED ✓')
        mdx_files = list(tmp_content.rglob('*.mdx'))
        print(f'MDX files generated: {len(mdx_files)}')
        for f in mdx_files:
            print(f'  {f.relative_to(tmp_content)}')

if __name__ == '__main__':
    main()
