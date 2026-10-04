const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/app.js', 'utf8');
const helper = source.slice(source.indexOf('function devicePreferences'), source.indexOf('const state ='));
const defaults = {public_account:{uid:''},akasha:{enabled:true},ui:{accent:'amber',language:'id'},hoyolab:{enabled:false}};
function device() {
  const storage = new Map();
  return vm.createContext({localStorage:{getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)},defaults});
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
