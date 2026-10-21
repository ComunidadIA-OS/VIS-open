"""Avatar del asistente de voz: un orbe azul sereno, abstracto y sin rasgos de género.

Una página HTML/canvas/JS propia, sin librerías ni recursos externos. Estados:
- reposo: brillo suave y lento;
- escuchando: se activa mientras el micrófono del panel está grabando (se mira el botón del
  panel; no se abre ningún micrófono más);
- hablando: brillo intenso, que pulsa con cada palabra de la voz del navegador (es-ES).
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
let state='idle',energy=.25,spike=0,ph=0;
const pd=window.parent.document;
function listening(){const b=pd.querySelector('[data-testid=stAudioInputActionButton]');
  const l=((b&&b.getAttribute('aria-label'))||'').toLowerCase();
  return /stop|detener|parar|grab/.test(l)&&!/record/.test(l)}
const cells=[];for(let i=0;i<9;i++)cells.push({a:Math.random()*6.28,d:.15+Math.random()*.55,
  s:.4+Math.random()*.8,r:.22+Math.random()*.2,h:Math.random()});
function glow(x,y,r,c0,c1){const q=g.createRadialGradient(x,y,0,x,y,r);q.addColorStop(0,c0);
  q.addColorStop(1,c1);g.fillStyle=q;g.beginPath();g.arc(x,y,r,0,7);g.fill()}
function frame(){
  const target=state==='speaking'?.75+Math.random()*.25
    :state==='listening'?.55+Math.random()*.15:.38;
  energy+=(target-energy)*.12;spike*=.9;const e=Math.min(1.25,energy+spike);
  ph+=still?0:.004+.022*e;
  g.clearRect(0,0,W,W);g.globalCompositeOperation='source-over';
  glow(C,C,R+30+26*e,'rgba(120,200,225,'+(.25+.3*e)+')','rgba(42,123,140,0)');  // halo
  glow(C,C,R,'rgba(42,123,140,.92)','rgba(22,70,100,.96)');                        // esfera
  g.save();g.beginPath();g.arc(C,C,R-2,0,7);g.clip();g.globalCompositeOperation='lighter';
  cells.forEach(c=>{const x=C+Math.cos(c.a+ph*c.s)*R*c.d*(1+.5*e),
    y=C+Math.sin(c.a*1.7+ph*c.s*1.3)*R*c.d*(1+.5*e),r=R*c.r*(1+.35*e);
    glow(x,y,r,'hsla('+(185+c.h*35)+',70%,'+(62+16*e)+'%,'+(.42+.3*e)+')','hsla(200,70%,50%,0)')});
  glow(C,C,R*(.5+.3*e),'rgba(232,248,255,'+(.55+.45*e)+')','rgba(140,210,235,0)');   // núcleo
  g.restore();
  g.globalCompositeOperation='lighter';
  const rim=g.createRadialGradient(C,C,R*.78,C,C,R);rim.addColorStop(0,'rgba(150,215,235,0)');
  rim.addColorStop(1,'rgba(190,235,248,'+(.55+.3*e)+')');g.fillStyle=rim;
  g.beginPath();g.arc(C,C,R,0,7);g.fill();g.globalCompositeOperation='source-over';
  g.fillStyle='rgba(255,255,255,.18)';g.beginPath();g.ellipse(C-R*.35,C-R*.52,R*.3,R*.12,-.6,0,7);
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
