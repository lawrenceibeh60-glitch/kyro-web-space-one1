// KAE Geometry Nodes: saved procedural 2D graph editor and lightweight evaluator.
import { state, setState } from '../core/state_manager.js';
import { bus } from '../core/event_bus.js';
const $ = id => document.getElementById(id);
const TYPES = {
 circle:{label:'Circle',inputs:[],outputs:['Geometry'],defaults:{radius:48,segments:32}},
 rectangle:{label:'Rectangle',inputs:[],outputs:['Geometry'],defaults:{width:96,height:64}},
 transform:{label:'Transform 2D',inputs:['Geometry'],outputs:['Geometry'],defaults:{x:0,y:0,rotation:0,scale:1}},
 join:{label:'Join Geometry',inputs:['Geometry A','Geometry B'],outputs:['Geometry'],defaults:{}},
 output:{label:'Group Output',inputs:['Geometry'],outputs:[],defaults:{}}
};
const makeId=p=>p+'_'+Math.random().toString(36).slice(2,9);
let activeGraphId=null,selectedNodeId=null,pendingFrom=null,drag=null;
function defaultGraph(){const a={id:makeId('circle'),type:'circle',x:60,y:80,params:{...TYPES.circle.defaults}},b={id:makeId('transform'),type:'transform',x:320,y:80,params:{...TYPES.transform.defaults}},c={id:makeId('output'),type:'output',x:590,y:80,params:{}};return{id:makeId('graph'),name:'Geometry Graph',nodes:[a,b,c],links:[{from:a.id,to:b.id},{from:b.id,to:c.id}]};}
function graphs(){if(!Array.isArray(state.project.node_graphs))state.project.node_graphs=[];return state.project.node_graphs;}
function graph(){return graphs().find(g=>g.id===activeGraphId)||graphs()[0]||null;}
function node(g,id){return g.nodes.find(n=>n.id===id);}
function commit(label){setState({dirty:true});bus.emit('project:changed',{label});render();}
function cycle(g,from,to){if(from===to)return true;const seen=new Set();function visit(id){if(id===from)return true;if(seen.has(id))return false;seen.add(id);return g.links.filter(l=>l.from===id).some(l=>visit(l.to));}return visit(to);}
function render(){
 const g=graph(),canvas=$('geoCanvas');if(!g||!canvas)return;
 const sel=$('geoGraphSelect');sel.replaceChildren();graphs().forEach(x=>{const o=document.createElement('option');o.value=x.id;o.textContent=x.name;sel.append(o);});sel.value=activeGraphId;
 canvas.replaceChildren();const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('class','geo-links');svg.setAttribute('viewBox','0 0 1100 760');svg.setAttribute('preserveAspectRatio','none');
 g.links.forEach(l=>{const a=node(g,l.from),b=node(g,l.to);if(!a||!b)return;const p=document.createElementNS(ns,'path');p.setAttribute('class','geo-link');p.setAttribute('d','M '+(a.x+178)+' '+(a.y+62)+' C '+(a.x+235)+' '+(a.y+62)+', '+(b.x-55)+' '+(b.y+62)+', '+b.x+' '+(b.y+62));svg.append(p);});canvas.append(svg);
 g.nodes.forEach(n=>{const meta=TYPES[n.type];if(!meta)return;const el=document.createElement('section');el.className='geo-node'+(n.id===selectedNodeId?' selected':'');el.style.left=n.x+'px';el.style.top=n.y+'px';
 const head=document.createElement('header');head.className='geo-node-head';const title=document.createElement('span');title.textContent=meta.label;const del=document.createElement('button');del.textContent='×';del.title='Delete node';del.onclick=e=>{e.stopPropagation();g.nodes=g.nodes.filter(x=>x.id!==n.id);g.links=g.links.filter(l=>l.from!==n.id&&l.to!==n.id);selectedNodeId=null;pendingFrom=null;commit('Delete geometry node');};head.append(title,del);
 head.onpointerdown=e=>{if(e.target===del)return;selectedNodeId=n.id;el.classList.add('selected');document.querySelectorAll('.geo-node').forEach(other=>{if(other!==el)other.classList.remove('selected');});renderInspector(graph());head.setPointerCapture(e.pointerId);};
 head.onpointermove=e=>{if(!drag||drag.id!==n.id)return;const q=node(graph(),n.id);q.x=Math.max(0,drag.x+e.clientX-drag.sx);q.y=Math.max(0,drag.y+e.clientY-drag.sy);el.style.left=q.x+'px';el.style.top=q.y+'px';};
 head.onpointerup=()=>{if(drag&&drag.id===n.id){drag=null;commit('Move geometry node');}};
 el.onclick=()=>{selectedNodeId=n.id;render();};const body=document.createElement('div');body.className='geo-node-body';
 meta.inputs.forEach((name,i)=>{const row=document.createElement('div');row.className='geo-socket-row';const socket=document.createElement('button');socket.className='geo-socket input'+(pendingFrom?' pending':'');socket.title='Connect input '+name;socket.onclick=e=>{e.stopPropagation();if(pendingFrom&&!cycle(g,pendingFrom.nodeId,n.id)){g.links=g.links.filter(l=>!(l.to===n.id&&(l.input||0)===i));g.links.push({from:pendingFrom.nodeId,to:n.id,input:i});pendingFrom=null;commit('Connect geometry nodes');}else{pendingFrom=null;$('geoStatus').textContent='Connection rejected or cancelled';render();}};row.append(socket,document.createTextNode(name));body.append(row);});
 Object.entries(meta.defaults).forEach(([k,v])=>{const row=document.createElement('div');row.className='geo-socket-row';row.textContent=k;const val=document.createElement('span');val.className='geo-node-type';val.textContent=String(n.params[k]??v);row.append(val);body.append(row);});
 meta.outputs.forEach(name=>{const row=document.createElement('div');row.className='geo-socket-row';row.append(document.createTextNode(name));const socket=document.createElement('button');socket.className='geo-socket';socket.title='Start connection from '+name;socket.onclick=e=>{e.stopPropagation();pendingFrom={nodeId:n.id};$('geoStatus').textContent='Choose an input socket';render();};row.append(socket);body.append(row);});
 el.append(head,body);canvas.append(el);});
 renderInspector(g);renderPreview(g);
}
function renderInspector(g){const host=$('geoInspector');host.replaceChildren();const n=node(g,selectedNodeId);if(!n){const p=document.createElement('p');p.className='hint';p.textContent='Select a node to inspect its parameters.';host.append(p);return;}Object.entries(TYPES[n.type].defaults).forEach(([k,v])=>{const label=document.createElement('label');label.textContent=k.replaceAll('_',' ');const input=document.createElement('input');input.type='number';input.step='any';input.value=n.params[k]??v;input.onchange=()=>{const x=Number(input.value);if(Number.isFinite(x)){n.params[k]=x;commit('Change geometry node parameter');}};label.append(input);host.append(label);});const p=document.createElement('p');p.className='geo-node-type';p.textContent='Parameters are stored in this project and included in .kae JSON.';host.append(p);}
function evaluate(g,n,stack=new Set()){if(stack.has(n.id))return[];const seen=new Set(stack);seen.add(n.id);function input(i=0){const l=g.links.find(x=>x.to===n.id&&(x.input||0)===i),src=l&&node(g,l.from);return src?evaluate(g,src,seen):[];}const p=n.params||{};
 if(n.type==='circle'){const r=Math.max(1,Math.min(400,+p.radius||48)),count=Math.max(8,Math.min(256,Math.round(+p.segments||32)));return[{points:Array.from({length:count},(_,i)=>[Math.cos(i*Math.PI*2/count)*r,Math.sin(i*Math.PI*2/count)*r])}];}
 if(n.type==='rectangle'){const w=Math.max(1,Math.min(800,+p.width||96))/2,h=Math.max(1,Math.min(800,+p.height||64))/2;return[{points:[[-w,-h],[w,-h],[w,h],[-w,h]]}];}
 if(n.type==='join')return input(0).concat(input(1));
 if(n.type==='transform'){const a=(+p.rotation||0)*Math.PI/180,s=Math.max(.01,Math.min(100,+p.scale||1)),c=Math.cos(a),sn=Math.sin(a);return input(0).map(sh=>({...sh,points:sh.points.map(([x,y])=>[x*s*c-y*s*sn+(+p.x||0),x*s*sn+y*s*c+(+p.y||0)])}));}
 if(n.type==='output')return input(0);return[];}
function renderPreview(g){const host=$('geoPreview');host.replaceChildren();const out=g.nodes.find(n=>n.type==='output'),shapes=out?evaluate(g,out):[],ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','-160 -100 320 200');const axis=document.createElementNS(ns,'path');axis.setAttribute('d','M-160 0H160 M0 -100V100');axis.setAttribute('stroke','#3d4653');axis.setAttribute('stroke-width','.7');svg.append(axis);shapes.forEach(sh=>{const p=document.createElementNS(ns,'polygon');p.setAttribute('points',sh.points.map(q=>q.join(',')).join(' '));p.setAttribute('fill','#e6b84c22');p.setAttribute('stroke','#e6b84c');p.setAttribute('stroke-width','2');svg.append(p);});host.append(svg);$('geoStatus').textContent=g.nodes.length+' nodes · '+g.links.length+' links · '+shapes.length+' generated shape(s) · '+(state.dirty?'modified':'loaded');}
export function initGeometryNodes(){if(!$('geoCanvas'))return;if(!graphs().length)graphs().push(defaultGraph());activeGraphId=graphs()[0].id;
 $('geoAddNode').onclick=()=>{const type=$('geoNodeType').value;if(!TYPES[type])return;const n={id:makeId(type),type,x:80+Math.round(Math.random()*240),y:80+Math.round(Math.random()*220),params:{...TYPES[type].defaults}};graph().nodes.push(n);selectedNodeId=n.id;commit('Add geometry node');};
 $('geoNewGraph').onclick=()=>{const name=prompt('New geometry graph name','Geometry Graph '+(graphs().length+1));if(!name?.trim())return;const g=defaultGraph();g.name=name.trim().slice(0,120);graphs().push(g);activeGraphId=g.id;selectedNodeId=null;commit('Create geometry graph');};
 $('geoDeleteGraph').onclick=()=>{if(graphs().length<2){$('geoStatus').textContent='Keep at least one graph in the project';return;}const g=graph();if(!g||!confirm('Delete geometry graph "'+g.name+'"?'))return;state.project.node_graphs=graphs().filter(x=>x.id!==g.id);activeGraphId=graphs()[0].id;selectedNodeId=null;pendingFrom=null;commit('Delete geometry graph');};
 $('geoGraphSelect').onchange=e=>{activeGraphId=e.target.value;selectedNodeId=null;pendingFrom=null;render();};render();
 bus.on('project:changed',()=>{if(!state.project)return;if(!Array.isArray(state.project.node_graphs))state.project.node_graphs=[];if(!state.project.node_graphs.length){state.project.node_graphs.push(defaultGraph());activeGraphId=state.project.node_graphs[0].id;}else if(!state.project.node_graphs.some(g=>g.id===activeGraphId))activeGraphId=state.project.node_graphs[0].id;render();});
}
