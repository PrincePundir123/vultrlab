import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
test.skip(process.env.SKG_FULL_STACK!=='1','Requires local operator configuration and Docker stack');
test('setup panel blocks unconfigured live calls and explains invalid API responses',async({page})=>{
  const env=readFileSync(resolve('../../.env'),'utf8');
  const password=env.split('\n').find(x=>x.startsWith('OPERATOR_PASSWORD='))!.split('=').slice(1).join('=').trim();
  await page.goto('/');
  await page.getByLabel('Password',{exact:true}).fill(password);
  await page.getByRole('button',{name:'Sign in',exact:true}).click();
  // Explicit HTTP fixtures test UI states without making billed provider requests.
  await page.route('**/api/v1/system/provider',route=>route.fulfill({json:{configured:false,missing:['VULTR_INFERENCE_API_KEY'],chat_model:'',vision_model:'',endpoint_allowed:true}}));
  await page.getByRole('navigation').getByRole('link',{name:'Security & metrics'}).click();
  const panel=page.getByRole('region',{name:'Vultr connection'});
  await expect(panel.getByText(/Missing configuration/)).toBeVisible();
  await expect(panel.getByRole('button',{name:'Test live inference (uses tokens)',exact:true})).toBeDisabled();
  await page.route('**/api/v1/system/models',route=>route.fulfill({status:502,contentType:'text/html',body:'<h1>Proxy unavailable</h1>'}));
  await panel.getByRole('button',{name:'Load available model IDs'}).click();
  await expect(panel.getByRole('alert')).toContainText('HTTP 502');
  await expect(panel.getByRole('alert')).not.toContainText('<h1>');
});
