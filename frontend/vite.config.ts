import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
export default defineConfig({plugins:[vue()],base:'/static/mobile/',build:{outDir:'../static/mobile',emptyOutDir:true,target:'es2020'},server:{proxy:{'/api':'http://127.0.0.1:5050','/uploads':'http://127.0.0.1:5050'}}});
