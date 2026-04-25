import asyncio
from ultron.core.sandbox import Sandbox

async def test():
    sb = Sandbox()
    code = "import pandas as pd; df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]}); print(df.sum().to_json())"
    result = await sb.execute_python(code)
    print(f"Success: {result.success}")
    print(f"Output: {result.stdout}")
    print(f"Error: {result.stderr}")

if __name__ == "__main__":
    asyncio.run(test())
