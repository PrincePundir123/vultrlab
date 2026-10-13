import {useState} from 'react';
import {ShieldCheck,KeyRound,ArrowUpRight} from 'lucide-react';
import {api,type User} from './api';

export function Login({onLogin}:{onLogin:(user:User)=>void}){
  const [signup,setSignup]=useState(false);
  const [username,setUsername]=useState('');
  const [password,setPassword]=useState('');
  const [confirmation,setConfirmation]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const submit=async()=>{
    setError('');
    if(signup&&password!==confirmation){setError('Passwords do not match.');return;}
    setBusy(true);
    try{onLogin(await api<User>(signup?'/auth/register':'/auth/login','POST',{username:username.trim(),password}));}
    catch(e){setError(e instanceof Error?e.message:String(e));}
    finally{setBusy(false);}
  };
  return <div className="login"><div className="login-story"><ShieldCheck size={44}/><h1>Teach once.<br/>Execute safely.<br/><em>Verify always.</em></h1><p>Reusable browser operations with explicit permissions and evidence you can inspect.</p><small>CONTROLLED SUPPLIER DEMONSTRATION</small></div>
    <form onSubmit={e=>{e.preventDefault();void submit();}}><KeyRound size={30}/><h2>{signup?'Create account':'Sign in'}</h2>
      <p>{signup?'Create your private workspace for read-only supplier checks.':'Sign in to your account to view your tasks and results.'}</p>
      <label>Username<input autoComplete="username" value={username} onChange={e=>setUsername(e.target.value)} required minLength={signup?3:1} maxLength={signup?40:100} pattern={signup?'[a-z][a-z0-9_-]{2,39}':undefined}/></label>
      {signup&&<p className="muted">3–40 lowercase characters. Start with a letter; numbers, underscores and hyphens are allowed.</p>}
      <label>Password<input type="password" autoComplete={signup?'new-password':'current-password'} value={password} onChange={e=>setPassword(e.target.value)} required minLength={signup?12:1} maxLength={200}/></label>
      {signup&&<><p className="muted">Use at least 12 characters.</p><label>Confirm password<input type="password" autoComplete="new-password" value={confirmation} onChange={e=>setConfirmation(e.target.value)} required maxLength={200}/></label></>}
      {error&&<p role="alert" className="error">{error}</p>}
      <button disabled={busy} type="submit">{busy?'Please wait…':signup?'Create account':'Sign in'} <ArrowUpRight size={17}/></button>
      <button type="button" className="secondary" disabled={busy} onClick={()=>{setSignup(!signup);setUsername('');setPassword('');setConfirmation('');setError('');}}>{signup?'Already have an account? Sign in':'Create a new account'}</button>
      <small>New accounts can run read-only checks. Supplier submissions and administration require operator permissions. All supplier records are synthetic.</small>
    </form></div>;
}
