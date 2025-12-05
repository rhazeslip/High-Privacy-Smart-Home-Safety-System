import http.server
import ssl
import socketserver

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=".", **kwargs)

httpd = socketserver.TCPServer(("127.0.0.1", 3000), Handler)
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain('../cert.pem', '../key.pem')
httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

print("Serving HTTPS on https://127.0.0.1:3000...")
httpd.serve_forever()