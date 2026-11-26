(() => {
  "use strict";
  const activeScript = document.currentScript;
  const theme = activeScript && activeScript.dataset ? activeScript.dataset.theme || "tcs" : "tcs";
  const host = location.hostname.toLowerCase();
  if (theme === "webdev" && host !== "webdev.thechocostudios.bond" && host !== "webdev.choco-ai.xyz") return;
  if (document.getElementById("tcs-community-widget")) return;
  const palette = {
    gaming:["#17111f","#21182d","#f7f0ff","#b7a9c8","#c4a2f4","#1a1024","#4d4161"],
    eji:["#f7fff8","#fff","#173a36","#5c7770","#24aeb6","#fff","#d5ebe1"],
    legal:["#101827","#142033","#edf2ff","#a8b4ca","#a8c7ff","#13203a","#33445f"],
    template:["#f6f7f3","#fff","#20251f","#687166","#687c64","#fff","#dfe4da"],
    webdev:["#12110f","#1d1a16","#f4eee4","#aaa08f","#d8bd8d","#17130d","#554733"]
  };
  const c = palette[theme] || palette.legal;
  const root = document.createElement("div");
  root.id = "tcs-community-widget";
  root.dataset.theme = theme;
  const rules = [
    "#tcs-community-widget{--bg:"+c[0]+";--panel:"+c[1]+";--text:"+c[2]+";--muted:"+c[3]+";--accent:"+c[4]+";--accent-text:"+c[5]+";--border:"+c[6]+";position:fixed;right:clamp(12px,3vw,24px);bottom:clamp(12px,3vh,24px);z-index:2147483000;font-family:inherit;color:var(--text);line-height:1.4}",
    "#tcs-community-widget[data-theme=webdev]{left:clamp(12px,3vw,24px);right:auto}",
    "#tcs-community-widget *{box-sizing:border-box}",
    "#tcs-community-widget button,#tcs-community-widget a{font:inherit}",
    "#tcs-community-widget .trigger{display:flex;align-items:center;gap:9px;min-height:48px;padding:0 15px;border:1px solid var(--border);border-radius:999px;background:var(--accent);color:var(--accent-text);font-size:13px;font-weight:800;box-shadow:0 8px 28px #0003;cursor:pointer;transition:transform .18s ease}",
    "#tcs-community-widget .trigger:hover{transform:translateY(-2px)}",
    "#tcs-community-widget .trigger:focus-visible,#tcs-community-widget a:focus-visible,#tcs-community-widget .close:focus-visible{outline:3px solid var(--accent);outline-offset:3px}",
    "#tcs-community-widget .panel{position:absolute;right:0;bottom:calc(100% + 12px);width:min(366px,calc(100vw - 24px));max-height:min(72vh,570px);overflow:auto;padding:16px;border:1px solid var(--border);border-radius:18px;background:var(--panel);color:var(--text);box-shadow:0 18px 58px #0004}",
    "#tcs-community-widget[data-theme=webdev] .panel{left:0;right:auto}",
    "#tcs-community-widget .panel[hidden]{display:none!important}",
    "#tcs-community-widget .head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:13px}",
    "#tcs-community-widget .title{margin:0;color:var(--text);font-size:16px;font-weight:800}",
    "#tcs-community-widget .description{margin:4px 0 0;color:var(--muted);font-size:11px;line-height:1.55}",
    "#tcs-community-widget .close{display:grid;place-items:center;flex:0 0 30px;width:30px;height:30px;border:1px solid var(--border);border-radius:50%;background:transparent;color:var(--text);font-size:19px;cursor:pointer}",
    "#tcs-community-widget .group{margin-top:14px}",
    "#tcs-community-widget .group h3{margin:0 0 8px;color:var(--muted);font-size:10px;font-weight:800;letter-spacing:.12em;text-transform:uppercase}",
    "#tcs-community-widget .list{display:grid;gap:7px}",
    "#tcs-community-widget .link{display:grid;grid-template-columns:34px minmax(0,1fr) 14px;align-items:center;gap:10px;min-height:50px;padding:8px 10px;border:1px solid var(--border);border-radius:12px;background:var(--bg);color:var(--text);text-decoration:none;transition:border-color .18s ease,transform .18s ease}",
    "#tcs-community-widget .link:hover{transform:translateY(-1px);border-color:var(--accent)}",
    "#tcs-community-widget .mark{display:grid;place-items:center;width:32px;height:32px;border-radius:10px;background:var(--accent);color:var(--accent-text);font-size:10px;font-weight:900}",
    "#tcs-community-widget .copy{display:grid;gap:2px;min-width:0}",
    "#tcs-community-widget .copy strong{overflow-wrap:anywhere;color:var(--text);font-size:12px;font-weight:800;line-height:1.3}",
    "#tcs-community-widget .copy small{color:var(--muted);font-size:10px;line-height:1.3}",
    "@media(max-width:520px){#tcs-community-widget{right:12px;bottom:12px}#tcs-community-widget[data-theme=webdev]{left:12px;right:auto}#tcs-community-widget .trigger{min-height:46px;padding:0 13px}#tcs-community-widget .panel{width:calc(100vw - 24px);max-height:70vh;padding:14px}}",
    "@media(prefers-reduced-motion:reduce){#tcs-community-widget .trigger,#tcs-community-widget .link{transition:none}}"
  ].join("\n");
  const style = document.createElement("style");
  style.textContent = rules;
  document.head.appendChild(style);
  root.innerHTML = '<button class="trigger" type="button" aria-expanded="false" aria-controls="tcs-community-panel"><span aria-hidden="true">↗</span><span>Komunitas TCS</span><span aria-hidden="true">⌃</span></button><section class="panel" id="tcs-community-panel" role="dialog" aria-label="Komunitas TCS" hidden><div class="head"><div><h2 class="title">Terhubung dengan komunitas</h2><p class="description">Pilih saluran WhatsApp atau grup Facebook.</p></div><button class="close" type="button" aria-label="Tutup panel komunitas">×</button></div><div class="groups"></div></section>';
  const wa = [
    ["Arabia","https://whatsapp.com/channel/0029VbEInjlJENxvx8QAow1V"],
    ["Global","https://whatsapp.com/channel/0029VbANzQeDzgT6qV5P2623"],
    ["Amerika Latin","https://whatsapp.com/channel/0029Vb9bJwx3QxRsTGxwgR0L"],
    ["Saluran resmi TCS","https://whatsapp.com/channel/0029VbDj294CRs1s4uu2ZI3T"]
  ];
  const fb = [
    ["The Choco Studios Sharing","https://www.facebook.com/share/g/1GB8ivQdzy/"],
    ["UMKM Bersatu Promosi Jual Beli","https://www.facebook.com/share/g/19uLqnUvyk/"]
  ];
  function group(label,items,mark,type) {
    const section=document.createElement("section");section.className="group";
    const heading=document.createElement("h3");heading.textContent=label;
    const list=document.createElement("div");list.className="list";
    items.forEach(function(item){
      const a=document.createElement("a");a.className="link";a.href=item[1];a.target="_blank";a.rel="noopener noreferrer";
      a.setAttribute("aria-label",item[0]+" ("+type+"), buka di tab baru");
      const badge=document.createElement("span");badge.className="mark";badge.setAttribute("aria-hidden","true");badge.textContent=mark;
      const copy=document.createElement("span");copy.className="copy";
      const strong=document.createElement("strong");strong.textContent=item[0];
      const small=document.createElement("small");small.textContent=type;copy.append(strong,small);
      const arrow=document.createElement("span");arrow.textContent="↗";arrow.setAttribute("aria-hidden","true");
      a.append(badge,copy,arrow);list.appendChild(a);
    });
    section.append(heading,list);root.querySelector(".groups").appendChild(section);
  }
  group("Saluran WhatsApp",wa,"WA","Saluran WhatsApp");
  group("Grup Facebook",fb,"f","Grup Facebook");
  document.body.appendChild(root);
  const trigger=root.querySelector(".trigger"),panel=root.querySelector(".panel"),close=root.querySelector(".close");
  function toggle(open,restore){panel.hidden=!open;trigger.setAttribute("aria-expanded",String(open));trigger.lastElementChild.textContent=open?"⌄":"⌃";if(open)close.focus({preventScroll:true});else if(restore)trigger.focus({preventScroll:true});}
  trigger.addEventListener("click",function(){toggle(panel.hidden,false)});
  close.addEventListener("click",function(){toggle(false,true)});
  panel.addEventListener("click",function(event){if(event.target.closest("a"))toggle(false,false)});
  document.addEventListener("pointerdown",function(event){if(!panel.hidden&&!root.contains(event.target))toggle(false,false)});
  document.addEventListener("keydown",function(event){if(event.key==="Escape"&&!panel.hidden)toggle(false,true)});
})();