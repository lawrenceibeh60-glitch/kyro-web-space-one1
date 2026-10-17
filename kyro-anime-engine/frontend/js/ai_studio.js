import { request } from './api/client.js';
const history = [];
let reference = null, imageUrl = null;
function el(tag, attrs = {}, text = '') {
  const node = document.createElement(tag);
  for (const [key,value] of Object.entries(attrs)) {
    if (key === 'class') node.className = value;
    else node.setAttribute(key,value);
  }
  if (text) node.textContent = text;
  return node;
}
export function initAIStudio() {
  if (document.getElementById('aiStudio')) return;
  const launch = el('button',{id:'aiLaunch',class:'ai-launch',title:'Open AI character studio'},'AI Studio');
  document.querySelector('.topbar .spacer')?.after(launch);
  const root = el('section',{id:'aiStudio',class:'ai-studio',hidden:''});
  const side=el('div',{class:'ai-side'}), head=el('header',{class:'ai-head'});
  head.append(el('span',{},'KAE / AI CHARACTER STUDIO'));
  const close=el('button',{type:'button','aria-label':'Close AI Studio'},'Close'); head.append(close);
  const thread=el('div',{class:'ai-thread','aria-live':'polite'});
  const compose=el('form',{class:'ai-compose'});
  const input=el('textarea',{placeholder:'Describe a character, pose, expression, outfit, or animation idea…',maxlength:'12000'});
  const actions=el('div',{class:'ai-actions'});
  const send=el('button',{class:'primary',type:'submit'},'Ask xKiro'), generate=el('button',{type:'button'},'Generate image');
  actions.append(send,generate); compose.append(input,actions); side.append(head,thread,compose);
  const preview=el('div',{class:'ai-preview'}), previewHead=el('header',{class:'ai-head'},'CHARACTER OUTPUT');
  const body=el('div',{class:'ai-preview-body'}), status=el('div',{class:'ai-status'},'Checking xKiro configuration…');
  const stage=el('div',{class:'ai-image-stage'}), image=el('img',{alt:'Generated anime character preview',hidden:''}); stage.append(image);
  const prompt=el('textarea',{class:'ai-prompt',placeholder:'Image prompt used for generation'});
  const previewActions=el('div',{class:'ai-actions'}), showRef=el('button',{type:'button',disabled:''},'Show over canvas');
  const download=el('a',{hidden:'',download:'kae-character.png'},'Save image');
  download.style.cssText='padding:8px 10px;border:1px solid var(--line);color:inherit;text-decoration:none;font-size:12px';
  previewActions.append(showRef,download);
  const note=el('p',{class:'ai-note'},'Canvas reference is a visual guide, not a rigged layer. Image-to-editable-parts and bone binding are the next integration step. Generated images are not uploaded to your project automatically.');
  body.append(status,stage,prompt,previewActions,note); preview.append(previewHead,body); root.append(side,preview); document.body.append(root);
  function addMessage(role,content) { const m=el('div',{class:'ai-msg '+role}); m.textContent=content; thread.append(m); thread.scrollTop=thread.scrollHeight; }
  function setBusy(value) { send.disabled=value; generate.disabled=value; if(value) status.textContent='Working…'; }
  async function ask() {
    const message=input.value.trim(); if(!message)return; input.value=''; addMessage('user',message); history.push({role:'user',content:message}); setBusy(true);
    try {
      const result=await request('POST','/api/ai/chat',{message,history:history.slice(-13,-1)});
      addMessage('assistant',result.reply); history.push({role:'assistant',content:result.reply}); status.textContent='Chat ready · '+(result.model||'xKiro');
      if(/generate|draw|create an image|make an image/i.test(message)) prompt.value=message;
    } catch(error) { addMessage('assistant','AI unavailable: '+error.message); status.textContent=error.message; }
    finally { setBusy(false); }
  }
  compose.addEventListener('submit',event=>{event.preventDefault();ask();});
  input.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();ask();}});
  generate.addEventListener('click',async()=>{
    const description=prompt.value.trim()||input.value.trim()||[...history].reverse().find(x=>x.role==='user')?.content||'';
    if(!description){status.textContent='Describe the character first.';input.focus();return;}
    prompt.value=description; setBusy(true);
    try {
      const result=await request('POST','/api/ai/images',{prompt:description}), data=result.image||{};
      imageUrl=data.url||(data.b64_json?'data:image/png;base64,'+data.b64_json:null);
      if(!imageUrl)throw new Error('Image provider returned no usable image.');
      image.src=imageUrl; image.hidden=false; showRef.disabled=false; download.href=imageUrl; download.hidden=false;
      status.textContent='Image generated. Show it over the canvas as a temporary visual reference.';
      if(data.revised_prompt)prompt.value=data.revised_prompt;
    } catch(error) { status.textContent='Image generation failed: '+error.message; addMessage('assistant','Image generation failed: '+error.message); }
    finally { setBusy(false); }
  });
  function clearReference(){reference?.remove();reference=null;showRef.textContent='Show over canvas';}
  showRef.addEventListener('click',()=>{
    const viewport=document.getElementById('viewport'); if(!viewport||!imageUrl)return;
    if(reference){clearReference();return;}
    reference=el('img',{class:'ai-reference',alt:'Temporary AI image reference overlay'}); reference.src=imageUrl;
    if(getComputedStyle(viewport).position==='static')viewport.style.position='relative';
    viewport.append(reference); showRef.textContent='Hide canvas reference'; root.hidden=true;
  });
  launch.addEventListener('click',()=>{root.hidden=false;input.focus();});
  close.addEventListener('click',()=>{root.hidden=true;});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!root.hidden)root.hidden=true;});
  addMessage('assistant','Describe your anime character or animation idea. Ask xKiro to refine the design, then generate an image. The generated image can be shown over the canvas as a temporary reference.');
  request('GET','/api/ai/status').then(result=>{status.textContent=result.configured?'xKiro configured · '+result.chat_model+' · image route '+(result.image_configured?'custom':'default OpenAI-compatible'):'xKiro not configured: set XKIRO_API_KEY on the server. Image generation may also require XKIRO_IMAGE_URL.';}).catch(()=>{});
}
