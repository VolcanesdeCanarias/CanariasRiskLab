import {CANARIAS, validBounds, cameraPose, samePose} from './view-state.mjs';
// Rendering only: the backend owns observations, filters and numerical results.
export class EarthView {
  constructor(element, select) {
    const C=globalThis.Cesium;
    this.C=C;this.element=document.getElementById(element);this.select=select;
    this.viewer=new C.Viewer(element,{terrainProvider:new C.EllipsoidTerrainProvider(),baseLayer:false,baseLayerPicker:false,
      animation:false,timeline:false,geocoder:false,homeButton:false,sceneModePicker:false,navigationHelpButton:false,
      fullscreenButton:false,selectionIndicator:false,infoBox:false,skyBox:false,skyAtmosphere:false,
      contextOptions:{webgl:{preserveDrawingBuffer:true}},requestRenderMode:true,maximumRenderTimeChange:Infinity});
    const v=this.viewer;
    v.scene.globe.baseColor=C.Color.fromCssColorString('#d5e5df');
    v.scene.backgroundColor=C.Color.fromCssColorString('#eef4f0');
    v.scene.globe.translucency.enabled=true;v.scene.globe.translucency.frontFaceAlpha=.82;
    v.scene.globe.translucency.backFaceAlpha=.2;v.scene.globe.showGroundAtmosphere=false;
    v.scene.screenSpaceCameraController.minimumZoomDistance=250;
    this.points=v.scene.primitives.add(new C.PointPrimitiveCollection());
    this.handler=new C.ScreenSpaceEventHandler(v.scene.canvas);
    this.handler.setInputAction(click=>{const hit=v.scene.pick(click.position);if(hit?.id?.risklabEvent)this.select(hit.id.risklabEvent);},C.ScreenSpaceEventType.LEFT_CLICK);
    this.frame(CANARIAS);
    this.ready=fetch('/api/v1/territory-outlines').then(r=>{if(!r.ok)throw Error('Contornos no disponibles');return r.json();}).then(data=>{
      for(const ring of data.rings)v.entities.add({polyline:{positions:C.Cartesian3.fromDegreesArray(ring.flatMap(p=>[p[0],p[1]])),width:1,material:C.Color.fromCssColorString('#43817c')}});
      v.scene.requestRender();
    }).catch(()=>{this.outlinesUnavailable=true;});
  }
  frame(bounds) {
    if(!validBounds(bounds))throw Error('Encuadre 3D inválido');
    const C=this.C;this.viewer.camera.setView({destination:C.Rectangle.fromDegrees(...bounds),orientation:{heading:0,pitch:-Math.PI/2,roll:0}});
    this.lastBounds=bounds.slice();this.framePose=cameraPose(C,this.viewer.camera);this.viewer.scene.requestRender();
  }
  home(){this.frame(CANARIAS);}
  bounds() {
    const C=this.C,camera=this.viewer.camera;
    if(this.framePose&&samePose(C,cameraPose(C,camera),this.framePose))return this.lastBounds.slice();
    // Derive a bounded surface footprint only when the user actually navigated.
    const canvas=this.viewer.scene.canvas,hits=[];
    for(const [x,y] of [[0,0],[canvas.clientWidth,0],[0,canvas.clientHeight],[canvas.clientWidth,canvas.clientHeight]]) {
      const hit=camera.pickEllipsoid(new C.Cartesian2(x,y),C.Ellipsoid.WGS84);
      if(hit){const p=C.Cartographic.fromCartesian(hit);hits.push([C.Math.toDegrees(p.longitude),C.Math.toDegrees(p.latitude)]);}
    }
    if(hits.length===4){const b=[Math.min(...hits.map(p=>p[0])),Math.min(...hits.map(p=>p[1])),Math.max(...hits.map(p=>p[0])),Math.max(...hits.map(p=>p[1]))];if(validBounds(b)&&b[2]-b[0]<25&&b[3]-b[1]<20)return b;}
    return this.lastBounds.slice();
  }
  setBase(config,notice) {
    const C=this.C,collection=this.viewer.imageryLayers,sequence=(this.baseSequence||0)+1;this.baseSequence=sequence;collection.removeAll();
    const add=(url,layers,transparent=false)=>{
      const provider=layers?new C.WebMapServiceImageryProvider({url,layers,rectangle:C.Rectangle.fromDegrees(-19.5,26,-12,31),tilingScheme:new C.GeographicTilingScheme({rectangle:C.Rectangle.fromDegrees(-19.5,26,-12,31),numberOfLevelZeroTilesX:1,numberOfLevelZeroTilesY:1}),parameters:{format:transparent?'image/png':'image/jpeg',transparent,version:'1.1.1'},credit:config.attribution,maximumLevel:config.max_zoom}):new C.UrlTemplateImageryProvider({url,credit:config.attribution,maximumLevel:config.max_zoom});
      provider.errorEvent.addEventListener(()=>{if(sequence===this.baseSequence)notice(`${config.name}: cartografía 3D no disponible. Las observaciones se conservan.`,true);});collection.addImageryProvider(provider);
    };
    add(config.url,config.kind==='street'?null:config.layers,config.id==='pnoa'||config.kind==='hybrid');if(config.kind==='hybrid')add(config.overlay_url,config.overlay_layers,true);
    this.viewer.scene.requestRender();
  }
  async loadTerrain(){
    if(this.terrainInfo)return this.terrainInfo;
    try{
      const response=await fetch('/api/v1/terrain');if(!response.ok)throw Error('MDT no disponible');
      const result=await response.json();
      if(result.state!=='documented_import'){this.terrainInfo=result.message;return this.terrainInfo;}
      this.grid=result.grid;this.renderTerrain();
      this.viewer.camera.moveEnd.addEventListener(()=>this.renderTerrain());
      this.terrainInfo=`MDT ${this.grid.metadata.product} · origen ${this.grid.metadata.source_resolution_m} m · malla ${this.grid.width}×${this.grid.height}, LOD visual · datum ${this.grid.metadata.vertical_datum} sin transformar · sin batimetría`;
      return this.terrainInfo;
    }catch{return 'MDT no disponible · globo elipsoidal · sin batimetría';}
  }
  renderTerrain(){
    const C=this.C,g=this.grid;if(!g)return;
    const height=this.viewer.camera.positionCartographic.height,step=height>100000?4:height>30000?2:1;
    if(this.terrainStep===step)return;
    this.terrainStep=step;
    if(this.terrainPrimitive)this.viewer.scene.primitives.remove(this.terrainPrimitive);
    const rows=[],cols=[];for(let r=0;r<g.height;r+=step)rows.push(r);for(let c=0;c<g.width;c+=step)cols.push(c);
    if(rows.at(-1)!==g.height-1)rows.push(g.height-1);if(cols.at(-1)!==g.width-1)cols.push(g.width-1);
    const positions=[],indices=[],lookup=new Map();
    for(let y=0;y<rows.length;y++)for(let x=0;x<cols.length;x++){
      const r=rows[y],c=cols[x],z=g.values[r*g.width+c];if(z===null)continue;
      const lon=g.bounds[0]+c/(g.width-1)*(g.bounds[2]-g.bounds[0]),lat=g.bounds[3]-r/(g.height-1)*(g.bounds[3]-g.bounds[1]);
      const p=C.Cartesian3.fromDegrees(lon,lat,z);lookup.set(y*cols.length+x,positions.length/3);positions.push(p.x,p.y,p.z);
    }
    for(let y=0;y<rows.length-1;y++)for(let x=0;x<cols.length-1;x++){
      const a=lookup.get(y*cols.length+x),b=lookup.get(y*cols.length+x+1),c=lookup.get((y+1)*cols.length+x),d=lookup.get((y+1)*cols.length+x+1);
      // No triangles across source nodata, even at a coarser visual LOD.
      let complete=true;for(let r=rows[y];r<=rows[y+1]&&complete;r++)for(let q=cols[x];q<=cols[x+1];q++)if(g.values[r*g.width+q]===null){complete=false;break;}
      if(complete&&[a,b,c,d].every(v=>v!==undefined))indices.push(a,c,b,b,c,d);
    }
    if(!indices.length)return;
    const geometry=C.GeometryPipeline.computeNormal(new C.Geometry({attributes:{position:new C.GeometryAttribute({componentDatatype:C.ComponentDatatype.DOUBLE,componentsPerAttribute:3,values:new Float64Array(positions)})},indices:new Uint32Array(indices),primitiveType:C.PrimitiveType.TRIANGLES,boundingSphere:C.BoundingSphere.fromVertices(positions)}));
    this.terrainPrimitive=this.viewer.scene.primitives.add(new C.Primitive({geometryInstances:new C.GeometryInstance({geometry,attributes:{color:C.ColorGeometryInstanceAttribute.fromColor(C.Color.fromCssColorString('#adc6af'))}}),appearance:new C.PerInstanceColorAppearance({flat:false,translucent:false,closed:false}),asynchronous:false}));
    this.viewer.scene.requestRender();
  }
  update(events,color) {
    const C=this.C;this.points.removeAll();
    for(const e of events)this.points.add({position:C.Cartesian3.fromDegrees(e.lon,e.lat,-e.depth_km*1000),pixelSize:Math.max(5,Math.min(17,5+((e.magnitude??0)+1)*2)),color:C.Color.fromCssColorString(color(e.depth_km)),outlineColor:C.Color.WHITE,outlineWidth:1,id:{risklabEvent:e},disableDepthTestDistance:Number.POSITIVE_INFINITY});
    this.viewer.scene.requestRender();
  }
  resize() {
    if(this.element.hidden||this.element.clientWidth<2||this.element.clientHeight<2)return;
    const C=this.C,camera=this.viewer.camera,pose=cameraPose(C,camera);
    this.viewer.resize();camera.setView({destination:pose.position,orientation:{direction:pose.direction,up:pose.up}});this.viewer.scene.requestRender();
  }
}
