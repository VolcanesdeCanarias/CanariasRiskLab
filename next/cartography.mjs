export class BaseMaps {
  constructor(map, notice) {this.map=map;this.notice=notice;this.active=[];this.sequence=0;}
  set(config) {
    const seq=++this.sequence;
    for(const layer of this.active)this.map.removeLayer(layer);
    this.active=[];this.config=config;let failures=0,loaded=0;
    const add=(url,layers,transparent=false)=>{
      const options={maxZoom:config.max_zoom,attribution:config.attribution,keepBuffer:1,updateWhenIdle:true};
      const layer=layers?L.tileLayer.wms(url,{...options,layers,format:transparent?'image/png':'image/jpeg',transparent,version:'1.1.1'}):L.tileLayer(url,options);
      layer.on('tileload',()=>{if(seq!==this.sequence)return;loaded++;this.notice(failures?`${config.name} · carga parcial (${failures} errores de imagen). Observaciones conservadas.`:`${config.name} · servicio en línea`,failures>0);});
      layer.on('tileerror',()=>{if(seq!==this.sequence)return;failures++;this.notice(loaded?`${config.name} · carga cartográfica parcial. Observaciones conservadas.`:`${config.name}: imágenes no disponibles. Se conservan observaciones y contornos.`,true);});
      layer.addTo(this.map);this.active.push(layer);
    };
    this.notice(`${config.name} · solicitando cartografía…`,false);
    add(config.url,config.kind==='street'?null:config.layers);
    if(config.kind==='hybrid')add(config.overlay_url,config.overlay_layers,true);
  }
}
