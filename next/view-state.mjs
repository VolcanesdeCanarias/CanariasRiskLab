// Layout and geographic state are independent of query/filter state.
export const CANARIAS = [-18.3, 27.5, -13.25, 29.55];
export function validBounds(b) {
  return Array.isArray(b) && b.length===4 && b.every(Number.isFinite) && b[0]<b[2] && b[1]<b[3] && b[0]>=-180 && b[2]<=180 && b[1]>=-90 && b[3]<=90;
}
export function paddedBounds(b, minimum=.06) {
  if(!validBounds(b)) throw Error('Encuadre geográfico no válido');
  const x=(b[0]+b[2])/2,y=(b[1]+b[3])/2,dx=Math.max(minimum,(b[2]-b[0])/2),dy=Math.max(minimum,(b[3]-b[1])/2);
  return [x-dx,y-dy,x+dx,y+dy];
}
export function panelBudget({height,timeline,footer,mobile=false,requested=280}) {
  const mapMin=mobile?250:320, min=128;
  const available=Math.floor(height-timeline-footer-mapMin);
  // On very short screens the workspace scrolls; the map never becomes a strip.
  const max=Math.max(min,Math.min(mobile?260:460,available));
  return {min,max,height:Math.max(min,Math.min(max,requested)),mapMin};
}
export function leafletBounds(bounds) {return [[bounds[1],bounds[0]],[bounds[3],bounds[2]]];}
export function geographicBounds(bounds) {return [bounds.getWest(),bounds.getSouth(),bounds.getEast(),bounds.getNorth()];}
export function cameraPose(C,camera) {
  return {position:C.Cartesian3.clone(camera.positionWC),direction:C.Cartesian3.clone(camera.directionWC),up:C.Cartesian3.clone(camera.upWC)};
}
export function samePose(C,a,b) {
  return C.Cartesian3.equalsEpsilon(a.position,b.position,1e-10,.001) && C.Cartesian3.equalsEpsilon(a.direction,b.direction,1e-10,1e-8);
}
