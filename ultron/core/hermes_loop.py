"""Hermes TAO execution loop."""
import json, logging, re, traceback
from ultron.core.hermes_tool import HermesTool
from ultron.core.hermes_prompt import to_hermes_system_prompt
from ultron.core.hermes_trajectory import ExecutionTrajectory
logger = logging.getLogger(__name__)
LT = chr(60)
GT = chr(62)

class HermesExecutionLoop:
    def __init__(self, llm_client, tools, max_turns=20, system_prompt=None):
        self.llm_client = llm_client
        self.tools = {t.name: t for t in tools}
        self.max_turns = max_turns
        self.system_prompt = system_prompt or to_hermes_system_prompt(tools)

    async def run(self, query):
        traj = ExecutionTrajectory(query=query)
        msgs = [{"role":"system","content":self.system_prompt},{"role":"user","content":query}]
        for turn in range(self.max_turns):
            try:
                resp = await self.llm_client.chat(msgs)
                thought, tname, targs = self._parse(resp.content)
                if not tname:
                    traj.final_answer = resp.content
                    traj.status = "success"
                    from datetime import datetime
                    traj.end_time = datetime.now()
                    return traj
                tool = self.tools.get(tname)
                if not tool:
                    err = f"Unknown tool: {tname}"
                    traj.add_step(thought=thought, action=tname, action_input=targs, error=err)
                    msgs.append({"role":"assistant","content":f"Calling {tname}"})
                    msgs.append({"role":"tool","content":f"ERROR: {err}"})
                    continue
                obs, err = await self._exec(tool, targs)
                traj.add_step(thought=thought, action=tname, action_input=targs, observation=obs, error=err)
                msgs.append({"role":"assistant","content":f"Calling {tname}({json.dumps(targs)})"})
                if err:
                    msgs.append({"role":"tool","content":f"ERROR executing {tname}:\n{err}"})
                else:
                    msgs.append({"role":"tool","content":f"Observation from {tname}:\n{obs}"})
            except Exception as e:
                traj.add_step(thought="Unexpected error.", error=str(e))
                logger.error("Hermes error turn %d: %s", turn+1, e)
                msgs.append({"role":"tool","content":f"SYSTEM ERROR: {e}"})
        traj.status = "max_turns"
        from datetime import datetime
        traj.end_time = datetime.now()
        return traj

    @staticmethod
    def _parse(content):
        thought = content
        tname = targs = None
        pat1 = LT + "tool_call" + GT + "(.*?)" + LT + "/tool_call" + GT
        m = re.search(pat1, content, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(1))
                tname = parsed.get("name","")
                targs = parsed.get("arguments",{})
            except (json.JSONDecodeError, AttributeError):
                pass
        if not tname:
            pat2 = chr(96)*3 + "json"
            m2 = re.search(pat2 + "(.*?)" + chr(96)*3, content, re.DOTALL)
            if m2:
                try:
                    parsed = json.loads(m2.group(1).strip())
                    tname = parsed.get("name","")
                    targs = parsed.get("arguments",{})
                except (json.JSONDecodeError, AttributeError):
                    pass
        if not tname:
            pat3 = chr(123) + "[^" + chr(125) + "]*" + chr(125)
            m3 = re.search(pat3, content, re.DOTALL)
            if m3:
                try:
                    parsed = json.loads(m3.group(0))
                    tname = parsed.get("name","")
                    targs = parsed.get("arguments",{})
                except (json.JSONDecodeError, AttributeError):
                    pass
        return thought, tname or None, targs or None

    async def _exec(self, tool, args):
        try:
            if tool.is_async:
                result = await tool.handler(**args)
            else:
                loop = __import__("asyncio").get_event_loop()
                result = await loop.run_in_executor(None, lambda: tool.handler(**args))
            return str(result), None
        except Exception as e:
            tb = traceback.format_exc()
            return None, f"{e}\n{tb}"
