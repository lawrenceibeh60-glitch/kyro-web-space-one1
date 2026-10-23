// Persistent viewport construction guides for KAE. Guides are editor-only and never enter render output.
import { state, setState } from '../core/state_manager.js';
import { bus } from '../core/event_bus.js';

const $ = id => document.getElementById(id);
const DEFAULTS = Object.freeze({
  enabled:false, grid:true, center:true, thirds:false, head:false, eyes:false, nose:false, mouth:false, ears:false, hairline:false, body:false,
  color:'#36c5d8', opacity:0.55, spacing:32, centered:true
});
let canvas=null, ctx=null, host=null, observer=null;
let scheduled=false;

function settings() {
  if (!state.project) return { ...DEFAULTS };
  if (!state.project.editor_settings || typeof state.project.editor_settings !== 'object') state.project.editor_settings = {};
  if (!state.project.editor_settings.guides || typeof state.project.editor_settings.guides !== 'object') {
    state.project.editor_settings.guides = { ...DEFAULTS };
  }
  return state.project.editor_settings.guides;
}
function schedulePaint() {
  if (scheduled) return;
  scheduled=true;
  requestAnimationFrame(() => { scheduled=false; paint(); });
}
function setupCanvas() {
  const viewport=$('viewport');
  if (!viewport) return;
  host=viewport;
  if (getComputedStyle(host).position==='static') host.style.position='relative';
  canvas=document.createElement('canvas');
  canvas.id='kaeGuideOverlay';
  canvas.setAttribute('aria-hidden','true');
  Object.assign(canvas.style,{position:'absolute',inset:'0',width:'100%',height:'100%',pointerEvents:'none',zIndex:'2'});
  host.append(canvas);
  ctx=canvas.getContext('2d',{alpha:true});
  const resize=()=>{
    const rect=host.getBoundingClientRect(),dpr=Math.max(1,window.devicePixelRatio||1);
    canvas.width=Math.max(1,Math.round(rect.width*dpr));
    canvas.height=Math.max(1,Math.round(rect.height*dpr));
    ctx.setTransform(dpr,0,0,dpr,0,0);
    schedulePaint();
  };
  observer=new ResizeObserver(resize); observer.observe(host);
  window.addEventListener('resize',resize,{passive:true});
  resize();
}
function line(x1,y1,x2,y2) { ctx.beginPath();ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.stroke(); }
function paint() {
  if (!ctx||!host) return;
  const rect=host.getBoundingClientRect(),w=rect.width,h=rect.height;
  ctx.clearRect(0,0,w,h);
  if (!state.project) return;
  const s=settings();
  if (!s.enabled) { const status=$('kaeGuideStatus');if(status)status.textContent='Guides disabled';return; }
  const color=/^#[0-9a-f]{6}$/i.test(s.color)?s.color:DEFAULTS.color;
  ctx.save();ctx.globalAlpha=Math.min(1,Math.max(.05,Number(s.opacity)||.55));
  ctx.strokeStyle=color;ctx.fillStyle=color;ctx.lineWidth=1;
  const zoom=Math.max(.1,Math.min(8,Number(state.view?.zoom)||1));
  const step=Math.max(8,Math.min(256,(Number(s.spacing)||32)*zoom));
  if(s.grid){
    ctx.globalAlpha*=.36;
    const panX=Number(state.view?.panX)||0,panY=Number(state.view?.panY)||0;
    const ox=((w/2+panX)%step+step)%step,oy=((h/2+panY)%step+step)%step;
    for(let x=ox;x<w;x+=step)line(x,0,x,h);
    for(let y=oy;y<h;y+=step)line(0,y,w,y);
    ctx.globalAlpha=Math.min(1,Math.max(.05,Number(s.opacity)||.55));
  }
  if(s.center){ctx.lineWidth=1.25;line(w/2,0,w/2,h);line(0,h/2,w,h/2);ctx.beginPath();ctx.arc(w/2,h/2,4,0,Math.PI*2);ctx.stroke();}
  if(s.thirds){ctx.setLineDash([5,5]);line(w/3,0,w/3,h);line(2*w/3,0,2*w/3,h);line(0,h/3,w,h/3);line(0,2*h/3,w,2*h/3);ctx.setLineDash([]);}
  if(s.head){
    const cx=w/2,cy=h*.28,rx=Math.min(w*.095,66),ry=rx*1.22;
    ctx.lineWidth=1.4;ctx.beginPath();ctx.ellipse(cx,cy,rx,ry,0,0,Math.PI*2);ctx.stroke();
    line(cx-rx,cy,cx+rx,cy);line(cx,cy-ry,cx,cy+ry);
    ctx.beginPath();ctx.ellipse(cx,cy+ry*.22,rx,ry*.42,0,0,Math.PI*2);ctx.stroke();
  }
  if(s.eyes || s.nose || s.mouth || s.ears || s.hairline){
    const cx=w/2,cy=h*.28,rx=Math.min(w*.095,66),ry=rx*1.22;
    ctx.lineWidth=1.25;
    if(s.eyes){
      const eyeY=cy-ry*.05,eyeGap=rx*.43,eyeW=rx*.22,eyeH=ry*.11;
      for(const ex of [cx-eyeGap,cx+eyeGap]){ctx.beginPath();ctx.ellipse(ex,eyeY,eyeW,eyeH,0,0,Math.PI*2);ctx.stroke();ctx.beginPath();ctx.arc(ex,eyeY,2.5,0,Math.PI*2);ctx.stroke();}
      line(cx-rx*.82,eyeY,cx+rx*.82,eyeY);
    }
    if(s.nose){line(cx,cy+ry*.02,cx-rx*.08,cy+ry*.38);line(cx-rx*.08,cy+ry*.38,cx+rx*.12,cy+ry*.4);ctx.beginPath();ctx.arc(cx,cy+ry*.4,rx*.16,0.15*Math.PI,0.85*Math.PI);ctx.stroke();}
    if(s.mouth){const my=cy+ry*.61;ctx.beginPath();ctx.ellipse(cx,my,rx*.28,ry*.065,0,0,Math.PI*2);ctx.stroke();line(cx-rx*.25,my,cx+rx*.25,my);}
    if(s.ears){for(const side of [-1,1]){ctx.beginPath();ctx.ellipse(cx+side*rx*1.04,cy+ry*.17,rx*.12,ry*.23,0,0,Math.PI*2);ctx.stroke();}}
    if(s.hairline){ctx.beginPath();ctx.ellipse(cx,cy-ry*.08,rx*.91,ry*.7,0,Math.PI*1.08,Math.PI*1.92);ctx.stroke();line(cx-rx*.85,cy+ry*.08,cx+rx*.85,cy+ry*.08);}
  }
  if(s.body){
    const cx=w/2,shoulderY=h*.43,hipY=h*.63,span=Math.min(w*.2,150);
    ctx.lineWidth=1.5;line(cx-span,shoulderY,cx+span,shoulderY);line(cx-span*.65,hipY,cx+span*.65,hipY);
    line(cx,shoulderY,cx,hipY);line(cx-span,shoulderY,cx-span*.72,h*.56);line(cx+span,shoulderY,cx+span*.72,h*.56);
    line(cx-span*.5,hipY,cx-span*.62,h*.88);line(cx+span*.5,hipY,cx+span*.62,h*.88);
    ctx.beginPath();ctx.arc(cx,shoulderY,3,0,Math.PI*2);ctx.arc(cx,hipY,3,0,Math.PI*2);ctx.stroke();
  }
  ctx.restore();
  const status=$('kaeGuideStatus');
  if(status)status.textContent='Guides active · editor overlay only · '+[s.grid&&'grid',s.center&&'axes',s.thirds&&'thirds',s.head&&'head',s.eyes&&'eyes',s.nose&&'nose',s.mouth&&'mouth',s.ears&&'ears',s.hairline&&'hairline',s.body&&'body'].filter(Boolean).join(', ');
}
function syncControls() {
  const s=settings();
  const map={kaeGuidesEnabled:'enabled',kaeGuideGrid:'grid',kaeGuideCenter:'center',kaeGuideThirds:'thirds',kaeGuideHead:'head',kaeGuideEyes:'eyes',kaeGuideNose:'nose',kaeGuideMouth:'mouth',kaeGuideEars:'ears',kaeGuideHairline:'hairline',kaeGuideBody:'body'};
  for(const [id,key] of Object.entries(map)){const el=$(id);if(el)el.checked=!!s[key];}
  for(const [id,key] of [['kaeGuideColor','color'],['kaeGuideOpacity','opacity'],['kaeGuideSpacing','spacing']]){
    const el=$(id);if(el)el.value=String(s[key]??DEFAULTS[key]);
  }
}
function persist() {
  if (!state.project) return;
  setState({dirty:true});
  bus.emit('project:changed',{label:'Update viewport guide settings'});
  schedulePaint();
}
function init() {
  if (!$('kaeGuidesEnabled')||!$('viewport')) return;
  setupCanvas();syncControls();
  const checks={kaeGuidesEnabled:'enabled',kaeGuideGrid:'grid',kaeGuideCenter:'center',kaeGuideThirds:'thirds',kaeGuideHead:'head',kaeGuideEyes:'eyes',kaeGuideNose:'nose',kaeGuideMouth:'mouth',kaeGuideEars:'ears',kaeGuideHairline:'hairline',kaeGuideBody:'body'};
  for(const [id,key] of Object.entries(checks))$(id).addEventListener('change',e=>{settings()[key]=e.target.checked;persist();});
  for(const [id,key] of [['kaeGuideColor','color'],['kaeGuideOpacity','opacity'],['kaeGuideSpacing','spacing']]){
    $(id).addEventListener('input',e=>{settings()[key]=key==='color'?e.target.value:Number(e.target.value);schedulePaint();});
    $(id).addEventListener('change',persist);
  }
  $('kaeGuideReset').addEventListener('click',()=>{state.project.editor_settings.guides={...DEFAULTS};syncControls();persist();});
  $('kaeGuideCenterView').addEventListener('click',()=>{const s=settings();s.centered=true;s.center=true;s.enabled=true;syncControls();persist();});
  bus.on('state',schedulePaint);
  bus.on('project:changed',()=>{syncControls();schedulePaint();});
  schedulePaint();
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
