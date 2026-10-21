"""Avatar del asistente de voz: un orbe de plasma, abstracto y neutro (sin rasgos de género).

Una página HTML/canvas/JS propia, sin librerías ni recursos externos. Estados:
- reposo: filamentos tenues y lentos;
- escuchando: se activa mientras el micrófono del panel está grabando (se mira el botón del
  panel; no se abre ningún micrófono más);
- hablando: filamentos intensos, que saltan con cada palabra de la voz del navegador (es-ES).
La respuesta también se escribe en un recuadro `aria-live`, para quien no oye o usa lector de
pantalla. Con «reducir movimiento» activado en el sistema, el orbe no se anima.

El texto llega como dato JSON (sin «<») y se pone con `textContent`: nunca es HTML.
"""

from __future__ import annotations

import json

_PAGE = """<!doctype html><html lang="es"><meta charset="utf-8"><style>
:root{--ink:#1d2a30;--paper:#f7f4ee;--soft:#cfe3e7}
@media (prefers-color-scheme:dark){:root{--ink:#e9eef0;--paper:#1b2327;--soft:#2c4046}}
html,body{margin:0;background:transparent;font:18px/1.4 system-ui,sans-serif;color:var(--ink)}
.wrap{display:flex;flex-direction:column;align-items:center;gap:8px;padding:4px}
canvas{width:220px;height:220px}
.say{min-height:2.6em;max-height:6em;overflow:auto;width:100%;background:var(--paper);
border:1px solid var(--soft);border-radius:10px;padding:8px 10px;box-sizing:border-box}
</style>
<div class="wrap">
<canvas id="c" width="440" height="440" role="img" aria-label="Asistente de voz"></canvas>
<div class="say" id="say" role="status" aria-live="polite"></div></div>
<script>
const t=__TEXT__,a=__ANCHOR__,speak=__SPEAK__;
const say=document.getElementById('say');say.textContent=t||'Dime una orden.';
const cv=document.getElementById('c'),g=cv.getContext('2d'),W=440,C=W/2,R=190;
const still=matchMedia('(prefers-reduced-motion:reduce)').matches;
let state='idle',energy=.25,spike=0,bolts=[];
const pd=window.parent.document;
function listening(){const b=pd.querySelector('[data-testid=stAudioInputActionButton]');
  const l=((b&&b.getAttribute('aria-label'))||'').toLowerCase();
  return /stop|detener|parar|grab/.test(l)&&!/record/.test(l)}
function bolt(){ // un filamento irregular del centro al borde
  const ang=Math.random()*Math.PI*2,pts=[[C,C]],n=9;
  for(let i=1;i<=n;i++){const r=R*.94*i/n,j=(Math.random()-.5)*34*(i/n+.3);
    pts.push([C+Math.cos(ang)*r+Math.cos(ang+1.57)*j,C+Math.sin(ang)*r+Math.sin(ang+1.57)*j])}
  return pts}
for(let i=0;i<16;i++)bolts.push(bolt());
function frame(){
  const target=state==='speaking'?.75+Math.random()*.3:state==='listening'?.5+Math.random()*.25:.22;
  energy+=(target-energy)*.18;spike*=.88;const e=Math.min(1.3,energy+spike);
  g.clearRect(0,0,W,W);
  let s=g.createRadialGradient(C,C,10,C,C,R);
  s.addColorStop(0,'rgba(120,200,255,'+(.35+.4*e)+')');s.addColorStop(.55,'rgba(42,123,140,.55)');
  s.addColorStop(1,'rgba(20,50,90,.85)');
  g.fillStyle=s;g.beginPath();g.arc(C,C,R,0,7);g.fill();
  g.save();g.beginPath();g.arc(C,C,R-3,0,7);g.clip();g.globalCompositeOperation='lighter';
  g.lineCap='round';g.lineJoin='round';
  bolts.forEach((b,k)=>{ if(!still&&Math.random()<.05+.25*e)bolts[k]=bolt();
    g.beginPath();b.forEach((p,i)=>i?g.lineTo(p[0],p[1]):g.moveTo(p[0],p[1]));
    g.strokeStyle='rgba(170,225,255,'+(.25+.5*e)+')';g.shadowColor='rgba(120,200,255,1)';
    g.shadowBlur=14*e+4;g.lineWidth=1.2+1.8*e;g.stroke()});
  g.restore();
  const core=g.createRadialGradient(C,C,0,C,C,40+40*e);
  core.addColorStop(0,'rgba(255,255,255,'+(.7+.3*e)+')');core.addColorStop(1,'rgba(150,215,255,0)');
  g.fillStyle=core;g.beginPath();g.arc(C,C,40+40*e,0,7);g.fill();
  g.lineWidth=5;g.strokeStyle='rgba(190,230,255,.75)';g.beginPath();g.arc(C,C,R,0,7);g.stroke();
  g.fillStyle='rgba(255,255,255,.22)';g.beginPath();g.ellipse(C-R*.35,C-R*.5,R*.32,R*.14,-.6,0,7);
  g.fill();
  if(!still&&!document.hidden)requestAnimationFrame(frame)}
if(still){frame()}else{
  requestAnimationFrame(frame);
  setInterval(()=>{if(state!=='speaking')state=listening()?'listening':'idle'},250)}
if(speak&&t){
  if(a){setTimeout(()=>{const e=pd.getElementById(a);
    if(e)e.scrollIntoView({behavior:'smooth'})},400)}
  const s=window.parent.speechSynthesis,u=new SpeechSynthesisUtterance(t);u.lang='es-ES';
  u.onstart=()=>{state='speaking'};u.onboundary=()=>{spike=.5};
  u.onend=u.onerror=()=>{state='idle'};
  s.cancel();s.speak(u);
}
</script></html>"""


def _safe(value: object) -> str:
    """JSON para meter en un <script>: sin «<», nada puede cerrar la etiqueta."""
    return json.dumps(value).replace("<", "\\u003c")


def avatar_html(text: str | None, anchor: str | None = None, speak: bool = False) -> str:
    return (
        _PAGE.replace("__TEXT__", _safe(text or ""))
        .replace("__ANCHOR__", _safe(anchor))
        .replace("__SPEAK__", "true" if speak else "false")
    )
