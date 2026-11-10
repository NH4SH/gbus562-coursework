"""Offline tests. Mock responses exist only in temporary unit-test directories."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent))
import ask


class ParsingTests(unittest.TestCase):
    def test_html_structure_preserves_version_and_entire_section(self):
        sections = ask.html_sections(ask.HERE / 'larkfield-docs/consumer-fee-schedule.html')
        section = next(s for s in sections if s.heading == 'Overdraft and returned item fees')
        self.assertIn('Version 8', section.info)
        body = ' '.join(section.paragraphs)
        for text in ['$29', 'three', '$10 or less', 'linked savings account is free']:
            self.assertIn(text, body)
        self.assertNotIn('background:', body)

    def test_pdf_all_seven_sections_and_final_sentence(self):
        sections = ask.pdf_sections(ask.HERE / 'copperline-docs/vendor-payment-terms.pdf')
        self.assertEqual(len(sections), 7)
        self.assertEqual(sections[-1].heading, 'Vendor questions about payments')
        self.assertIn('promising a payment date themselves.', sections[-1].paragraphs[0])
        bank = next(s for s in sections if s.heading == "Requests to change a vendor's bank details")
        self.assertIn('second review by another Accounts Payable team member.', bank.paragraphs[0])
        self.assertTrue(all(s.page == 1 for s in sections))

    def test_html_table_rows_retain_column_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'policy.html'
            p.write_text('<main><h1>Policy</h1><h2>Fees</h2><table><tr><th>Item</th><th>Fee</th></tr><tr><td>Wire</td><td>$45</td></tr></table></main>')
            sections = ask.html_sections(p)
            self.assertEqual(sections[0].paragraphs, ('Item: Wire; Fee: $45',))

    def test_archive_not_recursed(self):
        files = ask.document_files(ask.HERE / 'copperline-docs')
        self.assertEqual(len(files), 5)
        self.assertFalse(any('v3-2' in p.name for p in files))

    def test_unhandled_type_fails_loudly(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory)/'data.xlsx').write_text('not a workbook')
            with self.assertRaisesRegex(ValueError, 'Unsupported'):
                ask.document_files(Path(directory))

    def test_fingerprint_changes_on_content_not_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'one.txt'; p.write_text('first')
            a = ask.fingerprint([p]); p.touch()
            self.assertEqual(a, ask.fingerprint([p]))
            p.write_text('second')
            self.assertNotEqual(a, ask.fingerprint([p]))

    def test_chunk_labels_repeated_and_sentence_boundaries_kept(self):
        section = ask.Section('Title','Heading','file.txt','Version 1',
            tuple(f'Sentence {i} contains an intact thought.' for i in range(80)))
        chunks = ask.make_chunks(section, lambda text: len(text.split())*2)
        self.assertGreater(len(chunks),1)
        for chunk in chunks:
            self.assertTrue(chunk['text'].startswith('Title | Heading\nSource: file.txt'))
            self.assertLessEqual(chunk['metadata']['tokens'],256)
            self.assertLessEqual(chunk['metadata']['words'],190)
            self.assertTrue(chunk['text'].endswith('.'))
        for i in range(80):
            self.assertEqual(sum(f'Sentence {i} contains an intact thought.' in x['text'] for x in chunks),1)

    def test_oversized_sentence_fails_not_truncates(self):
        section = ask.Section('Title','Heading','file.txt','',('word '*400,))
        with self.assertRaisesRegex(ValueError,'too long'):
            ask.make_chunks(section, lambda text:len(text.split()))

    def test_source_list_empty_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'No supported'):
                ask.document_files(Path(directory))


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.results = [{'rank':1,'similarity':0.625,'source':'test-source.txt',
            'text':'Test title | Test section\nSource: test-source.txt\n\n'+'Unedited content. '*20,
            'metadata':{'source':'test-source.txt'}}]

    def test_preview_and_export_differ_only_in_chunk_length(self):
        full = ask.render_retrieval('Unit-test question',self.results)
        preview = ask.render_retrieval('Unit-test question',self.results,True)
        self.assertIn(self.results[0]['text'],full)
        self.assertNotIn(self.results[0]['text'],preview)
        self.assertIn('Rank: 1 | Similarity: 0.625000 | Source: test-source.txt',full)
        self.assertEqual(len(preview.splitlines()[-1]),150)

    def test_missing_key_fails_without_index_or_api(self):
        with patch.dict('os.environ',{},clear=True), patch.object(ask,'REPO',Path('/nonexistent/course/repo')), patch.object(ask,'prepare_collection') as build, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(ask.main(['Unit-test question']),1)
            build.assert_not_called()

    def test_no_fake_run_exports_from_retrieval_only(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                ask.main(['Unit-test question','--retrieve-only','--save','do-not-create.txt'])
        self.assertFalse(Path('do-not-create.txt').exists())

    def test_existing_export_refused_before_api(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'run.txt';p.write_text('preserve me')
            with patch.object(ask,'load_api_key') as key, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    ask.main(['Unit-test question','--save',str(p)])
                key.assert_not_called()
            self.assertEqual(p.read_text(),'preserve me')

    def test_mock_response_saved_byte_exact_and_audited(self):
        from types import SimpleNamespace
        text='UNIT TEST ONLY: explicitly mocked response.\nNo API call was made.'
        response=SimpleNamespace(content=[SimpleNamespace(type='text',text=text)],stop_reason='end_turn',
            model_dump=lambda **kw:{'model':ask.MODEL,'id':'unit-test-fake-id','stop_reason':'end_turn','content':[{'type':'text','text':text}]})
        client=Mock();client.messages.create.return_value=response
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'mock-only.txt'
            with patch.object(ask,'load_api_key',return_value='unit-test-not-a-real-key'), patch.object(ask,'prepare_collection',return_value=(Mock(),'test-corpus-hash',Path(directory))), patch.object(ask,'retrieve',return_value=self.results), patch('anthropic.Anthropic',return_value=client), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ask.main(['Unit-test question','--save',str(p)]),0)
            expected=ask.render_retrieval('Unit-test question',self.results)+'\n\nANSWER\n'+text
            self.assertEqual(p.read_bytes(),expected.encode())
            audit=json.loads(p.with_suffix('.audit.json').read_text())
            self.assertEqual(audit['export_sha256'],hashlib.sha256(p.read_bytes()).hexdigest())
            self.assertNotIn('unit-test-not-a-real-key',p.with_suffix('.audit.json').read_text())
            request=client.messages.create.call_args.kwargs
            self.assertEqual(request['model'],'claude-sonnet-5')
            self.assertEqual(request['thinking'],{'type':'disabled'})
            self.assertEqual(request['max_tokens'],1200)
            for unsupported in ['temperature','top_p','top_k']:
                self.assertNotIn(unsupported,request)

    def test_api_error_detail_redacts_credentials(self):
        class OfflineError(Exception):
            status_code=400
            body={'error':{'message':'Unsupported setting; credential sk-ant-unit-test-not-real'}}
        client=Mock();client.messages.create.side_effect=OfflineError()
        error=io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(ask,'load_api_key',return_value='sk-ant-unit-test-not-real'), patch.object(ask,'prepare_collection',return_value=(Mock(),'test-corpus-hash',Path(directory))), patch.object(ask,'retrieve',return_value=self.results), patch('anthropic.Anthropic',return_value=client), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(error):
                self.assertEqual(ask.main(['Unit-test question']),1)
        self.assertIn('Unsupported setting',error.getvalue())
        self.assertIn('[REDACTED]',error.getvalue())
        self.assertNotIn('sk-ant-unit-test-not-real',error.getvalue())


class RebuildSafetyTests(unittest.TestCase):
    def test_failed_rebuild_keeps_old_manifest_and_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);docs=root/'documents';docs.mkdir()
            (docs/'source.txt').write_text('A brief source paragraph.')
            corpus_hash=ask.fingerprint(ask.document_files(docs))
            folder_id=hashlib.sha256(str(docs.resolve()).encode()).hexdigest()[:12]
            db=root/'.chroma'/f'{docs.name}-{folder_id}';db.mkdir(parents=True)
            manifest=db/'manifest.json'
            before=json.dumps({'fingerprint':corpus_hash,'chunks':1,'collection':'old-good'})
            manifest.write_text(before)
            old=Mock();old.count.return_value=1
            new=Mock();new.add.side_effect=RuntimeError('injected offline build failure')
            client=Mock();client.create_collection.return_value=new;client.get_collection.return_value=old
            with patch.object(ask,'HERE',root), patch.object(ask,'embedding_and_counter',return_value=(Mock(),lambda text:len(text.split()))), patch('chromadb.PersistentClient',return_value=client):
                with self.assertRaisesRegex(RuntimeError,'injected'):
                    ask.prepare_collection(docs,True)
                self.assertEqual(manifest.read_text(),before)
                self.assertIs(ask.prepare_collection(docs,False)[0],old)
                client.delete_collection.assert_not_called()

    def test_stale_collection_rejected_before_embedding(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);docs=root/'documents';docs.mkdir()
            (docs/'source.txt').write_text('A new source paragraph.')
            folder_id=hashlib.sha256(str(docs.resolve()).encode()).hexdigest()[:12]
            db=root/'.chroma'/f'{docs.name}-{folder_id}';db.mkdir(parents=True)
            (db/'manifest.json').write_text(json.dumps({'fingerprint':'outdated','chunks':1}))
            with patch.object(ask,'HERE',root), patch.object(ask,'embedding_and_counter') as embed:
                with self.assertRaisesRegex(ValueError,'Documents changed'):
                    ask.prepare_collection(docs,False)
                embed.assert_not_called()


if __name__=='__main__':
    unittest.main(verbosity=2)
