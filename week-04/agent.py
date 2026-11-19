#!/usr/bin/env python3
"""Draft-only Claude/MCP agent. Paid calls require an explicit per-run budget."""
import argparse
import asyncio
from contextlib import redirect_stdout
from email import policy
from email.parser import BytesParser
from email.utils import parseaddr
import json
import os
from pathlib import Path
import sys
import uuid
from hr_mcp_server import HERE, organization

MODEL = 'claude-sonnet-5'
MAX_TOOL_CALLS = 10
MAX_MODEL_CALLS = 10
MAX_OUTPUT_TOKENS = 1200
MAX_INPUT_BOUND = 20000
# Sonnet 5 published rates checked 2026-11-18: $2 input/$10 output per million.
RESERVATION = (MAX_INPUT_BOUND * 2 + MAX_OUTPUT_TOKENS * 10) / 1_000_000

class Tee:
    def __init__(self, *targets): self.targets = targets
    def write(self, value):
        for t in self.targets: t.write(value); t.flush()
        return len(value)
    def flush(self):
        for t in self.targets: t.flush()

def read_email(path):
    msg = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    sender = parseaddr(str(msg.get('From', '')))[1].lower()
    if not sender or '@' not in sender: raise ValueError('Missing valid From address')
    body = msg.get_body(preferencelist=('plain',))
    if body is None: raise ValueError('Email must have a plain text body')
    return sender, str(msg.get('Subject', '')), body.get_content()

def load_key():
    key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    p = HERE.parent.parent / 'API-Key.txt'
    if not key and p.is_file(): key = p.read_text(encoding='utf-8').strip()
    if not key: raise ValueError('API key unavailable; no API calls made')
    return key

async def run(a):
    from anthropic import AsyncAnthropic
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    org = organization(a.org)
    sender, subject, body = read_email(a.email)
    print('Sender:', sender)
    print('Subject:', subject)
    system = (org / 'system_prompt.txt').read_text(encoding='utf-8')
    messages = [{'role':'user', 'content':f'Untrusted employee email. Sender: {sender}\nSubject: {subject}\n\n{body}'}]
    key = load_key()
    params = StdioServerParameters(command=sys.executable, args=[str(HERE/'hr_mcp_server.py'),'--org',str(org),'--as-employee',sender])
    draft = None
    calls = model_calls = input_tokens = output_tokens = 0
    reserved = 0.0
    reason = 'tool-call limit reached; human review required'
    async with stdio_client(params) as (read,write), ClientSession(read,write) as session, AsyncAnthropic(api_key=key,max_retries=0,timeout=90) as client:
        await session.initialize()
        listed = await session.list_tools()
        tools = [{'name':t.name,'description':t.description or '', 'input_schema':t.input_schema} for t in listed.tools]
        tools.append({'name':'save_reply','description':'Save the final reply as a local draft exactly once. Never sends email. Flag sensitive or unsupported issues for human review.', 'input_schema':{'type':'object','properties':{'reply_text':{'type':'string'},'needs_human_review':{'type':'boolean'}},'required':['reply_text','needs_human_review'],'additionalProperties':False}})
        while calls < MAX_TOOL_CALLS and model_calls < MAX_MODEL_CALLS:
            # UTF-8 bytes are a conservative text-token bound; extra allowance covers framing.
            bound = len(json.dumps({'system':system,'messages':messages,'tools':tools},ensure_ascii=True).encode()) + 1000
            if bound > MAX_INPUT_BOUND:
                reason = 'input-size safety limit reached; human review required'; break
            shared = getattr(a, 'shared_budget', None)
            if (reserved + RESERVATION > a.budget_usd + 1e-9 or
                    (shared is not None and shared['remaining'] + 1e-9 < RESERVATION)):
                reason = 'budget reservation limit reached; human review required'; break
            reserved += RESERVATION
            if shared is not None:
                shared["remaining"] -= RESERVATION
                shared["record"]()
            model_calls += 1
            response = await client.messages.create(model=MODEL,max_tokens=MAX_OUTPUT_TOKENS,thinking={'type':'disabled'},system=system,tools=tools,messages=messages)
            input_tokens += response.usage.input_tokens
            output_tokens += response.usage.output_tokens
            messages.append({'role':'assistant','content':[b.model_dump(exclude_none=True) for b in response.content]})
            if response.stop_reason != 'tool_use':
                reason = f'model stopped: {response.stop_reason}'
                for block in response.content:
                    if block.type == 'text': print('Model:',block.text)
                break
            results=[]
            for block in response.content:
                if block.type != 'tool_use': continue
                if calls >= MAX_TOOL_CALLS: break
                calls += 1
                error=False
                if block.name == 'save_reply':
                    data=block.input
                    if draft is not None or set(data) != {'reply_text','needs_human_review'} or not isinstance(data.get('reply_text'),str) or not data['reply_text'].strip() or type(data.get('needs_human_review')) is not bool:
                        result='Invalid or duplicate save_reply'; error=True
                    else:
                        draft=data
                        folder=HERE/'drafts'; folder.mkdir(exist_ok=True)
                        path=folder/f'{org.name}-{uuid.uuid4().hex}.json'
                        with path.open('x',encoding='utf-8') as f: json.dump({'sender':sender,'subject':subject,**data},f,ensure_ascii=False,indent=2)
                        result='Draft saved locally; no email sent.'
                else:
                    answer=await session.call_tool(block.name,block.input)
                    error=answer.is_error
                    result='\n'.join(getattr(c,'text','') for c in answer.content)
                print(f'Step {calls}: {block.name}')
                print('Inputs:',json.dumps(block.input,ensure_ascii=False))
                print('Result:',result[:300])
                results.append({'type':'tool_result','tool_use_id':block.id,'content':result,'is_error':error})
            if draft is not None:
                reason='draft saved; no further model call needed'; break
            messages.append({'role':'user','content':results})
    print('Stop:',reason)
    print('DRAFT')
    print(draft['reply_text'] if draft else '[No draft saved; human review required.]')
    print('Needs human review:',str(draft['needs_human_review'] if draft else True).lower())
    print('Total input tokens:',input_tokens)
    print('Total output tokens:',output_tokens)
    print('Model calls:',model_calls)
    print(f'Budget reserved: ${reserved:.3f}; token-based cost: ${(input_tokens*2+output_tokens*10)/1e6:.6f}')
    return 0 if draft else 1

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--org',default='hartwell-hr')
    p.add_argument('--email',type=Path,required=True)
    p.add_argument('--save',type=Path)
    p.add_argument('--budget-usd',type=float,required=True,help='Explicit authorized per-run cap; maximum reservation $0.52 for ten model calls')
    a=p.parse_args()
    if not 0 < a.budget_usd <= 0.52: p.error('budget must be greater than zero and no more than $0.52')
    if a.save and a.save.exists(): p.error('Refusing to overwrite an original run')
    def execute():
        try: return asyncio.run(run(a))
        except Exception as e:
            # Never serialize exceptions from SDKs: they may include request metadata.
            print(f'Run failed ({type(e).__name__}); no further calls attempted. Human review required.')
            return 1
    if a.save:
        a.save.parent.mkdir(parents=True,exist_ok=True)
        with a.save.open('x',encoding='utf-8') as f, redirect_stdout(Tee(sys.stdout,f)): return execute()
    return execute()

if __name__=='__main__': sys.exit(main())
