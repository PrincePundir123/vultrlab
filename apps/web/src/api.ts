export type User = {id:string;username:string;role:string;csrf:string};
export type Order = {order_id:string;expected_delivery:string};
export type Json = Record<string, unknown>;
export type Job = {id:string;kind:string;state:string;payload:Json;result:Json;created:number;finished:number|null};
export type Version = {id:string;number:number;created:number;expires:number;digest:string;definition:Json;contract:Json;validations:{passed:boolean;details:Json}[]};
export type Operation = {name:string;state:string;active_version:number|null;history:Json[];versions:Version[]};
export type Draft = {id:string;snapshot:{order_id:string;message:string;version:number};digest:string;state:string;expires:number;job_id:string|null};
let csrf='';
export function setCsrf(value:string){csrf=value;}
export async function api<T>(path:string, method='GET', body?:unknown):Promise<T>{
  const response=await fetch('/api/v1'+path,{method,credentials:'same-origin',headers:{...(body instanceof FormData?{}:{'Content-Type':'application/json'}),'X-CSRF-Token':csrf},body:body===undefined?undefined:body instanceof FormData?body:JSON.stringify(body)});
  const value=await response.json();
  if(response.status===401 && path!=='/auth/login') window.dispatchEvent(new Event('skg-session-expired'));
  if(!response.ok) throw new Error(typeof value.error?.message==='string'?value.error.message:JSON.stringify(value.detail??value.error??value));
  return value as T;
}
