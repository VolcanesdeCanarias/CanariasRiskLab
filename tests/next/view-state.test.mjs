import test from 'node:test';import assert from 'node:assert/strict';
import {panelBudget,paddedBounds,validBounds} from '../../next/view-state.mjs';
test('Research budget always retains a useful map on desktop/tablet/mobile',()=>{
 for(const [height,timeline,footer,mobile] of [[918,132,27,false],[700,170,30,false],[625,170,44,true],[430,170,44,true]]){
  const b=panelBudget({height,timeline,footer,mobile,requested:10000});assert.ok(b.height>=128);assert.ok(b.height<=460);
  if(height-timeline-footer>=b.mapMin+128)assert.ok(height-timeline-footer-b.height>=b.mapMin);
 }
});
test('physical short screens scroll rather than yield negative camera dimensions',()=>{const b=panelBudget({height:250,timeline:180,footer:40,mobile:true,requested:600});assert.equal(b.height,128);assert.equal(b.mapMin,250);});
test('navigation bounds are finite, ordered and padded without adding precision',()=>{
 assert.equal(validBounds([-13.55,29.2,-13.4,29.3]),true);for(const b of [[NaN,0,1,1],[0,1,0,2],[0,0,2,91]])assert.equal(validBounds(b),false);
 const b=paddedBounds([-13.5,29.24,-13.49,29.25]);assert.ok(Math.abs((b[2]-b[0])-.12)<1e-10);assert.ok(b[0]<-13.5&&b[1]<29.24&&b[2]>-13.49&&b[3]>29.25);
});
