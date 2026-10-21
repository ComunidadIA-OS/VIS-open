"""Avatar del asistente de voz: un orbe azul sereno, abstracto y sin rasgos de género.

Una página HTML/WebGL/JS propia, sin librerías ni recursos externos: un shader dibuja una nebulosa
fluida (ruido fractal deformado) dentro de una esfera de cristal, con estrellas y halo. Estados:
- reposo: movimiento lento y brillo suave;
- escuchando: se aviva mientras el micrófono del panel está grabando (se mira el botón del
  panel; no se abre ningún micrófono más);
- hablando: más brillo y movimiento, con un pulso en cada palabra de la voz del navegador (es-ES).
Sin WebGL se dibuja una esfera estática. La respuesta también se escribe en un recuadro
`aria-live`, para quien no oye o usa lector de pantalla. Con «reducir movimiento» activado en el
sistema, el orbe no se anima.

El texto llega como dato JSON (sin «<») y se pone con `textContent`: nunca es HTML.
"""

from __future__ import annotations

import json

_PAGE = """<!doctype html><html lang="es"><meta charset="utf-8"><style>
:root{--ink:#1d2a30;--paper:#f7f4ee;--soft:#cfe3e7}
@media (prefers-color-scheme:dark){:root{--ink:#e9eef0;--paper:#1b2327;--soft:#2c4046}}
html,body{margin:0;background:transparent;font:18px/1.4 system-ui,sans-serif;color:var(--ink)}
.wrap{display:flex;flex-direction:column;align-items:center;gap:8px;padding:4px}
canvas{width:240px;height:240px}
.say{min-height:2.6em;max-height:6em;overflow:auto;width:100%;background:var(--paper);
border:1px solid var(--soft);border-radius:10px;padding:8px 10px;box-sizing:border-box}
</style>
<div class="wrap">
<canvas id="c" width="480" height="480" role="img" aria-label="Asistente de voz"></canvas>
<div class="say" id="say" role="status" aria-live="polite"></div></div>
<script id="fs" type="x-shader/x-fragment">
precision highp float;
uniform vec2 uRes;uniform float uT,uE;
float h(vec3 p){p=fract(p*.3183099+.1);p*=17.;return fract(p.x*p.y*p.z*(p.x+p.y+p.z));}
float n(vec3 x){vec3 i=floor(x),f=fract(x);f=f*f*(3.-2.*f);
 float a=mix(mix(h(i),h(i+vec3(1,0,0)),f.x),mix(h(i+vec3(0,1,0)),h(i+vec3(1,1,0)),f.x),f.y);
 float b=mix(mix(h(i+vec3(0,0,1)),h(i+vec3(1,0,1)),f.x),
             mix(h(i+vec3(0,1,1)),h(i+vec3(1,1,1)),f.x),f.y);
 return mix(a,b,f.z);}
float fbm(vec3 p){float a=.5,s=0.;
 for(int i=0;i<5;i++){s+=a*n(p);p=p*2.03+vec3(1.7,9.2,3.1);a*=.5;}
 return s;}
void main(){
 vec2 uv=(gl_FragCoord.xy-.5*uRes)*1.3/(.5*uRes.y);
 float ang=atan(uv.y,uv.x);
 float rr=length(uv)*(1.+(.005+.022*uE)*sin(3.*ang+uT*1.3)+(.004+.016*uE)*sin(5.*ang-uT*.9));
 float halo=exp(-3.4*max(rr-1.,0.))*(.18+.3*uE)*smoothstep(1.28,1.04,rr);
 vec3 col=vec3(.35,.72,1.)*halo;float a=halo;
 if(rr<1.){
  float z=sqrt(1.-rr*rr);vec3 p=vec3(uv/max(length(uv),.001)*rr,z);
  float c=cos(uT*.3),s=sin(uT*.3);p.xz=mat2(c,-s,s,c)*p.xz;
  float ca=cos(uT*.32),sa=sin(uT*.32),cb=.94,sb=.34; // la esfera gira
  vec3 r3=vec3(p.x*ca+p.z*sa,p.y,-p.x*sa+p.z*ca);
  r3=vec3(r3.x,r3.y*cb-r3.z*sb,r3.y*sb+r3.z*cb);
  vec3 q=r3*1.25;
  vec3 w=vec3(fbm(q+uT*.12),fbm(q+vec3(5.2,1.3,2.8)-uT*.1),fbm(q+vec3(8.3,2.8,4.1)+uT*.08));
  float f=fbm(q+(1.8+1.2*uE)*w);
  float ridge=1.-abs(2.*f-1.);
  float g=fbm(q*.7+w*1.5+vec3(uT*.07,-uT*.05,3.)); // el color fluye por el espacio
  vec3 cB=vec3(.18,.42,1.),cC=vec3(.25,.9,1.),cT=vec3(.1,.78,.82),cV=vec3(.55,.45,1.);
  vec3 hue=mix(mix(cB,cC,smoothstep(.3,.55,g)),cT,smoothstep(.5,.7,g));
  hue=mix(hue,cV,smoothstep(.62,.85,fbm(q*.6-w+uT*.04))*.7);
  vec3 k=vec3(.0,.04,.14)+hue*.12*(.5+f); // nebulosa tenue de fondo
  k+=hue*.55*smoothstep(.35,.9,ridge)*(.7+.5*uE);
  k+=mix(hue,vec3(1.),.45)*pow(ridge,6.)*(1.+1.2*uE);
  k+=vec3(.85,.95,1.)*smoothstep(.96,1.,n(r3*30.))*(.25+.5*uE); // estrellas que giran
  k+=vec3(.2,.6,.9)*exp(-9.*rr*rr)*(.12+.3*uE);
  k+=vec3(.2,.7,.95)*pow(1.-z,3.)*(.7+.5*uE);
  float dir=dot(normalize(uv+.0001),normalize(vec2(-.6,.8)));
  k+=vec3(.9,.97,1.)*smoothstep(.05,0.,abs(rr-.93))*smoothstep(-.3,.8,dir)*.55;
  k+=vec3(.6,.9,1.)*smoothstep(.04,0.,abs(rr-.9))*smoothstep(.3,-.9,dir)*.25;
  float m=smoothstep(1.,.985,rr);
  float ak=m*(.86+.1*pow(1.-z,2.)); // un poco transparente
  col=col*(1.-ak)+k*ak;a=a*(1.-ak)+ak;
 }
 float rc=length(uv);
 float star=exp(-260.*rc*rc)*(.5+.7*uE)+exp(-abs(uv.y)*150.)*exp(-abs(uv.x)*4.)*(.08+.3*uE);
 col+=vec3(.8,.95,1.)*star;a=clamp(max(a,star*.9),0.,1.);
 gl_FragColor=vec4(min(col,vec3(1.)),a);
}
</script>
<script>
const t=__TEXT__,a=__ANCHOR__,speak=__SPEAK__;
const say=document.getElementById('say');say.textContent=t||'Dime una orden.';
const cv=document.getElementById('c');
const still=matchMedia('(prefers-reduced-motion:reduce)').matches;
let state='idle',energy=.3,spike=0,ph=0,last=0;
const pd=window.parent.document;
function listening(){const b=pd.querySelector('[data-testid=stAudioInputActionButton]');
  const l=((b&&b.getAttribute('aria-label'))||'').toLowerCase();
  return /stop|detener|parar|grab/.test(l)&&!/record/.test(l)}
const gl=cv.getContext('webgl',{premultipliedAlpha:true,alpha:true});
let draw=null;
if(gl){
  const mk=(ty,src)=>{const s=gl.createShader(ty);gl.shaderSource(s,src);
    gl.compileShader(s);return s};
  const pr=gl.createProgram();
  gl.attachShader(pr,mk(gl.VERTEX_SHADER,
    'attribute vec2 a;void main(){gl_Position=vec4(a,0.,1.);}'));
  gl.attachShader(pr,mk(gl.FRAGMENT_SHADER,document.getElementById('fs').textContent));
  gl.linkProgram(pr);
  if(gl.getProgramParameter(pr,gl.LINK_STATUS)){
    gl.useProgram(pr);const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
    const loc=gl.getAttribLocation(pr,'a');gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);
    const uT=gl.getUniformLocation(pr,'uT'),uE=gl.getUniformLocation(pr,'uE');
    gl.uniform2f(gl.getUniformLocation(pr,'uRes'),cv.width,cv.height);
    gl.viewport(0,0,cv.width,cv.height);gl.clearColor(0,0,0,0);
    draw=(time,e)=>{gl.clear(gl.COLOR_BUFFER_BIT);gl.uniform1f(uT,time);gl.uniform1f(uE,e);
      gl.drawArrays(gl.TRIANGLES,0,3)};
  }
}
if(!draw){ // sin WebGL: esfera estática
  const g=cv.getContext('2d'),C=240,q=g.createRadialGradient(C,C,10,C,C,190);
  q.addColorStop(0,'#cdefff');q.addColorStop(.5,'#2a7b8c');q.addColorStop(1,'#0b2a4a');
  draw=()=>{g.clearRect(0,0,480,480);g.fillStyle=q;g.beginPath();g.arc(C,C,190,0,7);g.fill()}}
function frame(now){
  const dt=Math.min(.05,(now-last)/1000||.016);last=now;
  const target=state==='speaking'?.8+Math.random()*.2
    :state==='listening'?.6:.3;
  energy+=(target-energy)*Math.min(1,dt*3);spike*=Math.pow(.02,dt);
  const e=Math.min(1.3,energy+spike);
  ph+=still?0:dt*(.35+1.1*e);
  draw(ph,e);
  if(!still&&!document.hidden)requestAnimationFrame(frame)}
if(still){draw(3.,.3)}else{
  requestAnimationFrame(frame);
  setInterval(()=>{if(state!=='speaking')state=listening()?'listening':'idle'},250)}
if(speak&&t){
  if(a){setTimeout(()=>{const e=pd.getElementById(a);
    if(e)e.scrollIntoView({behavior:'smooth'})},400)}
  const s=window.parent.speechSynthesis,u=new SpeechSynthesisUtterance(t);u.lang='es-ES';
  u.onstart=()=>{state='speaking'};u.onboundary=()=>{spike=.45};
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
