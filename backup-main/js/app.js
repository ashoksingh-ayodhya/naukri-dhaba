// Naukri Dhaba - Vanilla JS
const storage={get:k=>localStorage.getItem(k),set:(k,v)=>localStorage.setItem(k,v)};
function toggleDarkMode(){document.body.setAttribute('data-theme',document.body.getAttribute('data-theme')==='dark'?'light':'dark');storage.set('theme',document.body.getAttribute('data-theme'))}
function initTheme(){const t=storage.get('theme');if(t)document.body.setAttribute('data-theme',t)}
function toggleMobileMenu(){const nav=document.querySelector('.nav--mobile'),overlay=document.getElementById('menu-overlay');if(!nav)return;const open=nav.classList.toggle('active');if(overlay)overlay.style.display=open?'block':'none';document.body.style.overflow=open?'hidden':'';}
function closeMobileMenu(){const nav=document.querySelector('.nav--mobile'),overlay=document.getElementById('menu-overlay');if(nav)nav.classList.remove('active');if(overlay)overlay.style.display='none';document.body.style.overflow='';}
function checkEligibility(minAge,maxAge){const dob=document.getElementById('dob-input').value,cat=document.getElementById('category-select').value,res=document.getElementById('eligibility-result');if(!dob)return;const age=Math.floor((new Date()-new Date(dob))/(365.25*24*60*60*1000));let max=maxAge;if(cat==='obc')max+=3;else if(cat==='sc'||cat==='st')max+=5;const eligible=age>=minAge&&age<=max;res.style.display='block';res.className=eligible?'calculator__result calculator__result--success':'calculator__result calculator__result--error';res.innerHTML=eligible?'✅ You are eligible!':'❌ Not eligible';res.innerHTML+='<div>Age: '+age+' years | Max allowed: '+max+'</div>'}
function sharePost(url,text){if(navigator.share){navigator.share({title:text,url:url}).catch(function(){});}else if(navigator.clipboard){navigator.clipboard.writeText(url).then(function(){alert('Link copied to clipboard!');});}else{prompt('Copy this link:',url);}}
function countdown(target,elId){const el=document.getElementById(elId);if(!el)return;const t=new Date(target),update=()=>{const diff=t-new Date(),days=Math.floor(diff/(1000*60*60*24));if(days<0)el.innerHTML='Expired';else if(days===0)el.innerHTML='Last day today!';else el.innerHTML=days+' days left';};update();setInterval(update,60000)}
function doSearch(){var q=document.getElementById('search-input');if(q&&q.value.trim())window.location.href='/latest-jobs?q='+encodeURIComponent(q.value.trim());}
function filterJobs(q){var rows=document.querySelectorAll('#jobs-table tbody tr'),term=q.toLowerCase().trim(),noResults=document.getElementById('no-results');rows.forEach(function(r){r.style.display=(!term||r.textContent.toLowerCase().includes(term))?'':'none';});if(noResults)noResults.style.display=[].slice.call(rows).every(function(r){return r.style.display==='none';})?'block':'none';}
function filterPill(e,dept,el){e.preventDefault();document.querySelectorAll('.pill').forEach(function(p){p.classList.remove('active');});el.classList.add('active');var tbl=document.querySelector('table.table tbody');if(!tbl)return;var rows=tbl.querySelectorAll('tr');rows.forEach(function(r){var d=r.cells[0]?r.cells[0].textContent.trim().toUpperCase():'';r.style.display=(dept==='all'||d===dept.toUpperCase())?'':'none';});}
function initFooter(){
  var el=document.getElementById('site-footer');if(!el)return;
  el.innerHTML='<div class="container">'
  +'<div class="footer__about"><h3 class="footer__title">📋 Naukri Dhaba</h3>'
  +'<p style="color:#ccc;font-size:0.9rem;line-height:1.6;">Independent government job updates, result tracking, and admit card alerts for India.</p></div>'
  +'<div class="footer__mid"><div><h3 class="footer__title">Quick Links</h3>'
  +'<div class="footer__links"><a href="/latest-jobs">Latest Jobs</a><a href="/results">Results</a><a href="/admit-cards">Admit Cards</a></div></div>'
  +'<div><h3 class="footer__title">Tools</h3>'
  +'<div class="footer__links"><a href="/eligibility-calculator">Eligibility Calculator</a><a href="/study-planner">Study Planner</a><a href="/previous-papers">Previous Papers</a><a href="/syllabus.html">Syllabus</a><a href="/cut-off-marks.html">Cut-off Marks</a></div></div></div>'
  +'<div class="footer__grid"><div><h3 class="footer__title">State Jobs</h3>'
  +'<div class="state-list"><a href="/state/uttar-pradesh.html">Uttar Pradesh</a><a href="/state/bihar.html">Bihar</a><a href="/state/rajasthan.html">Rajasthan</a><a href="/state/madhya-pradesh.html">Madhya Pradesh</a><a href="/state/haryana.html">Haryana</a><a href="/state/jharkhand.html">Jharkhand</a><a href="/state/delhi.html">Delhi</a><a href="/state/maharashtra.html">Maharashtra</a><a href="/state/gujarat.html">Gujarat</a><a href="/state/punjab.html">Punjab</a></div></div></div>'
  +'<div class="footer__bottom"><p>&copy; 2026 Naukri Dhaba. All rights reserved.</p>'
  +'<p>Disclaimer: We are not affiliated with any government organization. We only provide information.</p></div></div>';
}
function cleanPlaceholders(){
  var placeholders=['Check Notification','As per Schedule','As per Government Norms','Check Site'];
  var isListing=!!document.querySelector('#jobs-table,.cards');
  var label=isListing?'—':'Yet to be announced';
  document.querySelectorAll('.info-item__value, td, .card p, ul li').forEach(function(el){
    var t=el.textContent.trim();
    if(placeholders.indexOf(t)!==-1)el.textContent=label;
    if(/nan[–-]nan/i.test(t))el.textContent=label;
  });
}
function labelDates(){
  document.querySelectorAll('.card p').forEach(function(p){
    var t=p.textContent.trim();
    if(/^\d{2}\/\d{2}\/\d{4}/.test(t)&&t.indexOf('Last Date')===-1)p.textContent='Last Date: '+t;
    else if(t==='—')p.textContent='Last Date: —';
  });
}
document.addEventListener('DOMContentLoaded',function(){
  initTheme();initFooter();cleanPlaceholders();labelDates();
  document.querySelectorAll('.nav--mobile a').forEach(function(a){a.addEventListener('click',closeMobileMenu);});
  var inp=document.getElementById('search-input');
  if(inp){
    inp.addEventListener('keydown',function(e){if(e.key==='Enter'){if(document.getElementById('jobs-table'))filterJobs(inp.value);else doSearch();}});
    var q=new URLSearchParams(window.location.search).get('q');
    if(q&&document.getElementById('jobs-table')){inp.value=q;filterJobs(q);}
  }
});
