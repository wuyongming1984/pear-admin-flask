from pathlib import Path
import tempfile
import unittest
from flask import Flask
from pear_admin.views.index import index_bp

class DesktopEntryTest(unittest.TestCase):
    def test_parallel_entry_and_config_switch(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'desktop').mkdir()
            (root/'desktop/index.html').write_text('<div>Vue desktop</div>')
            app=Flask(__name__,static_folder=folder,template_folder=str(Path(__file__).resolve().parents[1]/'templates'))
            app.register_blueprint(index_bp)
            client=app.test_client()
            with client.get('/pc/') as response:
                self.assertEqual(response.status_code,200)
                self.assertIn(b'Vue desktop',response.data)
                self.assertIn('no-store',response.headers['Cache-Control'])
            self.assertIn(b'pear.css',client.get('/').data)
            app.config['DESKTOP_DEFAULT']=True
            self.assertEqual(client.get('/').location,'/pc/')
            self.assertIn(b'pear.css',client.get('/legacy/').data)

    def test_missing_build_reports_unavailable(self):
        with tempfile.TemporaryDirectory() as folder:
            app=Flask(__name__,static_folder=folder)
            app.register_blueprint(index_bp)
            self.assertEqual(app.test_client().get('/pc/').status_code,503)
