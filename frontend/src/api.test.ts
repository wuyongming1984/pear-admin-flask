// @vitest-environment jsdom
import {it,expect,vi,afterEach} from 'vitest';
import {request,bindAccessToken} from './api';
afterEach(()=>vi.unstubAllGlobals());
it('does not retry uncertain POSTs and marks server errors uncertain',async()=>{
 const fetcher=vi.fn().mockResolvedValue(new Response(JSON.stringify({message:'failed'}),{status:500}));vi.stubGlobal('fetch',fetcher);
 await expect(request('/pay/',{method:'POST',body:'{}'})).rejects.toMatchObject({uncertain:true});expect(fetcher).toHaveBeenCalledTimes(1);
});
it('blocks a write after another tab changes the account token',async()=>{
 const fetcher=vi.fn();vi.stubGlobal('fetch',fetcher);bindAccessToken(null);localStorage.setItem('access_token','changed-account');
 try{await expect(request('/supplier/1',{method:'PUT',body:'{}'})).rejects.toThrow('账号已在其他页面改变');expect(fetcher).not.toHaveBeenCalled()}finally{localStorage.removeItem('access_token');bindAccessToken(null)}
});
it('keeps supplier sync response and rejects success:false',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({code:1001,data:{related_orders:[{id:4}]},msg:'需要确认'}))));
 await expect(request('/supplier/1',{method:'PUT',body:'{}'})).rejects.toMatchObject({response:{code:1001,data:{related_orders:[{id:4}]}}});
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({success:false,msg:'失败'}))));await expect(request('/nursery/inbound',{method:'POST',body:'{}'})).rejects.toThrow('失败');
});
it('public supplier links need no JWT and do not expire the employee session',async()=>{
 const listener=vi.fn();window.addEventListener('sf-auth-expired',listener);const fetcher=vi.fn().mockResolvedValue(new Response(JSON.stringify({msg:'链接无效'}),{status:401}));vi.stubGlobal('fetch',fetcher);
 await expect(request('/portal/reconcile/example/data')).rejects.toThrow('链接无效');expect(fetcher.mock.calls[0][0]).toBe('/portal/reconcile/example/data');expect(fetcher.mock.calls[0][1].headers.has('Authorization')).toBe(false);expect(listener).not.toHaveBeenCalled();window.removeEventListener('sf-auth-expired',listener);
});
it('announces expired authentication without retrying writes',async()=>{
 const listener=vi.fn();window.addEventListener('sf-auth-expired',listener);
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({msg:'Token expired'}),{status:401})));
 await expect(request('/project/1',{method:'PUT',body:'{}'})).rejects.toMatchObject({status:401,uncertain:false});expect(listener).toHaveBeenCalledOnce();window.removeEventListener('sf-auth-expired',listener);
});
