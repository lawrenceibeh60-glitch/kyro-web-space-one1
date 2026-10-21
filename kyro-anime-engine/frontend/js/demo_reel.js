(() => {
const canvas=document.getElementById('reel'),ctx=canvas.getContext('2d');
const W=1280,H=720,DURATION=24;
const captions=[
 ['SEQUENCE 01 / 04','THE AWAKENING','A hand-crafted motion study · rendered live by your browser'],
 ['SEQUENCE 02 / 04','WIND BEFORE THE STORM','Layered scenery · camera drift · atmospheric particles'],
 ['SEQUENCE 03 / 04','EDGE OF LIGHT','Procedural character motion · energy trails · cinematic timing'],
 ['SEQUENCE 04 / 04','DRAW. RIG. ANIMATE.','Your ideas, frame by frame — inside KYRO ANIME ENGINE']
];
let started=performance.now(),pausedAt=0,paused=false,recorder=null,chunks=[],recording=false;
const $=id=>document.getElementById(id);
function path(points,fill,stroke,width=1){ctx.beginPath();points.forEach((p,i)=>i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1]));if(fill){ctx.closePath();ctx.fillStyle=fill;ctx.fill()}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=width;ctx.stroke()}}
function glow(x,y,r,color){const g=ctx.createRadialGradient(x,y,0,x,y,r);g.addColorStop(0,color);g.addColorStop(1,'transparent');ctx.fillStyle=g;ctx.fillRect(x-r,y-r,r*2,r*2)}
function draw(t){
 const s=t% DURATION,beat=s* Math.PI*2/3,cam=Math.sin(s*.28)*22;
 const sky=ctx.createLinearGradient(0,0,0,H);sky.addColorStop(0,'#101c37');sky.addColorStop(.52,'#344f75');sky.addColorStop(1,'#df976e');ctx.fillStyle=sky;ctx.fillRect(0,0,W,H);
 glow(900+Math.sin(s*.16)*45,230,210,'#f3c68a44');ctx.fillStyle='#f5d5a0';ctx.beginPath();ctx.arc(900+Math.sin(s*.16)*45,230,58,0,Math.PI*2);ctx.fill();
 // distant ridges
 for(let layer=0;layer<4;layer++){const y=380+layer*63,amp=30+layer*15,shift=(s*(6+layer*8)+cam*(layer*.4))%(W+300);ctx.beginPath();ctx.moveTo(-100,H);for(let x=-100;x<=W+100;x+=50){const xx=x-shift;ctx.lineTo(x,y+Math.sin((xx+layer*90)/140)*amp+Math.cos(xx/260)*amp*.55)}ctx.lineTo(W+100,H);ctx.closePath();ctx.fillStyle=['#263b58','#1d3049','#142439','#0b1625'][layer];ctx.fill()}
 // floating light fragments
 for(let i=0;i<80;i++){const x=(i*197+s*(12+(i%5)*5))%(W+20),y=(i*83+Math.sin(s*.7+i)*40+H-(s*25+i*11)%H)%H;ctx.globalAlpha=.18+(i%5)*.09;ctx.fillStyle=i%3?'#9dcaff':'#ffd9a0';ctx.fillRect(x,y,1+(i%3),1+(i%2))}
 ctx.globalAlpha=1;
 // foreground floor and perspective streaks
 const floor=ctx.createLinearGradient(0,480,0,H);floor.addColorStop(0,'#1c2a3b');floor.addColorStop(1,'#080e19');ctx.fillStyle=floor;ctx.fillRect(0,490,W,230);
 for(let i=0;i<24;i++){const y=500+i*i*.7;ctx.strokeStyle='#9cc9f0'+Math.floor(10+i*1.6).toString(16).padStart(2,'0');ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(640+(i-12)*9,490);ctx.lineTo(i*85-200,y);ctx.stroke()}
 // aura and silhouette character
 const cx=590+Math.sin(s*.65)*16+cam*.25,ground=590,walk=Math.sin(s*5),swing=Math.sin(s*3.1),charge=Math.max(0,Math.sin((s-10)*.65));
 glow(cx,410,140,'#3b9ff233');
 ctx.save();ctx.translate(cx,0);
 // cape flowing behind
 path([[-18,300],[-68+walk*15,344],[-104+Math.sin(s*4)*25,490],[-40,466],[6,355]],'#101c2b','#607f9d',3);
 // legs in stride
 ctx.lineCap='round';ctx.lineJoin='round';
 ctx.strokeStyle='#0a111d';ctx.lineWidth=31;ctx.beginPath();ctx.moveTo(-10,440);ctx.lineTo(-23+walk*25,505);ctx.lineTo(-44+walk*45,ground-2);ctx.stroke();
 ctx.beginPath();ctx.moveTo(13,440);ctx.lineTo(31-walk*24,503);ctx.lineTo(54-walk*35,ground-2);ctx.stroke();
 ctx.strokeStyle='#526982';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(-23+walk*25,505);ctx.lineTo(-44+walk*45,ground-2);ctx.moveTo(31-walk*24,503);ctx.lineTo(54-walk*35,ground-2);ctx.stroke();
 // torso coat
 path([[-28,286],[22,281],[43,371],[22,448],[-28,448],[-48,361]],'#111b2a','#7290ad',3);
 path([[-18,292],[0,350],[16,294],[8,412],[-6,412]],'#263f5b','#7899b8',2);
 // arm and blade
 ctx.strokeStyle='#101827';ctx.lineWidth=20;ctx.beginPath();ctx.moveTo(-30,310);ctx.lineTo(-54+swing*12,366);ctx.stroke();
 ctx.beginPath();ctx.moveTo(23,310);ctx.lineTo(51+swing*10,355);ctx.stroke();
 const bx=50+swing*10,by=355;
 ctx.save();ctx.translate(bx,by);ctx.rotate(-.85+Math.sin(s*1.6)*.12-charge*.22);
 glow(0,-75,50,'#54baff55');path([[-5,0],[-8,-125],[0,-165],[8,-124],[5,0]],'#d6e8ff','#71caff',2);path([[-7,-10],[-22,-26],[0,-19],[22,-26],[7,-10]],'#caa35d','#ffe0a1',2);ctx.restore();
 // neck and head
 ctx.fillStyle='#c58e77';ctx.fillRect(-10,255,22,30);
 ctx.fillStyle='#d6a48b';ctx.beginPath();ctx.ellipse(1,226,34,43,-.08,0,Math.PI*2);ctx.fill();
 // hair silhouette spikes
 path([[-31,228],[-42,192],[-20,200],[-15,170],[1,192],[17,165],[21,198],[43,187],[32,225],[22,247],[14,217],[-5,238],[-17,218]],'#111827','#5c83a9',2);
 ctx.strokeStyle='#8fcfff';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(-23,231);ctx.lineTo(-6,230);ctx.lineTo(5,236);ctx.stroke();
 // eye glint
 ctx.fillStyle='#8fe5ff';ctx.fillRect(12,225,9,3);glow(17,226,14,'#56caff77');
 // trim and wind ribbons
 ctx.strokeStyle='#d3a85f';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(-27,315);ctx.lineTo(8,367);ctx.lineTo(19,421);ctx.stroke();
 for(let i=0;i<3;i++){ctx.globalAlpha=.45+i*.16;ctx.strokeStyle=i%2?'#6bc7ff':'#f5d49b';ctx.lineWidth=2+i*.5;ctx.beginPath();ctx.moveTo(-50,320+i*25);ctx.bezierCurveTo(-110+Math.sin(s*3+i)*30,340+i*20,-70+Math.cos(s*2+i)*40,430+i*20,-130+Math.sin(s*2.3+i)*60,460+i*15);ctx.stroke()}ctx.globalAlpha=1;
 ctx.restore();
 // energy ring burst on climax
 const burst=Math.max(0,Math.sin((s-12)*Math.PI/5));if(burst>.08){ctx.save();ctx.translate(cx,390);ctx.rotate(s*.4);ctx.strokeStyle='#7ed5ff';ctx.globalAlpha=.25+burst*.5;ctx.lineWidth=2+burst*5;ctx.beginPath();ctx.ellipse(0,0,80+burst*180,155+burst*90,0,0,Math.PI*2);ctx.stroke();ctx.globalAlpha=.8;for(let i=0;i<36;i++){const a=i*Math.PI*2/36+s;const r=90+burst*120;ctx.strokeStyle=i%3?'#69cfff':'#ffe1a0';ctx.beginPath();ctx.moveTo(Math.cos(a)*r,Math.sin(a)*r);ctx.lineTo(Math.cos(a)*(r+15+burst*60),Math.sin(a)*(r+15+burst*60));ctx.stroke()}ctx.restore()}
 // cinematic HUD ticks and title beats
 ctx.strokeStyle='#b8d7f955';ctx.lineWidth=1;ctx.strokeRect(42,42,W-84,H-84);for(let i=0;i<12;i++){ctx.beginPath();ctx.moveTo(42+i*8,42);ctx.lineTo(42+i*8,50);ctx.moveTo(W-42-i*8,H-42);ctx.lineTo(W-42-i*8,H-50);ctx.stroke()}
 const fade=Math.min(1,s*1.3,(DURATION-s)*2);ctx.globalAlpha=Math.max(0,fade);
 if(s>17){ctx.fillStyle='#f0c46d';ctx.font='800 16px system-ui';ctx.fillText('KAE / MOTION SYSTEM',72,98);ctx.fillStyle='#dce9fb';ctx.font='800 42px system-ui';ctx.fillText('EVERY FRAME HAS A PURPOSE.',72,145);ctx.fillStyle='#9fb4cf';ctx.font='15px system-ui';ctx.fillText('Draw  ·  Rig  ·  Animate  ·  Export',74,175)}
 ctx.globalAlpha=1;
 const seq=Math.min(3,Math.floor(s/6));$('captionIndex').textContent=captions[seq][0];$('captionTitle').textContent=captions[seq][1];$('captionSub').textContent=captions[seq][2];
 $('progress').style.width=(s/DURATION*100)+'%';$('timecode').textContent='00:'+String(Math.floor(s)).padStart(2,'0')+' / 00:24';
}
function tick(now){if(!paused){const t=((now-started)/1000)%DURATION;draw(t)}requestAnimationFrame(tick)}
$('playPause').onclick=()=>{paused=!paused;if(paused)pausedAt=performance.now();else started+=performance.now()-pausedAt;$('playPause').textContent=paused?'▶ Play':'Ⅱ Pause'};
$('restart').onclick=()=>{started=performance.now();paused=false;$('playPause').textContent='Ⅱ Pause';draw(0)};
$('record').onclick=async()=>{
 if(recording){recorder?.stop();return}
 if(!canvas.captureStream||!window.MediaRecorder){$('recordStatus').textContent='This browser does not support WebM recording. The animated demo still plays normally.';return}
 try{
  const stream=canvas.captureStream(30);let mime='video/webm;codecs=vp9';if(!MediaRecorder.isTypeSupported(mime))mime='video/webm';
  recorder=new MediaRecorder(stream,{mimeType:mime,videoBitsPerSecond:5000000});chunks=[];recording=true;$('record').textContent='■ Stop & save';$('recordStatus').textContent='Recording live 1280 × 720 canvas at 30 FPS…';
  recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
  recorder.onstop=()=>{const blob=new Blob(chunks,{type:'video/webm'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='KAE-Cinematic-Demo.webm';a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);stream.getTracks().forEach(track=>track.stop());document.querySelector('.reel-stage').classList.remove('recording');recording=false;$('record').textContent='● Record WebM';$('recordStatus').textContent='Video saved to your device · '+(blob.size/1024/1024).toFixed(1)+' MB.'};
  document.querySelector('.reel-stage').classList.add('recording');recorder.start(250);paused=false;$('playPause').textContent='Ⅱ Pause';started=performance.now();
 }catch(error){recording=false;$('recordStatus').textContent='Could not start recording: '+error.message}
};
draw(0);requestAnimationFrame(tick);
})();