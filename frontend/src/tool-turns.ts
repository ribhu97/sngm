/** Each provider response gets one continuation after all its tool work completes. */
export class ToolTurns {
  private pending=new Map<string,Promise<void>[]>();
  private signatures=new Set<string>();
  private continued=new Set<string>();
  private rounds=0;
  private userTurn=0;
  newUserTurn(){this.userTurn++;this.rounds=0;this.signatures.clear();this.pending.clear();this.continued.clear();}
  register(response:string,signature:string,work:()=>Promise<void>):boolean{
    if(this.signatures.has(signature)||this.rounds>=4)return false;
    this.signatures.add(signature);
    const token=this.userTurn;
    const task=Promise.resolve().then(()=>{if(token===this.userTurn)return work();});
    const tasks=this.pending.get(response)||[];tasks.push(task);this.pending.set(response,tasks);
    return true;
  }
  async complete(response:string):Promise<boolean>{
    if(this.continued.has(response))return false;
    this.continued.add(response);
    const tasks=this.pending.get(response);if(!tasks?.length)return false;
    const token=this.userTurn;
    await Promise.allSettled(tasks);this.pending.delete(response);
    if(token!==this.userTurn||this.rounds>=4)return false;
    this.rounds++;return true;
  }
}
