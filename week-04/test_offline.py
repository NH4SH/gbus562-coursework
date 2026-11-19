"""Offline tests; no Anthropic client or paid API usage."""
import asyncio
from pathlib import Path
import sys
import unittest
from hr_mcp_server import EmployeeDirectory, HERE, build_server
from agent import read_email
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class DirectoryTests(unittest.TestCase):
    def test_ridgeline_schema(self):
        d=EmployeeDirectory(HERE/'ridgeline-hotels')
        self.assertEqual(d.lookup('JENNA.MORALES@ridgelinehotels.example')['balances']['PTO Days Remaining'],'8')
    def test_hartwell_schema(self):
        d=EmployeeDirectory(HERE/'hartwell-hr')
        self.assertEqual(d.lookup('megan.turner@hartwellfoods.example')['balances']['vacation_days_left'],'7')
    def test_unknown(self):
        with self.assertRaisesRegex(ValueError,'Do not state any balance'):
            EmployeeDirectory(HERE/'ridgeline-hotels').lookup('logansmith@example.com')
    def test_all_emails(self):
        for path in (HERE/'ridgeline-hotels'/'sample-emails').glob('*.eml'):
            sender,subject,body=read_email(path)
            self.assertIn('@',sender); self.assertTrue(subject); self.assertTrue(body)

class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def check_server(self,sender,unknown=False):
        p=StdioServerParameters(command=sys.executable,args=[str(HERE/'hr_mcp_server.py'),'--org','ridgeline-hotels','--as-employee',sender])
        async with stdio_client(p) as (r,w), ClientSession(r,w) as s:
            await s.initialize()
            tools=await s.list_tools()
            balance=next(t for t in tools.tools if t.name=='get_leave_balance')
            self.assertFalse(balance.input_schema.get('properties'))
            result=await s.call_tool('get_leave_balance',{})
            self.assertEqual(result.is_error,unknown)
            text=' '.join(getattr(c,'text','') for c in result.content)
            if unknown: self.assertIn('Do not state any balance',text)
            else:
                self.assertIn(sender,text)
                self.assertNotIn('jenna.morales',text)
            # Unexpected selector must not expose requested coworker even if model tries.
            injected=await s.call_tool('get_leave_balance',{'work_email':'jenna.morales@ridgelinehotels.example'})
            self.assertNotIn('jenna.morales',' '.join(getattr(c,'text','') for c in injected.content))
    async def test_sender_isolation(self):
        await self.check_server(read_email(HERE/'ridgeline-hotels/sample-emails/04-tyler-coworker.eml')[0])
    async def test_unknown_error(self):
        await self.check_server(read_email(HERE/'ridgeline-hotels/sample-emails/07-logan-seasonal.eml')[0],True)


# All model calls below are mocks. No credentials or remote requests are used.
import io
import json
import tempfile
from contextlib import redirect_stdout, redirect_stderr
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import agent
import run_ridgeline

class AgentGuardTests(unittest.IsolatedAsyncioTestCase):
    def args(self, shared=None):
        return SimpleNamespace(org='ridgeline-hotels',
            email=HERE/'ridgeline-hotels/sample-emails/01-jenna-pto.eml',
            budget_usd=0.52, shared_budget=shared)
    def client(self):
        client=MagicMock()
        client.__aenter__=AsyncMock(return_value=client)
        client.__aexit__=AsyncMock(return_value=False)
        client.messages.create=AsyncMock(side_effect=RuntimeError('simulated network failure'))
        return client
    async def test_failed_call_keeps_persisted_reservation(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=Path(folder)/'ledger.json'
            shared={'remaining':2.0}
            def record(): ledger.write_text(json.dumps({'remaining':shared['remaining']}))
            shared['record']=record
            client=self.client()
            async def failed_request(**kwargs):
                # Reservation is durable BEFORE the mocked request starts.
                self.assertAlmostEqual(json.loads(ledger.read_text())['remaining'],2-agent.RESERVATION)
                raise RuntimeError('simulated network failure')
            client.messages.create.side_effect=failed_request
            with patch('anthropic.AsyncAnthropic',return_value=client),patch.object(agent,'load_key',return_value='offline-placeholder'),redirect_stdout(io.StringIO()):
                with self.assertRaises(BaseException): await agent.run(self.args(shared))
            client.messages.create.assert_awaited_once()
            self.assertAlmostEqual(shared['remaining'],2-agent.RESERVATION)
            self.assertAlmostEqual(json.loads(ledger.read_text())['remaining'],2-agent.RESERVATION)
    async def test_input_bound_stops_before_model(self):
        client=self.client()
        output=io.StringIO()
        with patch('anthropic.AsyncAnthropic',return_value=client),patch.object(agent,'load_key',return_value='offline-placeholder'),patch.object(agent,'MAX_INPUT_BOUND',1),redirect_stdout(output):
            self.assertEqual(await agent.run(self.args()),1)
        client.messages.create.assert_not_awaited()
        self.assertIn('input-size safety limit reached',output.getvalue())
    async def test_shared_budget_stops_before_model(self):
        client=self.client(); record=MagicMock()
        shared={'remaining':agent.RESERVATION-0.001,'record':record}
        with patch('anthropic.AsyncAnthropic',return_value=client),patch.object(agent,'load_key',return_value='offline-placeholder'),redirect_stdout(io.StringIO()):
            self.assertEqual(await agent.run(self.args(shared)),1)
        client.messages.create.assert_not_awaited(); record.assert_not_called()

class PersistenceTests(unittest.TestCase):
    def test_transcript_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'original.txt';path.write_bytes(b'unchanged evidence\n')
            argv=['agent.py','--email','unused.eml','--save',str(path),'--budget-usd','0.52']
            with patch.object(sys,'argv',argv),patch.object(agent,'run',new_callable=AsyncMock) as mocked,redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught: agent.main()
            self.assertEqual(caught.exception.code,2)
            self.assertEqual(path.read_bytes(),b'unchanged evidence\n');mocked.assert_not_awaited()
    def test_launcher_reuses_prior_ledger(self):
        with tempfile.TemporaryDirectory() as folder:
            here=Path(folder);ledger=here/'.budget-ridgeline.json'
            ledger.write_text(json.dumps({'limit':2.0,'remaining':1.75}))
            async def fake_batch(shared):
                self.assertEqual(shared['remaining'],1.75)
                shared['remaining']-=agent.RESERVATION
                shared['record']()
                return 0
            with patch.object(run_ridgeline,'HERE',here),patch.object(run_ridgeline,'batch',side_effect=fake_batch),patch.object(sys.stdin,'isatty',return_value=True),patch.object(run_ridgeline.getpass,'getpass',return_value='offline-placeholder'),patch.dict(run_ridgeline.os.environ,{},clear=False),redirect_stdout(io.StringIO()):
                self.assertEqual(run_ridgeline.main(),0)
                self.assertNotIn('ANTHROPIC_API_KEY',run_ridgeline.os.environ)
            self.assertAlmostEqual(json.loads(ledger.read_text())['remaining'],1.75-agent.RESERVATION)

if __name__=='__main__': unittest.main()
