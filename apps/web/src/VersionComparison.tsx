import {useState} from 'react';
import type {Operation} from './api';

const show=(value:unknown)=>value===undefined?'Not present':JSON.stringify(value,null,2);
function flatten(value:unknown,prefix=''):Record<string,unknown>{
  if(value!==null && typeof value==='object' && Object.keys(value).length){
    return Object.fromEntries(Object.entries(value).flatMap(([key,item])=>Object.entries(flatten(item,prefix?`${prefix}.${key}`:key))));
  }
  return {[prefix]:value};
}
export function VersionComparison({operation}:{operation:Operation}){
  const [from,setFrom]=useState('');
  const [to,setTo]=useState('');
  const versions=operation.versions;
  if(versions.length<2)return null;
  const previous=versions.find(v=>String(v.number)===from)??versions[1];
  const current=versions.find(v=>String(v.number)===to)??versions[0];
  const a=flatten({workflow:previous.definition,contract:previous.contract});
  const b=flatten({workflow:current.definition,contract:current.contract});
  const changed=[...new Set([...Object.keys(a),...Object.keys(b)])].filter(key=>show(a[key])!==show(b[key])).sort();
  return <details className="version-comparison"><summary>Compare immutable versions</summary>
    <div className="form-grid"><label>From version<select value={previous.number} onChange={e=>setFrom(e.target.value)}>{versions.map(v=><option key={v.id} value={v.number}>Version {v.number}</option>)}</select></label>
    <label>To version<select value={current.number} onChange={e=>setTo(e.target.value)}>{versions.map(v=><option key={v.id} value={v.number}>Version {v.number}</option>)}</select></label></div>
    <p>{changed.length} changed fields. Comparing versions does not activate either version.</p>
    {changed.length?<div className="table-wrap"><table><thead><tr><th>Field</th><th>Version {previous.number}</th><th>Version {current.number}</th></tr></thead><tbody>{changed.map(key=><tr key={key}><td>{key}</td><td><pre>{show(a[key])}</pre></td><td><pre>{show(b[key])}</pre></td></tr>)}</tbody></table></div>:<p>No workflow or permission differences.</p>}
  </details>;
}
