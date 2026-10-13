import {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {api,type Json} from './api';

type Configuration={configured:boolean;missing:string[];chat_model:string;vision_model:string;endpoint_allowed:boolean};
type Probe={status:string;live_inference_verified:boolean;scope?:string;measurements?:Json[]};
export function ProviderSetup(){
  const config=useQuery({queryKey:['provider-config'],queryFn:()=>api<Configuration>('/system/provider')});
  const [models,setModels]=useState<string[]>();
  const [probe,setProbe]=useState<Probe>();
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const run=async(kind:'catalog'|'probe')=>{
    setBusy(true);setError('');if(kind==='probe')setProbe(undefined);
    try{
      if(kind==='catalog')setModels((await api<{models:string[]}>('/system/models')).models);
      else setProbe(await api<Probe>('/system/inference-check','POST'));
    }catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setBusy(false);}
  };
  return <section className="panel" aria-label="Vultr connection"><h2>Vultr connection</h2>
    <p>Check setup before learning a workflow. Your API key stays on the server.</p>
    {config.isPending?<p>Reading configuration…</p>:config.data&&<>
      {config.data.missing.length>0&&<p className="note">Missing configuration: {config.data.missing.join(', ')}. Add these values privately to .env and recreate the API and orchestrator services.</p>}
      {!config.data.endpoint_allowed&&<p role="alert" className="error">The configured inference endpoint is not allowed.</p>}
      <p className="muted">Text model: {config.data.chat_model||'Not configured'} · Vision model: {config.data.vision_model||'Not configured'}</p>
    </>}
    {(error||config.error)&&<p role="alert" className="error">{error||String(config.error)}</p>}
    <div className="actions"><button className="secondary" disabled={busy||!config.data?.endpoint_allowed} onClick={()=>void run('catalog')}>Load available model IDs</button>
      <button disabled={busy||!config.data?.configured||!config.data?.endpoint_allowed} onClick={()=>void run('probe')}>{busy?'Checking…':'Test live inference (uses tokens)'}</button></div>
    <p className="muted">Model discovery is public and does not verify your API key. The live test makes a small real text request. It does not test vision or a complete browser workflow.</p>
    {models&&<details open><summary>{models.length} available text model IDs</summary><pre>{models.join('\n')}</pre></details>}
    {probe&&<div role="status"><strong>{probe.live_inference_verified?'Verified text inference':'Inference not configured'}</strong><p>{probe.scope}</p><details><summary>Recorded provider measurements</summary><pre>{JSON.stringify(probe.measurements??[],null,2)}</pre></details></div>}
  </section>;
}
