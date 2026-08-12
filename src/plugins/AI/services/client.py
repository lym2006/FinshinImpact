import json
import httpx

from ..config import API_KEY,TEMPERATURE,MODEL_NAME

headers={
    "Authorization":f"Bearer {API_KEY}",
    "Content-Type":"application/json",
}

class BaseClient:
    def __init__(self,base_url,headers):
        self.base_url=base_url
        self.headers=headers

    async def __aenter__(self):
        self.client=httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=90.0
        )
        return self
    
    async def __aexit__(self,_exc_type,_exc_val,_exc_tb):
        if self.client:
            await self.client.aclose()

    async def close(self):
        await self.client.aclose()

    async def get(self,url:str,**kwargs):
        return await self.client.get(url,**kwargs)
    
    def stream(self,method:str,url:str,**kwargs):
        return self.client.stream(method,url,**kwargs)

class ChatClient(BaseClient):
    def __init__(self):
        base_url="https://api.siliconflow.cn/v1"
        super().__init__(base_url,headers)

    async def stream_chat(self,msg:list):
        payload={
            "model":MODEL_NAME,
            "messages":msg,
            "stream":True,
            "temperature":TEMPERATURE,
        }
        async with self.stream("POST","/chat/completions",json=payload) as response:
            if (code:=response.status_code)!=200:
                raise Exception(f"错误码{code}")
            async for chunk in response.aiter_lines():
                if chunk.startswith("data: "):
                    try:
                        data=json.loads(chunk[6:])
                        data=data["choices"][0]["delta"]
                        yield data
                    except (json.JSONDecodeError,KeyError,IndexError):
                        continue