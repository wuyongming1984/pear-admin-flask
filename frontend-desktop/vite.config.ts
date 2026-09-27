import {defineConfig} from 'vite';
import vue from '@vitejs/plugin-vue';
export default defineConfig({plugins:[vue()],base:'/static/desktop/',build:{outDir:'../static/desktop',emptyOutDir:true,target:'es2020'},server:{port:5174,proxy:{'/api':'http://127.0.0.1:5050','/uploads':'http://127.0.0.1:5050','/portal':'http://127.0.0.1:5050'}}});
