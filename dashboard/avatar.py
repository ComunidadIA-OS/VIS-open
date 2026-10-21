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
vec2 ribbon(vec3 p,vec3 nrm,float t,float e){
 float d=dot(p,nrm)+.2*(fbm(p*1.5+nrm*2.+t*.4)-.5);
 float w=(.02+.045*fbm(p*1.1+nrm*3.-t*.3))*(1.+.4*e);
 return vec2(exp(-d*d/(w*w*.08)),exp(-d*d/(w*w*2.2)));
}
float tendrils(float ang,float rc,float N,float spin,float t,float seed){
 vec3 c=vec3(cos(ang)*1.4,sin(ang)*1.4,rc*2.8-t*.2+seed);
 float ph=ang*N+5.*fbm(c)+rc*3.2*sin(seed+t*.15)+spin;
 return pow(abs(sin(ph)),16.);
}
void main(){
 vec2 uv=(gl_FragCoord.xy-.5*uRes)*1.1/(.5*uRes.y);
 float rr=length(uv),ang=atan(uv.y,uv.x);
 vec3 col=vec3(0.);float a=0.;
 float bloom=exp(-pow(max(rr-1.,0.)*16.,2.))*(.3+.3*uE);
 col+=vec3(.2,.32,.95)*bloom*.55;a+=bloom*.5;
 if(rr<1.){
  float z=sqrt(1.-rr*rr);
  // cristal oscuro, con borde que brilla en azul y un toque violeta
  vec3 body=mix(vec3(.0,.012,.045),vec3(.0,.006,.025),rr);
  float vio=smoothstep(-.2,.9,dot(normalize(uv+.0001),normalize(vec2(.6,-.7))));
  body+=mix(vec3(.4,.72,1.),vec3(.6,.28,1.),vio)*pow(1.-z,4.)*.75;
  col+=body;a=.95;
  // hilos radiales finos que fluyen desde el centro
  float rc=rr;
  float spin=uT*.35;
  float tl=tendrils(ang,rc,22.,spin,uT,0.)*.8+tendrils(ang,rc,37.,spin*.8,uT,3.1)*.55
    +tendrils(ang,rc,61.,spin*.6,uT,6.2)*.3;
  float fade=exp(-rc*1.6)*smoothstep(.97,.55,rc)*smoothstep(.015,.14,rc);
  col+=mix(vec3(.5,.7,1.),vec3(.92,.96,1.),exp(-rc*3.))*tl*fade*(.7+.5*uE);
  // flujos de azules distintos, girando en sentido contrario a los hilos
  float phi=-uT*.22,cp=cos(phi),sp2=sin(phi);
  vec2 u2=mat2(cp,-sp2,sp2,cp)*uv;
  for(int s=0;s<2;s++){
   vec3 p=vec3(u2,s==0?z:-z);
   for(int i=0;i<4;i++){
    float fi=float(i);
    vec3 nrm=normalize(vec3(sin(uT*(.17+.06*fi)+fi*2.1),cos(uT*(.13+.05*fi)+fi*1.3),
                            sin(uT*(.1+.05*fi)+fi*3.7)));
    vec2 b=ribbon(p,nrm,uT,uE);
    vec3 hue=i==0?vec3(.1,.3,.95):i==1?vec3(.2,.6,1.):i==2?vec3(.32,.26,.92):vec3(.58,.3,.95);
    col+=hue*b.y*(.14+.12*uE)*(s==0?1.:.6)+mix(hue,vec3(1.),.55)*b.x*(.3+.22*uE)*(s==0?1.:.5);
   }
  }
  // partículas en el borde
  float grain=smoothstep(.985,1.,n(vec3(uv*85.,uT*.4)))*smoothstep(.78,.97,rr);
  col+=vec3(.7,.85,1.)*grain*.8;
  // chispa central
  col+=vec3(.85,.92,1.)*exp(-600.*rr*rr)*(.8+.6*uE)+vec3(.35,.55,1.)*exp(-16.*rr*rr)*(.25+.3*uE);
  // brillos del cristal
  float dir=dot(normalize(uv+.0001),normalize(vec2(-.6,.75)));
  col+=vec3(.9,.95,1.)*smoothstep(.05,0.,abs(rr-.9))*smoothstep(.1,.85,dir)*.6;
  col+=vec3(.55,.4,1.)*smoothstep(.05,0.,abs(rr-.9))*smoothstep(-.1,-.9,dir)*.35;
  col=min(col,vec3(a));
 }
 float ring=exp(-pow((rr-.995)*40.,2.))*.9;
 col+=vec3(.6,.82,1.)*ring;a=max(a,ring);
 gl_FragColor=vec4(min(col,vec3(a)),a); // color premultiplicado
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
