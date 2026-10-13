import {test,expect} from '@playwright/test';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
test.skip(process.env.SKG_FULL_STACK!=='1','Requires running Docker stack, validated fixture operation and orchestrator');
test('real UI approval submits through Docker and displays independently verified receipt',async({page})=>{
  test.setTimeout(120000);
  const env=readFileSync(resolve('../../.env'),'utf8');
  const password=env.split('\n').find(x=>x.startsWith('OPERATOR_PASSWORD='))!.split('=').slice(1).join('=').trim();
  await page.goto('/');
  await page.getByLabel('Username',{exact:true}).fill('operator');
  await page.getByLabel('Password',{exact:true}).fill(password);
  await page.getByRole('button',{name:'Sign in'}).click();
  await expect(page.getByRole('heading',{name:'Every action. Accounted for.'})).toBeVisible();
  page.on('dialog',dialog=>dialog.accept());
  await page.getByRole('navigation').getByRole('link',{name:'Operation library'}).click();
  await expect(page.getByRole('heading',{name:'submit_delivery_request',exact:true})).toBeVisible();
  const review=page.getByRole('button',{name:'Review and activate latest write version'});
  if(await review.count()){
    await review.click();
    await expect(review).toHaveCount(0);
  }
  await page.getByRole('navigation').getByRole('link',{name:'Approval center'}).click();
  await page.getByLabel('Order ID',{exact:true}).fill('ORD-104');
  const message=`UI acceptance ${Date.now()}: please confirm delivery for ORD-104.`;
  await page.getByLabel('Exact message').fill(message);
  await page.getByRole('button',{name:'Create approval preview'}).click();
  const card=page.locator('.panel').filter({has:page.locator('blockquote',{hasText:message})}).first();
  await expect(card.getByText('AWAITING APPROVAL',{exact:true})).toBeVisible();
  await card.getByRole('button',{name:'Approve exact request'}).click();
  await expect(card.getByRole('button',{name:'Submit approved request'})).toBeVisible();
  await page.screenshot({path:'../../docs/screenshots/approval.png',fullPage:true});
  await card.getByRole('button',{name:'Submit approved request'}).click();
  await expect(page.locator('.title .badge')).toHaveText('VERIFIED',{timeout:90000});
  await page.screenshot({path:'../../docs/screenshots/verified-execution.png',fullPage:true});
  await page.getByRole('navigation').getByRole('link',{name:'Verified results'}).click();
  await expect(page.locator('.panel .badge').first()).toHaveText('VERIFIED');
  await page.locator('summary').first().click();
  await expect(page.getByText(message,{exact:false}).first()).toBeVisible();
});
