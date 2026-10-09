import hashlib
import io
import os
from PIL import Image
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import progress_panel as p


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = {'created_at':1000, 'updated_at':1000, 'state':'waiting',
                      'credential_file':'DO_NOT_EXPOSE', 'text':'PRIVATE_INPUT',
                      'service':'/api/cell_figure_ds', 'credits_approved':10, 'application':'png'}
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        (self.root/'job.json').write_text(json.dumps(self.state), encoding='utf-8')

    def complete(self):
        output=io.BytesIO();Image.new('RGB',(20,16),'red').save(output,format='PNG');data=output.getvalue()
        (self.root/'result.png').write_bytes(data)
        self.state.update(png=str(self.root/'result.png'), png_sha256=hashlib.sha256(data).hexdigest(),
                          result_received_at=1100, state='ready')
        self.save()

    def test_opens_once_in_original_chat_without_sending_messages(self):
        self.state['thread_id']='origin-chat';self.save()
        url='http://127.0.0.1:12345/'+'a'*48+'/'
        (self.root/'progress-panel.json').write_text(json.dumps({'url':url}),encoding='utf-8')
        outer=self
        class Bridge:
            calls=[]
            def __init__(self,**kwargs):
                outer.assertEqual(kwargs,dict(caller_thread_id='origin-chat',submit_thread_ids=[],panel_url=url))
            def _desktop_tool(self,tool,args):
                self.calls.append(tool)
                outer.assertEqual(tool,'open_in_codex')
                outer.assertEqual(args,dict(placement='right',target=dict(type='browser',url=url)))
                return dict(status='queued',threadId='origin-chat')
            def close(self):pass
        with patch.object(p,'start',return_value=url), patch.dict(os.environ,{'CODEX_THREAD_ID':'origin-chat'}):
            self.assertTrue(p.show(self.root,bridge_factory=Bridge)['progress_opened'])
            self.assertTrue(p.show(self.root,bridge_factory=Bridge)['progress_opened'])
        self.assertEqual(Bridge.calls,['open_in_codex'])

    def test_bridge_rejects_other_urls_and_threads(self):
        from desktop_bridge import Bridge
        bridge=Bridge.__new__(Bridge)
        bridge.caller_thread_id='origin-chat'
        bridge.panel_url='http://127.0.0.1:12345/'+'a'*48+'/'
        good={'placement':'right','target':{'type':'browser','url':bridge.panel_url}}
        for thread,args in [('other-chat',good),('origin-chat',{'placement':'right','target':{'type':'browser','url':'https://example.org'}})]:
            with self.assertRaises(ValueError):
                bridge.call('tools/call',dict(namespace='codex_app',tool='open_in_codex',threadId=thread,arguments=args))

    def test_estimate_caps_at_99_even_after_ten_minutes(self):
        self.assertEqual(p.snapshot(self.root,now=1000)['percent'],0)
        self.assertEqual(p.snapshot(self.root,now=1300)['percent'],50)
        self.assertEqual(p.snapshot(self.root,now=1600)['percent'],99)
        self.assertEqual(p.snapshot(self.root,now=90000)['percent'],99)

    def test_remote_completion_without_local_file_is_not_100(self):
        self.state.update(remote_status='completed',state='ready')
        self.save()
        self.assertFalse(p.snapshot(self.root,now=90000)['complete'])

    def test_only_verified_local_result_finishes_early(self):
        self.complete()
        snapshot=p.snapshot(self.root,now=1200)
        self.assertEqual(snapshot['percent'],100)
        self.assertEqual(snapshot['elapsed'],100)
        (self.root/'result.png').write_bytes(b'corrupted')
        self.assertFalse(p.snapshot(self.root,now=1200)['complete'])

    def test_pause_and_attention_never_mean_complete(self):
        for state in ['stopped','attention','wake_uncertain']:
            self.state['state']=state;self.save()
            self.assertFalse(p.snapshot(self.root,now=90000)['complete'])

    def test_local_http_receives_state_changes_without_any_remote_calls(self):
        server=p.make_server(self.root,'test-capability')
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}/test-capability/'
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(base+'status') as response:
                before=json.load(response)
                self.assertEqual(response.headers['Cache-Control'],'no-store')
            self.assertFalse(before['complete'])
            self.assertNotIn('DO_NOT_EXPOSE',json.dumps(before))
            self.assertNotIn('PRIVATE_INPUT',json.dumps(before))
            self.complete()
            with opener.open(base+'status') as response:
                self.assertEqual(json.load(response)['percent'],100)
            with self.assertRaises(urllib.error.HTTPError) as caught:
                opener.open(base.replace('test-capability','wrong')+'status')
            self.assertEqual(caught.exception.code,404)
            request=urllib.request.Request(base+'status',headers={'Host':'example.org'})
            with self.assertRaises(urllib.error.HTTPError) as caught:opener.open(request)
            self.assertEqual(caught.exception.code,403)
        finally:
            server.shutdown();server.server_close();thread.join()



    def test_invalid_png_cannot_complete_even_with_matching_hash(self):
        data=b'not a png'
        (self.root/'result.png').write_bytes(data)
        self.state.update(png=str(self.root/'result.png'),png_sha256=hashlib.sha256(data).hexdigest())
        self.save()
        self.assertFalse(p.snapshot(self.root)['complete'])

    def test_other_service_and_other_chat_rejected(self):
        import client
        self.state.update(service='/api/figure_pro',thread_id='origin-chat');self.save()
        with self.assertRaises(client.ClientError):p.snapshot(self.root)
        self.state['service']='/api/cell_figure_ds';self.save()
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'another-chat'}), patch.object(p,'start') as start:
            with self.assertRaises(client.ClientError):p.show(self.root)
            start.assert_not_called()

    def test_submit_opens_panel_and_panel_failure_does_not_fail_order(self):
        import client
        from contextlib import ExitStack, redirect_stdout
        (self.root/'input.txt').write_text('Research',encoding='utf-8')
        args=['client.py','submit','--text-file',str(self.root/'input.txt'),'--job-dir',str(self.root),'--credits-approved','10','--authorize-wake']
        self.state.update(thread_id='origin-chat',charged_credits=10);self.save()
        for fails in (False,True):
            with ExitStack() as stack:
                stack.enter_context(patch.object(sys,'argv',args))
                stack.enter_context(patch.object(client,'install_recovery'))
                stack.enter_context(patch.object(client,'prepare',return_value=self.state))
                stack.enter_context(patch.object(client,'register'))
                submit=stack.enter_context(patch.object(client,'submit_existing',return_value=self.state))
                waiter=stack.enter_context(patch.object(client,'start_waiter'))
                stack.enter_context(patch.object(client,'check_waiter',return_value=True))
                show=stack.enter_context(patch.object(p,'show',side_effect=RuntimeError('offline') if fails else None,return_value={'progress_opened':True}))
                output=io.StringIO()
                with redirect_stdout(output):self.assertEqual(client.main(),0)
                result=json.loads(output.getvalue())
                self.assertEqual(result['charged_credits'],10)
                self.assertTrue(result['background_waiter_verified'])
                self.assertIn('progress_error' if fails else 'progress_opened',result)
                submit.assert_called_once();waiter.assert_called_once();show.assert_called_once()

    def test_recovery_keeps_waiter_when_panel_fails_without_reopening_ui(self):
        import client
        self.state['wake_state']='pending';self.save()
        (self.root/'registry.json').write_text(json.dumps([str(self.root)]),encoding='utf-8')
        (self.root/'progress-panel.json').write_text('{}',encoding='utf-8')
        with patch.object(client,'start_waiter') as waiter, patch.object(p,'start',side_effect=RuntimeError()), patch.object(p,'show') as show:
            self.assertEqual(client.recover(self.root)['checked_pending'],1)
            waiter.assert_called_once();show.assert_not_called()

if __name__=='__main__':unittest.main()
