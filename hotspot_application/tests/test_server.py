import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('hotspot_server', Path(__file__).resolve().parents[1] / 'serve.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class ConnectorTests(unittest.TestCase):
    def setUp(self):
        self.query = {'key': 'a' * 32, 'source': 'VIIRS_SNPP_NRT', 'days': 3, 'area': 'world', 'date': '2026-01-01'}

    def test_world_query_and_explicit_start_date(self):
        self.assertTrue(server.firms_url(self.query).endswith('/VIIRS_SNPP_NRT/world/3/2026-01-01'))
        self.query['date'] = ''
        self.assertTrue(server.firms_url(self.query).endswith('/world/3'))

    def test_product_and_bounds_validation(self):
        for patch_data in [{'source':'invalid'},{'area':'120,-5,100,5'},{'area':'-181,-5,100,5'},{'area':'nan,-5,100,5'},{'days':6},{'days':True},{'key':'secret/path'}]:
            with self.subTest(patch_data=patch_data), self.assertRaises(ValueError):
                server.firms_url(dict(self.query, **patch_data))

    def test_global_bounding_box_supported(self):
        self.query['area'] = '-130,30,-110,60'
        self.assertIn('/-130,30,-110,60/',server.firms_url(self.query))

    def test_availability_uses_product_not_dates(self):
        self.assertTrue(server.firms_url(self.query,availability=True).endswith('/'+'a'*32+'/VIIRS_SNPP_NRT'))

    def test_local_model_endpoints(self):
        self.assertEqual(server.llm_url({'provider':'ollama','endpoint':'http://localhost:11434'}),'http://localhost:11434/api/chat')
        self.assertEqual(server.llm_url({'provider':'local','endpoint':'http://127.0.0.1:1234/v1'}),'http://127.0.0.1:1234/v1/chat/completions')
        for provider, endpoint in [('local','http://192.168.1.1'),('ollama','file:///secret'),('hosted','http://example.com'),('hosted','https://user:password@example.com')]:
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                server.llm_url({'provider':provider,'endpoint':endpoint})

    @patch.object(server, 'fetch')
    def test_ollama_request_and_response(self, fetch):
        fetch.return_value = json.dumps({'message':{'content':'A study response'}})
        response = server.chat({'provider':'ollama','endpoint':'http://localhost:11434','model':'local-test','messages':[{'role':'user','content':'Summarize'}]})
        self.assertEqual(response, {'reply':'A study response'})
        self.assertEqual(fetch.call_args.args[1]['stream'],False)
        self.assertEqual(fetch.call_args.args[0],'http://localhost:11434/api/chat')

    @patch.object(server, 'fetch')
    def test_compatible_chat_response_and_malformed_errors(self, fetch):
        fetch.return_value = json.dumps({'choices':[{'message':{'content':'Compatible response'}}]})
        data = {'provider':'local','endpoint':'http://localhost:1234/v1','model':'local-test','messages':[{'role':'user','content':'Summarize'}]}
        self.assertEqual(server.chat(data)['reply'],'Compatible response')
        fetch.return_value = '{}'
        with self.assertRaises(ValueError): server.chat(data)


if __name__ == '__main__':
    unittest.main()
