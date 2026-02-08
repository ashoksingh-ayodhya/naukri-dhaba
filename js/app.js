// Naukri Dhaba - Vanilla JS
const storage={get:k=>localStorage.getItem(k),set:(k,v)=>localStorage.setItem(k,v)};
function toggleDarkMode(){document.body.setAttribute('data-theme',document.body.getAttribute('data-theme')==='dark'?'light':'dark');storage.set('theme',document.body.getAttribute('data-theme'))}
function initTheme(){const t=storage.get('theme');if(t)document.body.setAttribute('data-theme',t)}
function toggleMobileMenu(){document.querySelector('.nav--mobile').classList.toggle('active')}
function checkEligibility(minAge,maxAge){const dob=document.getElementById('dob-input').value,cat=document.getElementById('category-select').value,res=document.getElementById('eligibility-result');if(!dob)return;const age=Math.floor((new Date()-new Date(dob))/(365.25*24*60*60*1000));let max=maxAge;if(cat==='obc')max+=3;else if(cat==='sc'||cat==='st')max+=5;const eligible=age>=minAge&&age<=max;res.style.display='block';res.className=eligible?'calculator__result calculator__result--success':'calculator__result calculator__result--error';res.innerHTML=eligible?'✅ You are eligible! / आप योग्य हैं!':'❌ Not eligible / योग्य नहीं';res.innerHTML+='<div>Age: '+age+' years | Max allowed: '+max+'</div>'}
function shareWhatsApp(url,text){window.open('https://wa.me/?text= '+encodeURIComponent(text+' '+url),'_blank')}
function shareTelegram(url,text){window.open('https://t.me/share/url?url= '+encodeURIComponent(url)+'&text='+encodeURIComponent(text),'_blank')}
function copyLink(url){navigator.clipboard.writeText(url).then(()=>alert('Link copied!'))}
function countdown(target,elId){const el=document.getElementById(elId);if(!el)return;const t=new Date(target),update=()=>{const diff=t-new Date(),days=Math.floor(diff/(1000*60*60*24));if(days<0)el.innerHTML='Expired';else if(days===0)el.innerHTML='Last day today!';else el.innerHTML=days+' days left';};update();setInterval(update,60000)}
document.addEventListener('DOMContentLoaded',initTheme);
