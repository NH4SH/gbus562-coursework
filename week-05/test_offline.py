from pathlib import Path
from types import SimpleNamespace
import unittest

from pipeline import Budget
from specialists import Team, clean, email_body
from supply_mcp_server import HERE, Supply

def risks(s, part, plan):
    return [(r["order_id"],r["units_short"],r["ready_day"],r["days_late"],r["late_penalty"])
            for r in s.check_coverage(part,[{"day":d,"qty":q} for d,q in plan]) if not r["covered"]]

class LocalTests(unittest.TestCase):
    def setUp(self):
        self.c=Supply("copperline-coffee")

    def test_copperline_delay(self):
        self.assertEqual(risks(self.c,"PU-20",[(4,40),(19,160)]),
             [("O-2203",10,19,7,True),("O-2204",20,19,4,False),("O-2205",25,19,2,True)])

    def test_brookfield_lecture_benchmark(self):
        b=Supply("brookfield-bikes")
        self.assertEqual(risks(b,"MC-500",[(5,120),(26,280)]),
             [("O-1043",10,26,12,True),("O-1044",30,26,8,False),("O-1045",50,26,5,False)])

    def test_options_compared_without_comitting(self):
        self.assertEqual([r[0] for r in risks(self.c,"BL-12",[(7,80),(21,120)])],["O-2205"])
        self.assertEqual([r[0] for r in risks(self.c,"BL-12",[(13,200)])],["O-2203"])

    def test_other_messages_do_not_show_customer_risk(self):
        self.assertEqual(risks(self.c,"BR-64",[(13,120)]),[])
        self.assertEqual(risks(self.c,"SW-3",[(11,60)]),[])

    def test_missing_supply_stays_unknown(self):
        self.assertTrue(all(r[2] is None for r in risks(self.c,"PU-20",[])))

    def test_read_four_official_messages(self):
        files=sorted((HERE/"copperline-coffee"/"supplier-emails").glob("*.eml"))
        self.assertEqual(len(files),4)
        self.assertIn("follow 15 days later",email_body(files[0]))
        self.assertIn("No action is needed",email_body(files[3]))

    def test_recipient_guard(self):
        self.assertEqual(clean("O-2203 and ELM State University Dining",
              ["O-2203","Elm State University Dining"]),"[withheld] and [withheld]")

    def test_customer_facts_only(self):
        t=Team("copperline-coffee")
        t.brief={"part_id":"PU-20"}
        f,penalty=t.order_facts({"order_id":"O-2203","ready_day":19})
        self.assertEqual(set(f),{"order_id","customer","product","qty","days_late"})
        self.assertEqual(f["days_late"],7)
        self.assertTrue(penalty)

    def test_budget(self):
        b=Budget("0.05")
        b({"max_tokens":1250})
        b.settle(SimpleNamespace(input_tokens=1000,output_tokens=1000))
        self.assertEqual(str(b.spent),"0.012")
        with self.assertRaises(RuntimeError):
            Budget("0.001")({"max_tokens":1250})

if __name__=="__main__":
    unittest.main()
