// Dependency-free structural smoke test of the offline HTML preview.
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../web/Petite-Victoire.html'),'utf8');
const script=html.split('<script>')[1].split('</script>')[0];
const files=[];
class Element {
 constructor(tag='div') {this.tag=tag;this.listeners={};this.children=[];this.attributes={};this.textContent='';this.value='';this.checked=false;this.style={};}
 setAttribute(name,value){this.attributes[name]=value;}
 appendChild(element){this.children.push(element);return element;}
 replaceChildren(){this.children=[];}
 addEventListener(type,cb){this.listeners[type]=cb;}
 getBoundingClientRect(){return {left:0,top:0,width:1000,height:256};}
 click(){if(this.download)files.push({filename:this.download,blob:context.URL.lastBlob});}
}
const ids={};
for(const name of ['score','roll','play','stop','loop','time','volume','pan','bpm','midi','wav','status','bpmVal','volumeVal','panVal','tempoDisplay','playhead'])ids[name]=new Element();
ids.loop.checked=true;ids.volume.value='75';ids.pan.value='0';ids.bpm.value='120';
const blobURLs=[];
const url={createObjectURL(blob){blobURLs.push(blob);this.lastBlob=blob;return 'blob:mock';},revokeObjectURL(){}};
const context={
 window:{},document:{getElementById:id=>ids[id],createElementNS:(ns,tag)=>new Element(tag),createElement:tag=>new Element(tag)},
 URL:url,Blob,TextEncoder,Float32Array,Math,Number,Array,String,console,
 setTimeout(cb){/* Skip revoke URL for testing */},requestAnimationFrame(){return 0;},cancelAnimationFrame(){}
};
vm.createContext(context);
vm.runInContext(script,context,{timeout:3000});
assert(ids.score.children.length>30);
assert(ids.roll.children.length>30);
assert(ids.play.listeners.click && ids.stop.listeners.click);
ids.midi.listeners.click();
ids.wav.listeners.click();
assert.equal(files.length,2);
(async()=>{
 const midi=new Uint8Array(await files[0].blob.arrayBuffer());
 const wav=new Uint8Array(await files[1].blob.arrayBuffer());
 assert.equal(files[0].filename,'Petite-Victoire.mid');
 assert.equal(files[1].filename,'Petite-Victoire.wav');
 assert.equal(Buffer.from(midi.slice(0,4)).toString(),'MThd');
 assert.equal(Buffer.from(wav.slice(0,4)).toString(),'RIFF');
 assert.equal(wav.length,44+352800*4);
 ids.roll.listeners.click({clientX:90,clientY:15});
 assert.match(ids.status.textContent,/Note MIDI/);
 console.log('WEB_PREVIEW_SMOKE=PASS MIDI='+midi.length+' WAV='+wav.length);
})().catch(err=>{console.error(err);process.exitCode=1});
