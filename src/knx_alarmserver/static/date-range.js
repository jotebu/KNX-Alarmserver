'use strict';
// A single, local calendar range picker; no external services or dependencies.
window.AlarmDateRange=class AlarmDateRange {
  constructor(onApply){
    this.onApply=onApply;this.from='';this.until='';this.draftFrom='';this.draftUntil='';
    this.wrap=document.getElementById('date-range-wrap');this.trigger=document.getElementById('date-range-toggle');this.popup=document.getElementById('date-range-popup');
    this.trigger.onclick=()=>this.popup.hidden?this.open():this.close();
    document.getElementById('date-range-prev').onclick=()=>this.moveMonth(-1);
    document.getElementById('date-range-next').onclick=()=>this.moveMonth(1);
    document.getElementById('date-range-cancel').onclick=()=>this.close();
    document.getElementById('date-range-clear').onclick=()=>{this.from=this.until='';this.updateLabel();this.onApply('','');this.close();};
    document.getElementById('date-range-apply').onclick=()=>{if(!this.draftFrom||!this.draftUntil)return;this.from=this.draftFrom;this.until=this.draftUntil;this.updateLabel();this.onApply(this.from,this.until);this.close();};
    document.addEventListener('click',event=>{if(!this.popup.hidden&&!event.composedPath().includes(this.wrap))this.close(false);});
    document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!this.popup.hidden){event.preventDefault();this.close();}});
  }
  key(day){return `${day.getFullYear()}-${String(day.getMonth()+1).padStart(2,'0')}-${String(day.getDate()).padStart(2,'0')}`;}
  day(key){return new Date(key+'T12:00:00');}
  display(key){return this.day(key).toLocaleDateString('de-DE');}
  updateLabel(){const label=this.from?`${this.display(this.from)} – ${this.display(this.until)}`:'Zeitraum auswählen';document.getElementById('date-range-label').textContent=label;this.trigger.title=this.from?'Gekommen im gewählten Zeitraum, einschließlich Endtag':'Meldungen nach Gekommen eingrenzen';}
  open(){
    this.draftFrom=this.from;this.draftUntil=this.until;const start=this.from?this.day(this.from):new Date();
    this.month=new Date(start.getFullYear(),start.getMonth(),1,12);this.focusDate=this.from||this.key(start);
    this.popup.hidden=false;this.trigger.setAttribute('aria-expanded','true');this.render();this.focusDay();
  }
  close(returnFocus=true){this.popup.hidden=true;this.trigger.setAttribute('aria-expanded','false');if(returnFocus)this.trigger.focus();}
  moveMonth(offset){this.month=new Date(this.month.getFullYear(),this.month.getMonth()+offset,1,12);this.focusDate=this.key(this.month);this.render();}
  focusDay(){const node=this.popup.querySelector(`[data-date="${this.focusDate}"]`);if(node)node.focus();}
  choose(key){
    if(!this.draftFrom||this.draftUntil){this.draftFrom=key;this.draftUntil='';}
    else if(key<this.draftFrom){this.draftUntil=this.draftFrom;this.draftFrom=key;}
    else this.draftUntil=key;
    this.focusDate=key;this.render();this.focusDay();
  }
  navigate(event,key){
    const target=this.day(key),offset={ArrowLeft:-1,ArrowRight:1,ArrowUp:-7,ArrowDown:7}[event.key];
    if(offset!==undefined)target.setDate(target.getDate()+offset);
    else if(event.key==='Home')target.setDate(target.getDate()-(target.getDay()+6)%7);
    else if(event.key==='End')target.setDate(target.getDate()+6-(target.getDay()+6)%7);
    else if(event.key==='PageUp'||event.key==='PageDown'){const original=target.getDate();target.setDate(1);target.setMonth(target.getMonth()+(event.key==='PageUp'?-1:1));target.setDate(Math.min(original,new Date(target.getFullYear(),target.getMonth()+1,0).getDate()));}
    else return;
    event.preventDefault();const end=new Date(this.month.getFullYear(),this.month.getMonth()+2,1,12);
    if(target<this.month||target>=end)this.month=new Date(target.getFullYear(),target.getMonth(),1,12);
    this.focusDate=this.key(target);this.render();this.focusDay();
  }
  render(){
    const months=document.getElementById('date-range-months');months.replaceChildren();const today=this.key(new Date());
    for(let offset=0;offset<2;offset++){
      const month=new Date(this.month.getFullYear(),this.month.getMonth()+offset,1,12),section=document.createElement('section'),title=document.createElement('h4');
      title.id='date-range-month-'+offset;title.textContent=month.toLocaleDateString('de-DE',{month:'long',year:'numeric'});section.setAttribute('aria-labelledby',title.id);section.append(title);
      const grid=document.createElement('div');grid.className='range-calendar';
      for(const weekday of ['Mo','Di','Mi','Do','Fr','Sa','So']){const label=document.createElement('span');label.className='range-weekday';label.textContent=weekday;label.setAttribute('aria-hidden','true');grid.append(label);}
      for(let i=0;i<(month.getDay()+6)%7;i++)grid.append(document.createElement('span'));
      const days=new Date(month.getFullYear(),month.getMonth()+1,0).getDate();
      for(let number=1;number<=days;number++){
        const day=new Date(month.getFullYear(),month.getMonth(),number,12),key=this.key(day),button=document.createElement('button');
        button.type='button';button.dataset.date=key;button.textContent=number;button.tabIndex=key===this.focusDate?0:-1;
        const endpoint=key===this.draftFrom||key===this.draftUntil,inRange=Boolean(this.draftFrom&&this.draftUntil&&key>=this.draftFrom&&key<=this.draftUntil);
        button.className='range-day'+(inRange?' range-between':'')+(endpoint?' range-endpoint':'');button.setAttribute('aria-pressed',String(endpoint||inRange));
        button.setAttribute('aria-label',day.toLocaleDateString('de-DE',{weekday:'long',day:'numeric',month:'long',year:'numeric'})+(key===this.draftFrom?', Beginn':'')+(key===this.draftUntil?', Ende':''));
        if(key===today)button.setAttribute('aria-current','date');button.onclick=()=>this.choose(key);button.onkeydown=event=>this.navigate(event,key);grid.append(button);
      }
      section.append(grid);months.append(section);
    }
    document.getElementById('date-range-selection').textContent=this.draftUntil?`${this.display(this.draftFrom)} – ${this.display(this.draftUntil)}`:this.draftFrom?`${this.display(this.draftFrom)} – Enddatum wählen`:'Beginn und Ende im Kalender auswählen';
    document.getElementById('date-range-apply').disabled=!this.draftFrom||!this.draftUntil;
  }
};
