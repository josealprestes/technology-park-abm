"use strict";
(async () => {
const $ = id => document.getElementById(id);
let data;
try { const bytes=Uint8Array.from(atob($("evidence").textContent.trim()),char=>char.charCodeAt(0));const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));data=JSON.parse(await new Response(stream).text()); }
catch (_) { $("status").textContent="Abra a versão gerada desta prévia para carregar as execuções.";document.querySelectorAll("button").forEach(b=>b.disabled=true);return; }
const scenarios = new Map(data.scenarios.map(s=>[s.id,s]));
const state = {step:0,n:4,horizon:60,period:0,key:"productive_tie_count",conditions:{...data.conditions},selected:{...data.conditions},drafts:{},mode:"observe",base:1,seeds:[1,2,3,4],prepared:false,engineAvailable:false,busy:false,job:null,timer:null,hits:[]};
const buildStamp=()=>`v${data.version}`;
$("edition-build").textContent=buildStamp();
const meta = {
 productive_tie_count:{label:"Parcerias produtivas",unit:"Parcerias no limiar configurado · média de contagens",digits:1},
 congestion:{label:"Congestionamento",unit:"Razão demanda / capacidade · acima de 1 há saturação",digits:2},
 innovation_cumulative:{label:"Inovações acumuladas",unit:"Eventos acumulados no modelo · média de contagens",digits:1},
 knowledge_mean:{label:"Conhecimento médio",unit:"Estoque médio por startup ativa · unidades do modelo",digits:2},
 capital_total:{label:"Capital total",unit:"Capital das startups ativas · unidades do modelo, sem conversão para R$",digits:1},
 active_startup_count:{label:"Startups ativas",unit:"Startups presentes · média de contagens",digits:1}
};
const typeNames={startup:"startup",anchor:"empresa-âncora",university:"universidade",investor:"investidor",worker:"trabalhador"};
const nodeColors={startup:"#009e73",anchor:"#e69f00",university:"#f0e442",investor:"#56b4e9",worker:"#cc79a7"};
const edgeColors={partnership:"#009e73",investment:"#56b4e9",hiring:"#cc79a7"};
const edgeDashes={partnership:[],investment:[6,4],hiring:[2,4]};
const fmt=(n,d=1)=>new Intl.NumberFormat("pt-BR",{minimumFractionDigits:d,maximumFractionDigits:d}).format(n);
const signed=(n,d=1)=>(n>0?"+":"")+fmt(n,d);
const mean=xs=>xs.reduce((a,b)=>a+b,0)/xs.length;
const quantile=(values,p)=>{const v=[...values].sort((a,b)=>a-b),t=p*(v.length-1),i=Math.floor(t);return v[i]+(v[Math.min(i+1,v.length-1)]-v[i])*(t-i);};
const scenario=c=>scenarios.get(state.conditions[c]);
const sourceScenario=c=>scenarios.get(state.selected[c]);
const activeConditions=()=>state.mode==="observe"?["A"]:["A","B"];
const runs=c=>scenario(c).runs.slice(0,state.n);
const recordAt=(run,p)=>p===0?run.initial:run.history[p-1];
const finals=(c,key=state.key)=>runs(c).map(run=>recordAt(run,state.period)[key]);
const average=(c,key=state.key)=>mean(finals(c,key));
const configFlat=config=>Object.fromEntries(Object.entries(config).flatMap(([k,v])=>k==="policy"?Object.entries(v).map(([pk,pv])=>["policy__"+pk,pv]):[[k,v]]));
const display=v=>typeof v==="number"?(Number.isFinite(v)?new Intl.NumberFormat("pt-BR",{maximumFractionDigits:5}).format(v):"—"):typeof v==="boolean"?(v?"sim":"não"):v===null?"não definido":Array.isArray(v)?v.join(", "):({active:"ativa",passive:"passiva",none:"nenhum",baseline:"padrão",aggregates:"agregados",empirical:"empírico",central_firm:"empresa central",funding:"financiamento"}[v]||String(v));
function differences(){const a=configFlat(scenario("A").config),b=configFlat(scenario("B").config);return Object.keys(a).filter(k=>k!=="seed"&&JSON.stringify(a[k])!==JSON.stringify(b[k]));}
function appendRow(target,values){const row=document.createElement("tr");values.forEach((value,i)=>{const cell=document.createElement(i===0?"th":"td");if(i===0)cell.scope="row";cell.textContent=value;row.append(cell);});target.append(row);}
function renderScenarios(){renderScenarioCards();setConditionLabels();}
function scopeText(){const seeds=state.seeds.slice(0,state.n);return `Simulação · período visível ${state.period} de ${state.horizon} · sementes ${seeds.join(", ")} · ${state.mode==="observe"?state.n+" execuções de um cenário":state.n+" pares A/B"}`;}
function aggregate(c,end=state.period){return Array.from({length:end+1},(_,p)=>{const v=runs(c).map(run=>recordAt(run,p)[state.key]);return {period:p,mean:mean(v),p10:quantile(v,.1),p90:quantile(v,.9)};});}
function paired(){const a=finals("A"),d=finals("B").map((v,i)=>v-a[i]);return {positive:d.filter(v=>v>1e-9).length,negative:d.filter(v=>v< -1e-9).length,equal:d.filter(v=>Math.abs(v)<=1e-9).length};}
/* RENDER_FUNCTION */
function stop(){if(state.timer!==null)clearInterval(state.timer);state.timer=null;$("play-pause").textContent="Reproduzir evolução";$("play-pause").setAttribute("aria-pressed","false");}
function seek(p){state.period=Math.max(0,Math.min(state.horizon,p));document.querySelectorAll(".checklist input").forEach(input=>input.checked=false);if(state.period===state.horizon)stop();update();}
function canvasContext(canvas){const rect=canvas.getBoundingClientRect(),dpr=Math.min(window.devicePixelRatio||1,2);canvas.width=Math.round(rect.width*dpr);canvas.height=Math.round(rect.height*dpr);const ctx=canvas.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);return {ctx,w:rect.width,h:rect.height};}
function drawTrajectory(){
 const canvas=$("trajectory"),{ctx,w,h}=canvasContext(canvas);if(!w)return;
 const all=activeConditions().flatMap(c=>aggregate(c,state.horizon)),left=w<500?52:68,right=18,top=24,bottom=44;
 const rawMax=Math.max(...all.map(v=>Math.max(v.mean,v.p90)),state.key==="congestion"?1:0,1e-9),target=rawMax/4,power=Math.pow(10,Math.floor(Math.log10(target))),ratio=target/power;
 const tick=[1,2,5,10].find(v=>v>=ratio)*power,ymax=Math.max(tick,Math.ceil(rawMax/tick)*tick),x=p=>left+p/state.horizon*(w-left-right),y=v=>h-bottom-v/ymax*(h-top-bottom);
 ctx.font='12px "Geist Mono",monospace';ctx.textBaseline="middle";
 for(let v=0;v<=ymax+tick*.01;v+=tick){ctx.strokeStyle="#deded8";ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(left,y(v));ctx.lineTo(w-right,y(v));ctx.stroke();ctx.fillStyle="#55554f";ctx.textAlign="right";ctx.fillText(new Intl.NumberFormat("pt-BR",{maximumFractionDigits:2,notation:ymax>=10000?"compact":"standard"}).format(v),left-10,y(v));}
 if(state.key==="congestion"){ctx.strokeStyle="#66665f";ctx.setLineDash([3,4]);ctx.beginPath();ctx.moveTo(left,y(1));ctx.lineTo(w-right,y(1));ctx.stroke();ctx.setLineDash([]);ctx.fillStyle="#41413d";ctx.textAlign="left";ctx.fillText("limite 1",left+8,y(1)-10);}
 [0,Math.round(state.horizon/2),state.horizon].forEach(p=>{ctx.fillStyle="#55554f";ctx.textAlign="center";ctx.fillText("p"+p,x(p),h-24);});
 for(const [series,color,dash] of activeConditions().map(c=>[aggregate(c),c==="A"?"#0072b2":"#d55e00",c==="A"?[]:[7,5]])){
  if(state.n>1){ctx.fillStyle=color;ctx.globalAlpha=.13;ctx.beginPath();series.forEach((v,i)=>{if(!i)ctx.moveTo(x(v.period),y(v.p90));else ctx.lineTo(x(v.period),y(v.p90));});[...series].reverse().forEach(v=>ctx.lineTo(x(v.period),y(v.p10)));ctx.closePath();ctx.fill();ctx.globalAlpha=1;}
  ctx.strokeStyle=color;ctx.lineWidth=2.5;ctx.setLineDash(dash);ctx.beginPath();series.forEach((v,i)=>{if(!i)ctx.moveTo(x(v.period),y(v.mean));else ctx.lineTo(x(v.period),y(v.mean));});ctx.stroke();ctx.setLineDash([]);const last=series.at(-1);ctx.fillStyle=color;ctx.beginPath();ctx.arc(x(last.period),y(last.mean),3,0,Math.PI*2);ctx.fill();
 }
 ctx.strokeStyle="#141414";ctx.lineWidth=1;ctx.setLineDash([2,3]);ctx.beginPath();ctx.moveTo(x(state.period),top);ctx.lineTo(x(state.period),h-bottom);ctx.stroke();ctx.setLineDash([]);
 canvas.dataset.period=String(state.period);canvas.dataset.band=state.n>1?"p10-p90":"none";canvas.setAttribute("aria-label",$("figure-scope").textContent+" "+$("metric-unit").textContent+" "+$("chart-caption").textContent+" "+$("uncertainty-reading").textContent+" Valores por semente na tabela abaixo.");
}
const count=(n,one,many)=>`${fmt(n,0)} ${n===1?one:many}`;
function eventsText(item){const exits=Object.values(item.exit_count_by_type).reduce((a,b)=>a+b,0),ties=item.ties_formed_by_type;return [count(item.entry_count,"entrada","entradas"),count(exits,"saída","saídas"),count(ties.partnership||0,"nova parceria","novas parcerias"),count(ties.investment||0,"investimento","investimentos"),count(ties.hiring||0,"contratação","contratações"),count(item.innovation_count,"inovação","inovações")].join("; ")+".";}
function updateNetwork(){
 const c=$("network-condition").value,item=scenario(c),map=item.maps[String(state.period)],select=$("network-node"),current=select.value;
 select.replaceChildren();map.nodes.forEach(node=>{const option=document.createElement("option");option.value=String(node.id);option.textContent=`${node.label} · ${typeNames[node.type]}`;select.append(option);});if(map.nodes.some(n=>String(n.id)===current))select.value=current;
 $("network-scope").textContent=`Simulação · ${state.mode==="compare"?c+": ":""}${item.name} · semente ${item.runs[0].seed} · período ${state.period} · execução individual; gráficos abaixo: média de ${state.n} sementes.`;
 const run=item.runs[0],list=$("period-events");list.replaceChildren();
 const messages=state.period===0?["Estado inicial, antes de entradas e custos do primeiro período."]:[eventsText(run.events[state.period-1]),`Saídas por tipo: ${Object.entries(run.events[state.period-1].exit_count_by_type).map(([k,v])=>({failure:"falha",acquisition:"aquisição",voluntary:"voluntária",migration:"migração"}[k]+" "+v)).join("; ")}.`,`Congestionamento: ${fmt(recordAt(run,state.period).congestion,2)}; inovações acumuladas: ${fmt(recordAt(run,state.period).innovation_cumulative,0)}.`];
 if(item.config.shock_period===state.period&&state.period>0)messages.unshift("Período configurado para o choque. As saídas registradas abaixo mostram o que ocorreu; o agendamento não garante uma saída.");
 if(state.period>0){const key=e=>`${Math.min(e.source,e.target)}:${Math.max(e.source,e.target)}:${e.type}`,before=new Set(item.maps[String(state.period-1)].edges.map(key)),after=new Set(map.edges.map(key));messages.push(`Entre os quadros: ${[...after].filter(k=>!before.has(k)).length} relações apareceram e ${[...before].filter(k=>!after.has(k)).length} deixaram de existir. Saídas também podem remover relações.`);}
 messages.forEach(text=>{const li=document.createElement("li");li.textContent=text;list.append(li);});
 $("event-log").replaceChildren();run.events.slice(Math.max(0,state.period-5),state.period).forEach(event=>{const li=document.createElement("li");li.textContent=`p${event.period}: ${eventsText(event)}`;$("event-log").append(li);});
 drawNetwork();
}
function nodeShape(ctx,x,y,r,type){ctx.beginPath();if(type==="startup")ctx.arc(x,y,r,0,Math.PI*2);else if(type==="worker"){ctx.moveTo(x,y-r);ctx.lineTo(x+r,y+r);ctx.lineTo(x-r,y+r);ctx.closePath();}else if(type==="university"){ctx.moveTo(x,y-r);ctx.lineTo(x+r,y);ctx.lineTo(x,y+r);ctx.lineTo(x-r,y);ctx.closePath();}else ctx.rect(x-r,y-r,r*2,r*2);}
function drawNetwork(){
 const c=$("network-condition").value,item=scenario(c),map=item.maps[String(state.period)],selected=Number($("network-node").value),node=map.nodes.find(n=>n.id===selected),{ctx,w,h}=canvasContext($("network"));if(!w)return;
 const onlyStartups=Object.values(item.maps).every(frame=>frame.nodes.every(n=>n.type==="startup"));
 if(!item.bounds){const points=Object.values(item.maps).flatMap(frame=>Object.values(frame.positions));item.bounds=onlyStartups?{minx:Math.min(...points.map(p=>p[0])),maxx:Math.max(...points.map(p=>p[0])),miny:Math.min(...points.map(p=>p[1])),maxy:Math.max(...points.map(p=>p[1]))}:{minx:0,maxx:1,miny:0,maxy:1};}
 const bounds=item.bounds,pos=id=>{const p=map.positions[String(id)];return [28+(p[0]-bounds.minx)/(bounds.maxx-bounds.minx||1)*(w-56),h-28-(p[1]-bounds.miny)/(bounds.maxy-bounds.miny||1)*(h-56)];};
 const ids=new Set(map.nodes.map(n=>n.id)),edges=map.edges.filter(e=>ids.has(e.source)&&ids.has(e.target)),neighbors=new Set([selected]);edges.forEach(e=>{if(e.source===selected)neighbors.add(e.target);if(e.target===selected)neighbors.add(e.source);});
 edges.forEach(e=>{const a=pos(e.source),b=pos(e.target),focused=e.source===selected||e.target===selected;ctx.strokeStyle=edgeColors[e.type]||"#66665f";ctx.globalAlpha=focused?.95:.35;ctx.lineWidth=focused?2:1;ctx.setLineDash(edgeDashes[e.type]||[]);ctx.beginPath();ctx.moveTo(...a);ctx.lineTo(...b);ctx.stroke();});ctx.setLineDash([]);ctx.globalAlpha=1;
 state.hits=[];
 map.nodes.forEach(n=>{const p=pos(n.id),r=n.id===selected?8:n.type==="startup"?4.5:7;nodeShape(ctx,p[0],p[1],r,n.type);ctx.fillStyle=nodeColors[n.type];ctx.fill();ctx.strokeStyle="#141414";ctx.lineWidth=neighbors.has(n.id)?2:1;ctx.stroke();if(n.type==="worker"&&n.employed_by!==null){ctx.beginPath();ctx.arc(p[0],p[1],2,0,Math.PI*2);ctx.fillStyle="#141414";ctx.fill();}if(n.id===selected||["anchor","university","investor"].includes(n.type)){ctx.font="12px Geist,Arial";ctx.textAlign=p[0]>w-65?"right":"left";ctx.lineWidth=4;ctx.strokeStyle="#f1f1ee";const tx=p[0]+(p[0]>w-65?-12:12);ctx.strokeText(n.label,tx,p[1]-10);ctx.fillStyle="#141414";ctx.fillText(n.label,tx,p[1]-10);}state.hits.push({id:n.id,x:p[0],y:p[1]});});
 const ties=edges.filter(e=>e.source===selected||e.target===selected);const facts=node?Object.entries(node).filter(([k])=>!["id","label","type"].includes(k)).map(([k,v])=>`${({sector:"setor",capital:"capital",knowledge:"conhecimento",reputation:"reputação",team_size:"equipe",age:"idade",participation:"participação",active:"ativo",skill:"habilidade",education:"escolaridade",wage:"salário",employed_by:"empregador",knowledge_stock:"estoque de conhecimento"}[k]||k)}: ${display(v)}`).join(" · "):"";
 $("node-reading").textContent=node?`${node.label} (${typeNames[node.type]}) · ${count(ties.length,"relação","relações")}. ${facts}.`:"Nenhum agente neste período.";
 $("network").dataset.period=String(state.period);$("network").setAttribute("aria-label",$("network-scope").textContent+` ${map.nodes.length} agentes e ${edges.length} relações. `+$("node-reading").textContent);
}
function download(name,type,content){const url=URL.createObjectURL(new Blob([content],{type})),link=document.createElement("a");link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$("status").textContent="Arquivo preparado: "+name;}
/* SETUP_HELPERS */
document.querySelectorAll("[data-step]").forEach(b=>b.addEventListener("click",()=>go(Number(b.dataset.step))));document.querySelectorAll("[data-next]").forEach(b=>b.addEventListener("click",()=>go(Number(b.dataset.next))));
for(const c of ["A","B"]){
 $("scenario-"+c.toLowerCase()).addEventListener("change",event=>{stop();state.selected[c]=event.target.value;state.conditions[c]=event.target.value;state.period=0;resetDraft(c);renderScenarios();});
 $("editor-details-"+c.toLowerCase()).addEventListener("toggle",()=>{if($("editor-details-"+c.toLowerCase()).open&&!$("params-editor-"+c.toLowerCase()).children.length)renderEditor(c);});
 $("reset-params-"+c.toLowerCase()).addEventListener("click",()=>resetDraft(c));
}
for(const input of document.querySelectorAll('[name="investigation-mode"]'))input.addEventListener("change",()=>{stop();state.mode=input.value;state.prepared=false;renderPreparation();update();});
$("replicates").addEventListener("change",event=>{stop();state.n=Number(event.target.value);state.prepared=false;renderPreparation();});
$("horizon").addEventListener("change",event=>{stop();state.horizon=Number(event.target.value);state.prepared=false;});
$("seed-base").addEventListener("input",event=>{state.base=Number(event.target.value);state.prepared=false;});
$("run-config").addEventListener("click",executeConfiguration);$("use-example").addEventListener("click",useExample);
$("cancel-run").addEventListener("click",cancelRun);
$("metric").addEventListener("change",event=>{state.key=event.target.value;update();});
$("timeline").addEventListener("input",event=>{stop();seek(Number(event.target.value));});
$("play-pause").addEventListener("click",()=>{if(state.timer!==null){stop();return;}if(state.period===state.horizon)seek(0);$("play-pause").textContent="Pausar evolução";$("play-pause").setAttribute("aria-pressed","true");state.timer=setInterval(()=>seek(state.period+1),600);});
$("step-one").addEventListener("click",()=>{stop();seek(state.period+1);});$("step-ten").addEventListener("click",()=>{stop();seek(state.period+10);});$("rewind").addEventListener("click",()=>{stop();seek(0);});$("go-final").addEventListener("click",()=>{stop();seek(state.horizon);});
$("network-condition").addEventListener("change",updateNetwork);$("network-node").addEventListener("change",drawNetwork);
$("network").addEventListener("click",event=>{const rect=$("network").getBoundingClientRect(),x=event.clientX-rect.left,y=event.clientY-rect.top,hit=[...state.hits].reverse().find(n=>Math.hypot(n.x-x,n.y-y)<14);if(hit){$("network-node").value=String(hit.id);drawNetwork();}});
$("export-json").addEventListener("click",()=>download("investigacao.json","application/json",JSON.stringify(exportPayload(),null,2)));
$("export-csv").addEventListener("click",()=>download("investigacao-trajetorias.csv","text/csv;charset=utf-8",exportCsv()));
window.addEventListener("resize",()=>{if(state.step===2){drawTrajectory();drawNetwork();}});document.addEventListener("visibilitychange",()=>{if(document.hidden)stop();});
for(const c of ["A","B"])state.drafts[c]=baseParams(c);
for(const id of data.research.order){const item=scenarios.get(id),li=document.createElement("li"),title=document.createElement("h3");title.textContent=item.name;li.append(title);const brief=briefs[item.id];paragraph(li,brief[0]);paragraph(li,brief[1],"small");paragraph(li,item.research.group+" · "+item.research.hypothesis_id,"small");$("scenario-catalog").append(li);}
$("research-selection").textContent=data.research.selection;$("research-scope").textContent=data.research.scope;$("research-limitations").textContent=data.research.limitations;Object.keys(data.research.sources).forEach(key=>renderSource($("scenario-bibliography"),key));
renderScenarios();update();document.querySelectorAll("button").forEach(button=>button.disabled=false);$("run-config").disabled=true;probeEngine();$("main").setAttribute("aria-busy","false");document.documentElement.dataset.ready="true";
})();
