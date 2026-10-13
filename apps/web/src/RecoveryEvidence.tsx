import {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {Link,useNavigate} from 'react-router-dom';
import {api,type Job,type Json} from './api';
type Entry={id:number;kind:string;data:Json};
export function RecoveryEvidence({job,events,admin}:{job:Job;events:Entry[];admin:boolean}){
 const nav=useNavigate();const [error,setError]=useState('');const [busy,setBusy]=useState(false);
 const sourceId=job.payload.source_job_id as string|undefined;
 const source=useQuery({queryKey:['recovery-source',sourceId],queryFn:()=>api<Job>('/tasks/'+sourceId),enabled:!!sourceId});
 if(job.state!=='PORTAL_CHANGED'&&!['repair','learn'].includes(job.kind))return null;
 const start=events.find(e=>e.kind==='RECOVERY_STARTED');const old=start?.data.previous as {number:number;definition:Json;contract:Json}|null;
 const failed=source.data??(job.state==='PORTAL_CHANGED'?job:null);
 const shots=(failed?.result.artifacts??[]) as string[];
 const candidates=events.filter(e=>e.kind==='CANDIDATE_VERSION');
 return <section className="panel"><h2>Recovery and evidence</h2>{sourceId&&<Link to={'/tasks/'+sourceId}>Open original failed execution</Link>}{failed&&<><p>Failure: {JSON.stringify(failed.result.failure)} · Previous version {String(failed.result.version??'unknown')}</p>{shots.map(id=><img className="evidence" key={id} src={'/api/v1/artifacts/'+id} alt="Browser at the failed operation"/>)}</>}{source.error&&<p role="alert">Could not load the original execution.</p>}
 {job.state==='PORTAL_CHANGED'&&admin&&<button disabled={busy} onClick={async()=>{setBusy(true);try{const next=await api<Job>('/operations/get_order_status/repair?source_job_id='+job.id,'POST');nav('/tasks/'+next.id);}catch(e){setError(String(e));}finally{setBusy(false);}}}>Repair this failure and run checks</button>}{error&&<p role="alert">{error}</p>}
 {old&&<details><summary>Previous operation v{old.number}</summary><pre>{JSON.stringify(old.definition,null,2)}</pre></details>}
 {candidates.map((candidate,index)=>{const next=candidates[index+1];const checks=events.filter(e=>e.kind==='REGRESSION'&&e.id>candidate.id&&(!next||e.id<next.id));const contract=candidate.data.contract as Json;const keys=Array.from(new Set([...Object.keys(old?.contract??{}),...Object.keys(contract)]));const diff=keys.filter(k=>JSON.stringify(old?.contract[k])!==JSON.stringify(contract[k]));return <article key={candidate.id}><h3>Candidate v{String(candidate.data.number)}</h3><p>{checks.filter(e=>e.data.verified).length}/{checks.length} observed checks passed · {checks.filter(e=>e.data.held_out).length} held-out cases</p><details><summary>Definition and validation details</summary><pre>{JSON.stringify({definition:candidate.data.definition,checks:checks.map(e=>e.data)},null,2)}</pre></details><details><summary>Contract changes ({diff.length})</summary><pre>{JSON.stringify(diff.map(key=>({key,before:old?.contract[key],after:contract[key]})),null,2)}</pre></details></article>})}
 {events.filter(e=>['CANDIDATE_REJECTED','CANDIDATE_PROMOTED'].includes(e.kind)).map(e=><p key={e.id}><strong>{e.kind.replaceAll('_',' ')}</strong>: {String(e.data.reason)}</p>)}{!candidates.length&&job.kind==='repair'&&<p>No candidate has been recorded yet.</p>}<p className="muted">Promotion requires every regression check to pass. A generated write candidate requires a separate review and each submission requires its own approval.</p></section>
}
