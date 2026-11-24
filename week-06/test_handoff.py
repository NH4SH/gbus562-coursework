import asyncio
import csv
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/"capstone"))
from handoff import JobRecords, enforce_date, hold, read_reply

RECORDS=json.loads((HERE.parent/"capstone/records.json").read_text())

class GuardTests(unittest.TestCase):
    def draft(self,date,source):
        return dict(hold("draft"),scope="draft scope",confirmed_date=date,date_source=source)

    def test_valid(self):
        item = self.draft("2027-01-12","P2")
        self.assertEqual(enforce_date(item,RECORDS["PINE"]),item)

    def test_proposal(self):
        self.assertEqual(enforce_date(self.draft("2027-01-18","C2"),RECORDS["CEDAR"]),hold())

    def test_cancellation(self):
        self.assertEqual(enforce_date(self.draft("2027-01-19","E2"),RECORDS["ELM"]),hold())

    def test_other_job(self):
        self.assertEqual(enforce_date(self.draft("2027-01-12","P2"),RECORDS["OAK"]),hold())

    def test_new_proposal_does_not_cancel_booking(self):
        item=self.draft("2027-01-23","A2")
        self.assertEqual(enforce_date(item,RECORDS["ASH"]),item)

    def test_parser_refuses_side_channel(self):
        self.assertEqual(read_reply(json.dumps(dict(hold(), extra="external details"))),hold())

    def test_no_date_after_refusal(self):
        bad=dict(hold("refused"),confirmed_date="2027-01-12",date_source="P2")
        self.assertEqual(enforce_date(bad,RECORDS["PINE"]),hold("refused"))

    def test_case_design(self):
        with (HERE/"test-cases.csv").open() as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(len({row["id"] for row in rows}),8)
        self.assertEqual({row["type"] for row in rows},{"Typical","Edge case","Should refuse","Guardrail"})
        self.assertTrue(all(len(row["expected"].split())>=5 for row in rows))

    def test_actual_mcp_lookup_and_isolation(self):
        async def go():
            async with JobRecords() as client:
                self.assertEqual(await client.get("PINE"),RECORDS["PINE"])
                self.assertEqual(await client.get("UNKNOWN"),[])
        asyncio.run(go())
