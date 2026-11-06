/* Keep publisher ad creatives intact; collapse only wholly unfilled desktop slots. */
(function(){
function init(){
 for(const slot of document.querySelectorAll('.rc-ad-slot')){
  const frame=slot.querySelector('.rc-ad-frame');if(!frame)continue;
  const isFilled=()=>{
   for(const node of frame.children){
    if(node.tagName==='SCRIPT'||node.tagName==='STYLE')continue;
    const rect=node.getBoundingClientRect();
    if(rect.width<100||rect.height<45)continue;
    if(node.tagName==='IFRAME'){
     try{const doc=node.contentDocument;if(doc&&doc.readyState==='complete'&&doc.body&&!doc.body.children.length&&!doc.body.textContent.trim())continue}catch(_){}
    }
    return true;
   }
   return false;
  };
  const check=()=>{if(isFilled())slot.classList.remove('rc-ad-unfilled')};
  const observer=new MutationObserver(check);
  observer.observe(frame,{childList:true,subtree:false});
  setTimeout(()=>{if(!isFilled())slot.classList.add('rc-ad-unfilled')},12000);
 }
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
