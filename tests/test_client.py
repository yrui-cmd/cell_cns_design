import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import client
from ds_png import validate_png_bytes

def png(color='red'):
    output=io.BytesIO()
    Image.new('RGB',(20,16),color).save(output,format='PNG')
    return output.getvalue()

class PNGTests(unittest.TestCase):
    def test_png_dimensions(self):self.assertEqual(validate_png_bytes(png()),{'format':'PNG','width':20,'height':16})
    def test_truncated_stream_with_valid_crc_rejected(self):
        import struct,zlib
        def chunk(t,b):return struct.pack('>I',len(b))+t+b+struct.pack('>I',zlib.crc32(t+b)&0xffffffff)
        data=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',20,16,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0red'))+chunk(b'IEND',b'')
        with self.assertRaises(ValueError):validate_png_bytes(data)

class ClientRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.directory=self.root/'order'
        self.tid='11111111-1111-1111-1111-111111111111'
        class API:
            def me(self):return {'id':'customer','credits_available':20,'credits_per_task':10}
        self.api=API()
        self.args=dict(image=None,text='Research',application='png',thread_id=self.tid,credential_file=self.root/'key',credits_approved=10,wake_authorized=True,api=self.api,registry=self.root/'registry')

    def tearDown(self):self.temp.cleanup()

    def ready(self):
        client.prepare(self.directory,**self.args)
        output=self.directory/'result.png';output.write_bytes(png())
        return client.update(self.directory,state='ready',png=str(output),png_sha256=client.sha(png()))

    def test_invalid_inputs_have_no_registered_order(self):
        for changes in ({'text':''},{'image':self.root/'image.png'},{'credits_approved':45},{'wake_authorized':False}):
            with self.assertRaises(client.ClientError):client.prepare(self.directory,**{**self.args,**changes})
        self.assertFalse((self.directory/'job.json').exists());self.assertFalse((self.root/'registry/registry.json').exists())

    def test_reusing_directory_does_not_change_request(self):
        first=client.prepare(self.directory,**self.args);second=client.prepare(self.directory,**self.args)
        self.assertEqual(first['request_id'],second['request_id'])
        with self.assertRaises(client.ClientError):client.prepare(self.directory,**{**self.args,'text':'changed'})

    def test_cross_service_directory_is_rejected(self):
        self.ready();state=client.read_job(self.directory);state['service']='/api/figure_pro';client.write(self.directory/'job.json',state)
        with self.assertRaises(client.ClientError):client.read_job(self.directory)

    def test_ambiguous_wake_does_not_send_twice(self):
        self.ready();sent=[];tid=self.tid
        class Bridge:
            def __init__(self,**kwargs):pass
            def _desktop_tool(self,*args):return {'thread':{'id':tid,'status':{'type':'idle'}},'turns':[]}
            def submit(self,*args):sent.append(args);raise TimeoutError()
            def close(self):pass
        result=client.notify(self.directory,Bridge);self.assertEqual(result['state'],'wake_uncertain')
        client.notify(self.directory,Bridge);self.assertEqual(len(sent),1)

    def test_busy_original_chat_is_not_interrupted(self):
        self.ready();tid=self.tid
        class Bridge:
            def __init__(self,**kwargs):pass
            def _desktop_tool(self,*args):return {'thread':{'id':tid,'status':{'type':'active'}},'turns':[]}
            def submit(self,*args):raise AssertionError('Should not send while active')
            def close(self):pass
        self.assertEqual(client.notify(self.directory,Bridge)['state'],'ready')

    def test_acknowledge_only_original_chat_nonce(self):
        state=self.ready()
        with patch.dict(os.environ,{'CODEX_THREAD_ID':self.tid}):
            with self.assertRaises(client.ClientError):client.acknowledge(self.directory,'wrong')
            self.assertEqual(client.acknowledge(self.directory,state['wake_nonce'])['state'],'received')

    def test_existing_png_resume_does_not_submit(self):
        self.ready()
        with patch.dict(os.environ,{'CODEX_THREAD_ID':self.tid}):
            self.assertEqual(client.resume_job(self.directory)['next_action'],'deliver_existing_png')


if __name__=='__main__':unittest.main()
