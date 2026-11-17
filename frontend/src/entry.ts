/** Demo routes are fresh; restore requires the same backend boot or an explicit link. */
export function runToRestore(path:string,search:string,storedRun:string|null,storedBoot:string|null,serverBoot:string):string|null{
 const params=new URLSearchParams(search);
 const explicit=params.get('resume');
 if(explicit)return explicit;
 return path==='/app'&&!params.has('scenario')&&storedBoot===serverBoot?storedRun:null;
}
