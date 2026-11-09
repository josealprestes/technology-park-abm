/* Included inside the workbench closure; no runtime script request. */
const briefs=Object.fromEntries(Object.entries(data.research.scenarios).map(([id,item])=>[id,[item.question,item.watch,item.caveat]]));
const groupNames={Population:"População",Environment:"Ambiente e recursos",Entry:"Entradas",Partnerships:"Parcerias",Knowledge:"Conhecimento",Finance:"Finanças e trabalho",Congestion:"Congestionamento","Exits & Shocks":"Saídas e choques","Anchors & Reputation":"Âncoras e reputação",Empirical:"Atributos e dados",Policy:"Políticas"};
const editableSpecs=(data.parameters||[]).filter(spec=>!["seed","microdata_path"].includes(spec.name));
const baseParams=c=>{const params=structuredClone(configFlat(sourceScenario(c).config));delete params.seed;delete params.microdata_path;return params;};
const changedKeys=(a,b)=>Object.keys(a).filter(k=>k!=="seed"&&JSON.stringify(a[k])!==JSON.stringify(b[k]));
const draftChanges=c=>changedKeys(baseParams(c),state.drafts[c]);
function paragraph(parent,text,className=""){const p=document.createElement("p");p.textContent=text;p.className=className;parent.append(p);return p;}
function renderSource(parent,key){
 const source=data.research.sources[key],details=document.createElement("details"),summary=document.createElement("summary");
 details.className="research-source";summary.textContent=source.citation+" · "+source.kind;details.append(summary);
 paragraph(details,source.title);paragraph(details,source.summary);paragraph(details,"Aplicação e alcance: "+source.application);
 paragraph(details,"Consulta: "+source.access,"small");
 const link=document.createElement("a");link.href=source.url;link.target="_blank";link.rel="noopener noreferrer";link.textContent="Consultar a obra: "+source.citation+" (abre nova aba)";details.append(link);parent.append(details);
}
function dossierSection(parent,title,text){const heading=document.createElement("h4");heading.textContent=title;parent.append(heading);paragraph(parent,text);}
function renderDossier(parent,item){
 const r=item.research,details=document.createElement("details"),summary=document.createElement("summary");details.className="actor-note research-dossier";summary.textContent="Base conceitual e hipótese";details.append(summary);
 paragraph(details,r.hypothesis_id+" · revisão de "+new Date(data.research.reviewed_on+"T12:00:00").toLocaleDateString("pt-BR"),"read-only");
 dossierSection(details,"Por que este roteiro está na seleção",r.rationale);
 dossierSection(details,"O que este roteiro permite testar",r.hypothesis);
 dossierSection(details,"Como observar o comportamento",r.observation);
 dossierSection(details,"Comparação sugerida",r.contrast.label+". "+r.contrast.description);
 const button=document.createElement("button");button.type="button";button.dataset.compareRecipe=item.id;button.textContent="Preparar comparação deste roteiro";button.addEventListener("click",()=>prepareResearchComparison(item.id));details.append(button);
 paragraph(details,"Substitui A e B pelo desenho sugerido para você revisar. Não executa a simulação.","small");
 dossierSection(details,"Quando a expectativa não se sustenta",r.counterevidence);
 dossierSection(details,"Limites da representação",r.caveat);
 dossierSection(details,"Relação com IA006J",r.course);
 const heading=document.createElement("h4");heading.textContent="Obras de referência e aplicações";details.append(heading);r.sources.forEach(key=>renderSource(details,key));
 paragraph(details,"A descrição acima se refere ao roteiro original. Edições podem mudar o alcance da comparação. Referência teórica, aplicação publicada e validação deste modelo são evidências distintas.","small");parent.append(details);
}
function prepareResearchComparison(id){
 stop();const item=scenarios.get(id),r=item.research;state.mode="compare";state.prepared=false;state.period=0;
 for(const c of ["A","B"]){state.selected[c]=id;state.conditions[c]=id;state.drafts[c]={...baseParams(c),...structuredClone(r.contrast[c.toLowerCase()])};renderEditor(c);}
 document.querySelectorAll('[name="investigation-mode"]').forEach(input=>input.checked=input.value==="compare");
 renderScenarios();go(1);$("run-status").textContent="Comparação sugerida preparada. Confira as diferenças e execute quando desejar.";$("review-heading").focus();$("review-heading").scrollIntoView({block:"start"});
}
function renderPreparation(){
 const comparing=state.mode==="compare";
 document.querySelectorAll("[data-compare-only]").forEach(el=>el.hidden=!comparing);
 document.querySelectorAll(".scenario-selectors").forEach(grid=>grid.style.gridTemplateColumns=comparing?"":"minmax(0,1fr)");
 $("scenario-label-a").textContent=comparing?"A · Primeiro roteiro":"Roteiro de partida";
 $("config-head-a").textContent=comparing?"A":"Cenário";
 $("editor-title-a").textContent=comparing?"Alterar parâmetros de A":"Alterar parâmetros do cenário";
 $("run-config").textContent=comparing?"Executar comparação":"Executar meu cenário";
 $("network-condition").value=comparing?$("network-condition").value:"A";
 $("network-condition").parentElement.hidden=!comparing;
 document.querySelectorAll(".mode-options label").forEach(label=>label.classList.toggle("selected",label.querySelector("input").checked));
 for(const c of ["A","B"]){
  const amount=draftChanges(c).length;
  $("changes-"+c.toLowerCase()).textContent=amount?`${amount} parâmetro${amount===1?"":"s"} alterado${amount===1?"":"s"} em relação ao roteiro. A nova configuração será calculada ao executar.`:"Valores originais do roteiro. Você pode usá-los ou abrir os campos para personalizar.";
 }
 const a=state.drafts.A,b=state.drafts.B,changed=changedKeys(a,b);
 $("parameter-differences").replaceChildren();$("all-parameters").replaceChildren();
 for(const key of Object.keys(a)){
  const label=data.parameter_labels[key]||key;
  appendRow($("all-parameters"),comparing?[label,display(a[key]),display(b[key])]:[label,display(a[key])]);
  if(changed.includes(key))appendRow($("parameter-differences"),[label,display(a[key]),display(b[key])]);
 }
 if(!changed.length)appendRow($("parameter-differences"),["Nenhum parâmetro alterado","mesma configuração","mesma configuração"]);
 const differentThresholds=comparing&&a.productive_tie_strength_threshold!==b.productive_tie_strength_threshold;
 $("comparison-warning").textContent=!comparing?"Você observará um cenário. As repetições mostram trajetórias possíveis desta configuração; nenhuma referência B é necessária.":differentThresholds?"Os limiares de parceria produtiva diferem: isso muda a definição da contagem, não a dinâmica da rede. O delta de parcerias produtivas ficará indisponível. Use o mesmo limiar para comparar esse indicador.":changed.length>1?`${changed.length} parâmetros diferem entre A e B. A comparação descreve configurações; não isola um único mecanismo.`:changed.length===1?"Um parâmetro difere entre A e B. As duas configurações usarão as mesmas sementes e horizonte.":"As configurações são iguais. Com as mesmas sementes, suas trajetórias devem coincidir.";
}
function renderScenarioCards(){
 for(const c of ["A","B"]){
  const item=sourceScenario(c),select=$("scenario-"+c.toLowerCase()),box=$("scenario-description-"+c.toLowerCase());
  select.replaceChildren();const groups=new Map();
  for(const id of data.research.order){const s=scenarios.get(id),group=s.research.group;if(!groups.has(group)){const node=document.createElement("optgroup");node.label=group;groups.set(group,node);select.append(node);}const option=document.createElement("option");option.value=s.id;option.textContent=s.name;groups.get(group).append(option);}select.value=state.selected[c];
  box.replaceChildren();paragraph(box,"Sobre o roteiro · informação para leitura","read-only");
  const info=briefs[item.id]||[item.name,item.description,"Resultados exploratórios."];
  const heading=document.createElement("h3");heading.textContent=info[0];box.append(heading);
  paragraph(box,item.research.group+" · "+item.research.hypothesis_id,"small");paragraph(box,info[1]);paragraph(box,info[2],"small");
  const mix=[["n_startups","startups"],["n_anchor_firms","âncoras"],["n_universities","universidades"],["n_investors","investidores"],["n_workers","trabalhadores"]].map(([k,label])=>`${item.config[k]} ${label}`).join(" · ");
  paragraph(box,"Configuração original: "+mix+".","small");
  renderDossier(box,item);
 }
 renderPreparation();
}
function renderEditor(c){
 const parent=$("params-editor-"+c.toLowerCase());parent.replaceChildren();
 const basic=document.createElement("div"),advanced=document.createElement("details"),summary=document.createElement("summary");
 summary.textContent="Parâmetros avançados";advanced.append(summary);parent.append(basic,advanced);
 for(const advancedOnly of [false,true]){
  const specs=editableSpecs.filter(spec=>!spec.simple===advancedOnly),groups=[...new Set(specs.map(spec=>spec.group))];
  for(const group of groups){
   const fieldset=document.createElement("fieldset"),legend=document.createElement("legend");legend.textContent=groupNames[group]||group;fieldset.append(legend);(advancedOnly?advanced:basic).append(fieldset);
   for(const spec of specs.filter(s=>s.group===group)){
    const field=document.createElement("div");field.className="field";fieldset.append(field);
    const id=`param-${c.toLowerCase()}-${spec.name}`,label=document.createElement("label");label.htmlFor=id;label.textContent=spec.label;field.append(label);
    let input;
    if(spec.choices||spec.kind==="bool"){
     input=document.createElement("select");
     const options=spec.kind==="bool"?[true,false]:(spec.kind==="optional_choice"?[null,...spec.choices]:spec.choices.filter(v=>v!=="microdata"));
     options.forEach(value=>{const option=document.createElement("option");option.value=value===null?"":String(value);option.textContent=value===null?"Sem choque":display(value);input.append(option);});
     input.value=state.drafts[c][spec.name]===null?"":String(state.drafts[c][spec.name]);
    }else{
     input=document.createElement("input");input.type=spec.kind==="sectors"||spec.kind==="text"?"text":"number";
     if(input.type==="number"){
      input.step=["int","optional_int"].includes(spec.kind)?"1":"any";
      if(spec.minimum!==null)input.min=String(spec.minimum);
      if(spec.kind==="probability")input.max="1";
      if(spec.name.startsWith("n_"))input.max="100";
      if(spec.name==="entry_potential_per_period")input.max="5";
     }
     const value=state.drafts[c][spec.name];input.value=value===null?"":Array.isArray(value)?value.join(", "):String(value);
     input.required=!["optional_int","text"].includes(spec.kind);
    }
    input.id=id;input.dataset.parameter=spec.name;input.setAttribute("aria-describedby",id+"-help");field.append(input);
    const help=document.createElement("small");help.id=id+"-help";help.className="small";help.textContent=spec.description||"Valor editável da configuração.";field.append(help);
    input.addEventListener("input",()=>{
     let value=input.value;
     if(spec.kind==="bool")value=value==="true";
     else if(spec.kind==="sectors")value=value.split(",").map(v=>v.trim()).filter(Boolean);
     else if(["optional_choice","optional_int"].includes(spec.kind)&&value==="")value=null;
     else if(input.type==="number")value=value===""?NaN:Number(value);
     state.drafts[c][spec.name]=value;state.prepared=false;renderPreparation();
    });
   }
  }
 }
}
function resetDraft(c){state.drafts[c]=baseParams(c);state.prepared=false;renderEditor(c);renderPreparation();}
function validPreparation(){
 for(const c of activeConditions())for(const input of $("params-editor-"+c.toLowerCase()).querySelectorAll("input,select")){
  if(!input.checkValidity()){
   for(let parent=input.parentElement;parent;parent=parent.parentElement)if(parent.tagName==="DETAILS")parent.open=true;
   $("run-status").textContent="Revise o valor de "+(data.parameter_labels[input.dataset.parameter]||"este campo")+" antes de executar.";input.focus();input.reportValidity();return false;
  }
 }
 for(const id of ["seed-base","replicates","horizon"])if(!$(id).checkValidity()){$(id).reportValidity();return false;}
 return true;
}
function setBusy(busy){
 state.busy=busy;document.querySelectorAll('[data-page="1"] input,[data-page="1"] select,[data-page="1"] button,.steps button').forEach(control=>control.disabled=busy);
 $("cancel-run").hidden=!busy;$("cancel-run").disabled=false;$("run-progress").hidden=!busy;$("run-config").setAttribute("aria-busy",String(busy));
 if(!busy)$("run-config").disabled=!state.engineAvailable;
}
async function request(path,body){
 let response;
 try{response=await fetch(path,body?{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}:{});}
 catch(_){throw new Error("Não foi possível acessar o motor local. Verifique se o servidor de investigação está em execução e tente novamente. Seus parâmetros foram mantidos.");}
 let result;try{result=await response.json();}catch(_){throw new Error("O motor local não respondeu. Abra a prévia pelo servidor de investigação.");}
 if(!response.ok)throw new Error(result.error||"Não foi possível executar. Reveja a configuração.");return result;
}
async function executeConfiguration(){
 if(state.busy||!validPreparation())return;
 stop();state.prepared=false;state.cancelRequested=false;setBusy(true);$("run-status").textContent="Calculando sua configuração no motor local…";$("run-progress").value=0;
 const conditions={};for(const c of activeConditions())conditions[c]={name:sourceScenario(c).name+(draftChanges(c).length?" · personalizada":""),params:structuredClone(state.drafts[c])};
 try{
  const started=await request("/api/investigation/run",{mode:state.mode,n_seeds:state.n,base_seed:state.base,periods:state.horizon,conditions});state.job=started.job_id;
  if(state.cancelRequested)await request("/api/investigation/cancel",{job_id:state.job});
  while(true){
   const job=await request("/api/investigation/jobs/"+state.job);$("run-progress").value=100*job.done/Math.max(1,job.total);$("run-status").textContent=`Calculando ${job.done} de ${job.total} execuções…`;
    if(job.state==="done"){
     if(state.cancelRequested){$("run-status").textContent="Cancelamento solicitado. Nenhum resultado foi aplicado.";break;}
     for(const [c,item] of Object.entries(job.result.conditions)){item.base_scenario_id=state.selected[c];item.research=sourceScenario(c).research;item.research_modified=draftChanges(c).length>0;scenarios.set(item.id,item);state.conditions[c]=item.id;}
     for(const id of scenarios.keys())if(id.startsWith("live-")&&!Object.values(state.conditions).includes(id))scenarios.delete(id);
    state.seeds=job.result.seeds;state.period=0;state.prepared=true;setBusy(false);state.job=null;$("run-status").textContent="Configuração calculada. Pronta para explorar.";go(2);return;
   }
   if(job.state==="cancelled"){$("run-status").textContent="Execução cancelada. Seus parâmetros foram mantidos.";break;}
   if(job.state==="error")throw new Error(job.error||"A execução não foi concluída. Reveja os parâmetros.");
   await new Promise(resolve=>setTimeout(resolve,350));
  }
 }catch(error){$("run-status").textContent=error.message||"Não foi possível concluir a execução.";}
 finally{state.job=null;setBusy(false);}
}
function useExample(){
 if(activeConditions().some(c=>draftChanges(c).length)||state.base!==1){$("run-status").textContent="Os exemplos usam os valores originais e semente inicial 1. Para suas alterações, use Executar no motor local.";return;}
 for(const c of activeConditions())state.conditions[c]=state.selected[c];state.seeds=data.seeds.slice(0,state.n);state.period=0;state.prepared=true;go(2);
}
async function probeEngine(){
 try{if(!location.protocol.startsWith("http"))throw new Error();const result=await request("/api/investigation/health");state.engineAvailable=result.available===true;}catch(_){state.engineAvailable=false;}
 $("engine-availability").textContent=state.engineAvailable?"Motor local disponível · até 8 sementes, 80 períodos e 150 agentes iniciais. Seus parâmetros serão calculados ao executar.":"Motor local indisponível nesta abertura. Os exemplos registrados continuam disponíveis; personalizações precisam do servidor de investigação.";
 $("run-config").disabled=!state.engineAvailable;
}
async function cancelRun(){
 state.cancelRequested=true;$("run-status").textContent="Cancelando execução…";
 try{if(state.job)await request("/api/investigation/cancel",{job_id:state.job});}catch(error){$("run-status").textContent=error.message;}
}
