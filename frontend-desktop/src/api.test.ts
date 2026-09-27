// @vitest-environment jsdom
import{beforeEach,afterEach,describe,it,expect,vi}from'vitest';import{request,allRows,ApiError}from'./api';
beforeEach(()=>{localStorage.clear();vi.stubGlobal('fetch',vi.fn())});afterEach(()=>vi.unstubAllGlobals());
const result=(data:any,status=200)=>Promise.resolve(new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}}));
describe('desktop API',()=>{
it('preserves decimal payload and performs no write retry',async()=>{vi.mocked(fetch).mockRejectedValue(new Error('offline'));await expect(request('/pay/',{method:'POST',body:JSON.stringify({current_payment_amount:'100.01'})})).rejects.toMatchObject({uncertain:true});expect(fetch).toHaveBeenCalledTimes(1);expect(vi.mocked(fetch).mock.calls[0][1]?.body).toContain('"100.01"')});
it('rejects legacy business failure and preserves error detail',async()=>{vi.mocked(fetch).mockImplementation(()=>result({success:false,msg:'重复'}));await expect(request('/dictionary/')).rejects.toThrow('重复');vi.mocked(fetch).mockImplementation(()=>result({code:1001,msg:'关联变更',data:{orders:4}}));try{await request('/supplier/')}catch(e){expect((e as ApiError).code).toBe(1001);expect((e as ApiError).data.orders).toBe(4)}});
it('dispatches expiry without deleting local form state',async()=>{const cb=vi.fn();window.addEventListener('sf-auth-expired',cb);vi.mocked(fetch).mockImplementation(()=>result({code:-1,msg:'token 已过期，请重新登录'},403));await expect(request('/project/')).rejects.toThrow();expect(cb).toHaveBeenCalledOnce();window.removeEventListener('sf-auth-expired',cb)});
it('loads beyond default limit and rejects repeating pages',async()=>{vi.mocked(fetch).mockResolvedValueOnce(await result({code:0,count:2,data:[{id:1}]})).mockResolvedValueOnce(await result({code:0,count:2,data:[{id:2}]}));expect(await allRows('/user/')).toHaveLength(2);vi.mocked(fetch).mockImplementation(()=>result({code:0,count:4,data:[{id:1}]}));await expect(allRows('/user/')).rejects.toThrow('分页未推进')});
});
