import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',use:{baseURL:process.env.SKG_APP_URL??'http://localhost:5173',channel:'chrome',headless:true},workers:1,reporter:'list'});
