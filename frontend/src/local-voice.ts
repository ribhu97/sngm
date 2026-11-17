/** Local Omni hears WAV turns; the device's speech voice reads the guide's reply. */
export class LocalVoice {
  private context?: AudioContext;
  private stream?: MediaStream;
  private processor?: ScriptProcessorNode;
  private stopped = false;
  private listening = false;
  private chunks: Float32Array[] = [];
  private speechMs = 0;
  private silenceMs = 0;
  private speaking = false;
  private elapsed = 0;
  constructor(private status:(value:string)=>void, private turn:(audio:string)=>Promise<string>, private caption:(text:string)=>void, private failure:(message:string)=>void = ()=>{}) {}
  async start(opening:string) {
    if(!('speechSynthesis' in window))throw new Error('Your browser cannot play the local guide’s voice. Try Chrome or choose ElevenLabs.');
    this.context = new AudioContext({sampleRate:24000});
    await this.context.resume();
    this.stream = await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true,autoGainControl:true}});
    if(this.stopped){this.stream.getTracks().forEach(t=>t.stop());return;}
    const input=this.context.createMediaStreamSource(this.stream);
    this.processor=this.context.createScriptProcessor(4096,1,1);
    this.processor.onaudioprocess=event=>{
      if(!this.listening || this.stopped)return;
      const data=event.inputBuffer.getChannelData(0);
      const ms=data.length/this.context!.sampleRate*1000;
      let energy=0;for(const sample of data)energy+=sample*sample;
      const audible=Math.sqrt(energy/data.length)>.018;
      if(audible){this.speaking=true;this.speechMs+=ms;this.silenceMs=0;this.status('Listening');}
      if(!this.speaking)return;
      this.chunks.push(new Float32Array(data));this.elapsed+=ms;
      if(!audible)this.silenceMs+=ms;
      if(this.elapsed>20000 || (this.silenceMs>1100 && this.speechMs>180))void this.finishTurn();
    };
    input.connect(this.processor);this.processor.connect(this.context.destination);
    await this.speak(opening);
  }
  private async finishTurn(){
    this.listening=false;
    const chunks=this.chunks;this.chunks=[];this.speaking=false;this.speechMs=0;this.silenceMs=0;this.elapsed=0;
    this.status('Reflecting');
    const length=chunks.reduce((sum,c)=>sum+c.length,0), bytes=new Uint8Array(44+length*2), view=new DataView(bytes.buffer);
    const str=(offset:number,text:string)=>{for(let i=0;i<text.length;i++)view.setUint8(offset+i,text.charCodeAt(i));};
    str(0,'RIFF');view.setUint32(4,36+length*2,true);str(8,'WAVE');str(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);
    const rate=this.context!.sampleRate;view.setUint32(24,rate,true);view.setUint32(28,rate*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true);str(36,'data');view.setUint32(40,length*2,true);
    let index=44;for(const chunk of chunks)for(const value of chunk){view.setInt16(index,Math.max(-1,Math.min(1,value))*32767,true);index+=2;}
    let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
    try {const reply=await this.turn(btoa(binary));if(!this.stopped)await this.speak(reply);}
    catch(e){if(!this.stopped){const message=e instanceof Error?e.message:'I couldn’t hear that. Try starting again.';this.stop();this.failure(message);}}
  }
  private speak(text:string):Promise<void>{
    if(this.stopped)return Promise.resolve();
    this.caption(text);this.status('Speaking');this.listening=false;
    return new Promise((resolve,reject)=>{
      const utterance=new SpeechSynthesisUtterance(text);utterance.rate=.92;utterance.pitch=1;
      const voices=speechSynthesis.getVoices();utterance.voice=voices.find(v=>v.lang==='en-IN')||voices.find(v=>v.lang==='en-GB')||voices.find(v=>v.lang.startsWith('en'))||null;
      utterance.onend=()=>{if(!this.stopped){this.listening=true;this.status('Listening');}resolve();};
      utterance.onerror=()=>{if(!this.stopped){this.status('Tap Start guide to enable audio.');reject(new Error('Tap Start guide to enable audio.'));}else resolve();};
      speechSynthesis.speak(utterance);
    });
  }
  stop(){this.stopped=true;this.listening=false;speechSynthesis.cancel();this.processor?.disconnect();this.stream?.getTracks().forEach(t=>t.stop());void this.context?.close();}
}
