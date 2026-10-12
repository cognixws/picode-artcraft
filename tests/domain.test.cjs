const test = require('node:test');
const assert = require('node:assert/strict');
const {state, matches} = require('../ui/domain.js');
const workspace = {path:'/project'};
const base = {title:'WordCraft',kind:'Documents',category:'Documents',purpose:'Write and format documents',extensions:['.docx']};
test('status and contextual actions including workspace mismatch',()=>{
  for(const [id,action] of [['ready','open'],['not-installed','download'],['connected',null],['uncontrolled','refresh'],['connection-error','refresh'],['error','refresh'],['checking',null],['unavailable','settings']]) assert.equal(state({...base,state:id},workspace).action,action);
  assert.equal(state({...base,state:'connected',openedForRoot:'/other'},workspace).id,'other-workspace');
  assert.equal(state({...base,state:'connected',openedForRoot:'/project'},workspace).id,'connected');
});
test('search by task/extension and combine availability/category',()=>{
  const row={...base,state:'connected',installed:true};
  assert.ok(matches(row,'format','Documents','installed',workspace));
  assert.ok(matches(row,'.docx','All','connected',workspace));
  assert.ok(!matches(row,'','Images','all',workspace));
  assert.ok(!matches({...row,openedForRoot:'/other'},'','All','connected',workspace));
  assert.ok(matches({...row,state:'uncontrolled'},'','All','attention',workspace));
});
