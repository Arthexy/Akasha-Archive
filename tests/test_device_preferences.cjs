const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/app.js', 'utf8');
const helper = source.slice(source.indexOf('function readDeviceHoyo'), source.indexOf('const state ='));
const defaults = {public_account:{uid:''},akasha:{enabled:true},ui:{accent:'amber',language:'id'},hoyolab:{enabled:false}};
function device() {
  const storage = new Map();
  return vm.createContext({localStorage:{getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value),removeItem:key=>storage.delete(key)},defaults});
}
const first = device(), second = device();
for (const context of [first,second]) vm.runInContext(helper, context);
vm.runInContext('devicePreferences(defaults,{public_account:{uid:"812345678"},ui:{accent:"ocean",language:"en"},akasha:{enabled:false},hoyolab:{cookies:{ltoken_v2:"never-store"}}})', first);
assert.equal(vm.runInContext('devicePreferences(defaults).public_account.uid', first), '812345678');
assert.equal(vm.runInContext('devicePreferences(defaults).ui.accent', first), 'ocean');
assert.equal(vm.runInContext('devicePreferences(defaults).akasha.enabled', first), false);
assert.equal(vm.runInContext('devicePreferences(defaults).public_account.uid', second), '');
assert.equal(vm.runInContext('localStorage.getItem("hoyo-device-preferences").includes("never-store")', first), false);
vm.runInContext('localStorage.setItem("hoyo-device-preferences","broken JSON")', first);
assert.equal(vm.runInContext('devicePreferences(defaults).public_account.uid', first), '');
assert.equal(defaults.public_account.uid, '');
console.log('Device preferences checks passed: persistence, isolation, secret exclusion, invalid storage.');

async function connectionChecks() {
  const requests = [];
  first.fetch = async (url, options)=>{
    requests.push({url,...options});
    return {ok:true,json:async()=>({data:[{uid:'812345678',nickname:'Only this device'}]})};
  };
  Object.assign(first, {publicMode:true,csrf:'test',state:{config:defaults,notesGeneration:0},waitSeconds:()=>0,rememberCooldown(){}});
  vm.runInContext(source.slice(source.indexOf('async function api('),source.indexOf('function show(')),first);
  const run = code=>vm.runInContext(code, first);
  await run('api("/auth/hoyolab","POST",{cookies:{ltuid_v2:"123",ltoken_v2:"device-secret"},region:"os"})');
  assert.equal(requests.length,0);
  assert.equal(run('devicePreferences(defaults).hoyolab.configured'),true);
  assert.equal(run('JSON.stringify(devicePreferences(defaults)).includes("device-secret")'),false);
  assert.equal(vm.runInContext('devicePreferences(defaults).hoyolab.configured',second),false);
  await run('api("/config","PATCH",{hoyolab:{enabled:true,game_uid:"812345678"}})');
  await run('api("/auth/hoyolab/test","POST",{})');
  await run('api("/notes")');
  await run('api("/refresh","POST",{source:"explore"})');
  assert.deepEqual(requests.map(r=>r.url),['/api/v1/hoyolab/accounts','/api/v1/hoyolab/notes','/api/v1/hoyolab/explore']);
  for (const request of requests) {
    assert.equal(request.method,'POST');
    assert.equal(request.url.includes('device-secret'),false);
    assert.equal(JSON.parse(request.body).cookies.ltoken_v2,'device-secret');
    assert.equal(JSON.parse(request.body).game_uid,'812345678');
  }
  // Replacing cookies must discard the previous bound account and optional fields.
  await run('api("/auth/hoyolab","POST",{cookies:{ltuid_v2:"456",ltoken_v2:"replacement"},region:"cn"})');
  assert.equal(run('readDeviceHoyo().game_uid'),'');
  assert.equal(run('readDeviceHoyo().region'),'cn');
  await run('api("/auth/hoyolab","DELETE")');
  assert.equal(run('devicePreferences(defaults).hoyolab.configured'),false);
  assert.equal(run('localStorage.getItem("hoyo-device-hoyolab")'),null);
  await assert.rejects(run('api("/notes")'),/Configure ltuid_v2/);
  await run('api("/auth/hoyolab","POST",{cookies:{ltuid_v2:"123",ltoken_v2:"pending-secret"},region:"os"})');
  let finish;
  first.fetch=()=>new Promise(resolve=>{finish=resolve;});
  const pending=run('api("/auth/hoyolab/test","POST",{})');
  await run('api("/auth/hoyolab","DELETE")');
  finish({ok:true,json:async()=>({data:[{uid:'812345678'}]})});
  await assert.rejects(pending,/Koneksi HoYoLAB berubah/);
  const count=requests.length;
  first.localStorage.setItem=()=>{throw new Error('Storage unavailable');};
  await assert.rejects(run('api("/auth/hoyolab","POST",{cookies:{ltuid_v2:"123",ltoken_v2:"unsaved"},region:"os"})'),/Storage unavailable/);
  assert.equal(requests.length,count);
  console.log('Device HoYoLAB checks passed: local save/delete, isolated credentials, POST-only proxy, replacement, unavailable storage.');
}
connectionChecks().catch(error=>{console.error(error);process.exitCode=1;});
