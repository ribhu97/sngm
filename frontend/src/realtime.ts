import { ToolTurns } from './tool-turns';
/** Explicit PCM24k WebSocket audio; all resources belong to one connection. */
export class Realtime {
  ws?: WebSocket; context?: AudioContext; stream?: MediaStream; processor?: ScriptProcessorNode;
  private turns=new ToolTurns();
  sources = new Set<AudioBufferSourceNode>(); next = 0; stopped = false; item = ''; played = 0; response = ''; cancelled = new Set<string>(); itemStart = 0;
  constructor(private status: (text:string)=>void, private tool:(name:string,args:any,id:string)=>Promise<any>, private caption:(text:string)=>void = ()=>{}) {}
  send(event:any) { if(this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(event)); }
  silence() { for(const source of this.sources) {try{source.stop();}catch{}} this.sources.clear(); this.next=0; }
  interrupt() { if(this.response)this.cancelled.add(this.response); this.played=this.context && this.itemStart?Math.max(0,(this.context.currentTime-this.itemStart)*1000):0; this.send({type:'response.cancel'}); if(this.item) this.send({type:'conversation.item.truncate',item_id:this.item,content_index:0,audio_end_ms:Math.floor(this.played)}); this.silence(); this.status('Interrupted'); }
  async start(config:any) {
    this.stopped=false;
    try {
      this.context = new AudioContext({sampleRate:24000}); await this.context.resume();
      this.stream = await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true,noiseSuppression:true}});
      if(this.stopped) { this.stream.getTracks().forEach(t=>t.stop()); return; }
      this.ws = new WebSocket(config.url, ['realtime', `openai-insecure-api-key.${config.value}`]);
      await new Promise<void>((resolve,reject)=>{const timer=setTimeout(()=>reject(new Error('Voice connection timed out.')),12000); this.ws!.onopen=()=>{clearTimeout(timer);resolve();}; this.ws!.onerror=()=>{clearTimeout(timer);reject(new Error('Voice connection failed. Check provider access.'));};});
      this.ws.onclose=()=>{if(!this.stopped){this.stop();this.status('Disconnected · reconnect to continue');}};
      this.ws.onmessage = async event => {
        if(this.stopped) return;
        const e=JSON.parse(event.data);
        if(e.type==='response.created')this.response=e.response.id;
        if(e.response_id && this.cancelled.has(e.response_id))return;
        if(['response.audio_transcript.done','response.output_audio_transcript.done'].includes(e.type))this.caption(e.transcript);
        if(e.type==='error') {this.status(e.error?.message || 'Voice error');return;}
        if(e.type==='input_audio_buffer.speech_started') {this.turns.newUserTurn();if(this.response||this.sources.size)this.interrupt();this.status('Listening');}
        if(e.type==='input_audio_buffer.speech_stopped') this.status('Processing');
        if(['response.audio.delta','response.output_audio.delta'].includes(e.type)) {
          this.status('Speaking'); if(e.item_id!==this.item){this.item=e.item_id;this.itemStart=Math.max(this.context!.currentTime,this.next);this.played=0;}
          const bytes=Uint8Array.from(atob(e.delta), c=>c.charCodeAt(0));
          const pcm=new DataView(bytes.buffer), audio=this.context!.createBuffer(1,bytes.length/2,24000);
          const values=audio.getChannelData(0); for(let i=0;i<values.length;i++) values[i]=pcm.getInt16(i*2,true)/32768;
          const source=this.context!.createBufferSource(); source.buffer=audio; source.connect(this.context!.destination);
          const when=Math.max(this.context!.currentTime,this.next);this.next=when+audio.duration;this.sources.add(source);
          source.onended=()=>{this.sources.delete(source);this.played+=audio.duration*1000;if(!this.sources.size)this.status('Listening');}; source.start(when);
        }
        if(e.type==='response.function_call_arguments.done') {
          const response=e.response_id||this.response;
          const signature=e.name+':'+e.arguments;
          const accepted=this.turns.register(response,signature,async()=>{
            let output;
            try{output=await this.tool(e.name,JSON.parse(e.arguments),e.call_id);}
            catch(error){output={error:String(error),retry_allowed:false,instruction:'Do not retry this action on the same turn. Ask one specific clarification, then wait.'};}
            if(this.stopped||this.cancelled.has(response))return;
            this.send({type:'conversation.item.create',item:{type:'function_call_output',call_id:e.call_id,output:JSON.stringify(output)}});
          });
          if(!accepted)this.send({type:'conversation.item.create',item:{type:'function_call_output',call_id:e.call_id,output:JSON.stringify({already_attempted:true,instruction:'This turn is complete. Do not repeat the tool or question. Wait for the person.'})}});
        }
        if(e.type==='response.done'){
          const response=e.response?.id||e.response_id||this.response;
          if(this.response===response)this.response='';
          if(await this.turns.complete(response)&&!this.stopped&&!this.cancelled.has(response))this.send({type:'response.create'});
        }
      };
      const source=this.context.createMediaStreamSource(this.stream);
      // ScriptProcessor keeps the local demo dependency-free; zero output prevents feedback.
      this.processor=this.context.createScriptProcessor(4096,1,1);
      this.processor.onaudioprocess=e=>{
        if(this.stopped)return;
        const input=e.inputBuffer.getChannelData(0), data=new Uint8Array(input.length*2), view=new DataView(data.buffer);
        for(let i=0;i<input.length;i++)view.setInt16(i*2,Math.max(-1,Math.min(1,input[i]))*32767,true);
        let binary='';for(const byte of data)binary+=String.fromCharCode(byte);
        this.send({type:'input_audio_buffer.append',audio:btoa(binary)});
      };
      source.connect(this.processor);this.processor.connect(this.context.destination);
      this.send({type:'response.create'});this.status('Listening');
    } catch(e) {this.stop(); throw e;}
  }
  stop() {this.stopped=true;this.silence();this.processor?.disconnect();this.stream?.getTracks().forEach(t=>t.stop());this.ws?.close();void this.context?.close();}
}
