"""Exercise real connection reuse and cookie isolation on loopback only."""
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Barrier, Thread
from unittest import TestCase

from helios import service_http


class ServiceHttpTests(TestCase):
    def test_connections_reused_per_thread_without_cookies_or_sticky_auth(self):
        calls = []
        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'
            def do_POST(self):
                body = self.rfile.read(int(self.headers['Content-Length'])).decode()
                calls.append((body, self.client_address[1], self.headers.get('Cookie'),
                              self.headers.get('Authorization')))
                self.send_response(200)
                self.send_header('Set-Cookie', 'student=must-not-persist; Path=/')
                self.send_header('Content-Length', '2')
                self.end_headers()
                self.wfile.write(b'ok')
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        server.daemon_threads = True
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        barrier = Barrier(2)
        def student(subject):
            barrier.wait(timeout=5)
            for attempt in range(2):
                response = service_http.post(f'http://127.0.0.1:{server.server_port}/',
                    data=subject, headers={'Authorization':subject} if attempt == 0 else {},
                    timeout=3, allow_redirects=False)
                self.assertEqual(response.content, b'ok')
            self.assertFalse(service_http._local.session.cookies)
            service_http._local.session.close()
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                list(pool.map(student, ['student-a', 'student-b']))
            self.assertEqual(len(calls), 4)
            self.assertTrue(all(cookie is None for _, _, cookie, _ in calls))
            ports = []
            for subject in ['student-a', 'student-b']:
                own = [c for c in calls if c[0] == subject]
                self.assertEqual(own[0][1], own[1][1])
                self.assertEqual([c[3] for c in own], [subject, None])
                ports.append(own[0][1])
            self.assertNotEqual(*ports)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
