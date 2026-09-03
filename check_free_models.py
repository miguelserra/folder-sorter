#%%
from openai import OpenAI
from config import API_KEY, BASE_URL
c = OpenAI(base_url=BASE_URL, api_key=API_KEY)
print("\n".join(sorted(m.id for m in c.models.list().data if ":free" in m.id)))
# %%
