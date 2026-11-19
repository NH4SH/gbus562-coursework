#!/usr/bin/env python3
"""Seven genuine model runs with a shared $2 cap; key stays in process memory."""
import asyncio
from contextlib import redirect_stdout
import fcntl
import getpass
import json
import os
import sys
from types import SimpleNamespace
import warnings
from agent import HERE, Tee, run

async def batch(shared):
    runs=HERE/'runs'; runs.mkdir(exist_ok=True)
    for i,email in enumerate(sorted((HERE/'ridgeline-hotels/sample-emails').glob('*.eml')),1):
        path=runs/f'ridgeline-{i:02d}.txt'
        if path.exists():
            print(f'{path.name} already exists; leaving original unchanged.'); continue
        args=SimpleNamespace(org='ridgeline-hotels',email=email,budget_usd=0.52,shared_budget=shared)
        print(f'Running email {i}/7; shared reservation remaining ${shared["remaining"]:.3f}')
        with path.open('x',encoding='utf-8') as f,redirect_stdout(Tee(sys.stdout,f)):
            try: result=await run(args)
            except Exception as exc:
                print(f'Run failed ({type(exc).__name__}); stopped without retries. Human review required.')
                return 1
        if result: return result
    return 0

def main():
    ledger=HERE/'.budget-ridgeline.json'
    with (HERE/'.budget-ridgeline.lock').open('a') as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print('Another batch is running; stopped.'); return 1
        state=json.loads(ledger.read_text()) if ledger.exists() else {'limit':2.0,'remaining':2.0}
        if state.get('limit') != 2.0 or not 0 <= state['remaining'] <= 2.0:
            print('Budget ledger invalid; stopped for review.'); return 1
        shared={'remaining':state['remaining']}
        def record():
            temp=ledger.with_suffix('.tmp')
            with temp.open('w',encoding='utf-8') as f:
                json.dump({'limit':2.0,'remaining':shared['remaining']},f)
                f.flush(); os.fsync(f.fileno())
            temp.replace(ledger)
        shared['record']=record
        print('Seven Ridgeline homework runs. Total API charge ceiling: $2.00.')
        print('Your key is hidden and held only in memory. It will not be saved or printed.')
        if not sys.stdin.isatty():
            print('Run this directly in Terminal for secure hidden key entry.'); return 1
        with warnings.catch_warnings():
            warnings.simplefilter('error',getpass.GetPassWarning)
            key=getpass.getpass('Anthropic API key (hidden): ').strip()
        if not key:
            print('No key entered; stopped.'); return 1
        os.environ['ANTHROPIC_API_KEY']=key
        try: return asyncio.run(batch(shared))
        finally: os.environ.pop('ANTHROPIC_API_KEY',None)

if __name__=='__main__': sys.exit(main())
