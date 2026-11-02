// Earth is a rendering component, never an independent scientific data source.
// Cesium 1.146.0 matches RiskLab Earth V2.1; no private terrain/imagery is redistributed.
export class EarthView {
  constructor(element, select) {
    const C=globalThis.Cesium;
    this.C=C;this.select=select;
    this.viewer=new C.Viewer(element,{terrainProvider:new C.EllipsoidTerrainProvider(),baseLayer:false,baseLayerPicker:false,
      animation:false,timeline:false,geocoder:false,homeButton:false,sceneModePicker:false,navigationHelpButton:false,
      fullscreenButton:false,selectionIndicator:false,infoBox:false,skyBox:false,skyAtmosphere:false,
      contextOptions:{webgl:{preserveDrawingBuffer:true}},requestRenderMode:true,maximumRenderTimeChange:Infinity});
    const v=this.viewer;
    v.scene.globe.baseColor=C.Color.fromCssColorString('#c9deda');
    v.scene.backgroundColor=C.Color.fromCssColorString('#edf3ee');
    v.scene.globe.translucency.enabled=true;v.scene.globe.translucency.frontFaceAlpha=.5;
    v.scene.globe.translucency.backFaceAlpha=.2;v.scene.globe.showGroundAtmosphere=false;
    this.points=v.scene.primitives.add(new C.PointPrimitiveCollection());
    this.handler=new C.ScreenSpaceEventHandler(v.scene.canvas);
    this.handler.setInputAction(click=>{const hit=v.scene.pick(click.position);if(hit?.id?.risklabEvent)this.select(hit.id.risklabEvent);},C.ScreenSpaceEventType.LEFT_CLICK);
    this.home();
    this.ready=fetch('/api/v1/territory-outlines').then(r=>{if(!r.ok)throw Error('Contornos no disponibles');return r.json();}).then(data=>{
      for(const ring of data.rings)v.entities.add({polyline:{positions:C.Cartesian3.fromDegreesArray(ring.flatMap(p=>[p[0],p[1]])),width:1,material:C.Color.fromCssColorString('#43817c')}});
      v.scene.requestRender();
    }).catch(()=>{this.outlinesUnavailable=true;});
  }
  home(){const C=this.C;this.viewer.camera.lookAt(C.Cartesian3.fromDegrees(-15.5,28.35,0),new C.HeadingPitchRange(0,-Math.PI/3,650000));this.viewer.camera.lookAtTransform(C.Matrix4.IDENTITY);this.viewer.scene.requestRender();}
  update(events,color){const C=this.C;this.points.removeAll();for(const e of events)this.points.add({position:C.Cartesian3.fromDegrees(e.lon,e.lat,-e.depth_km*1000),pixelSize:Math.max(5,Math.min(17,5+(e.magnitude+1)*2)),color:C.Color.fromCssColorString(color(e.depth_km)),outlineColor:C.Color.WHITE,outlineWidth:1,id:{risklabEvent:e},disableDepthTestDistance:Number.POSITIVE_INFINITY});this.viewer.scene.requestRender();}
  resize(){this.viewer.resize();this.viewer.scene.requestRender();}
}
