from aiohttp import web
import ssl

async def handle(request):
    """Serve the requested file or index.html for /"""
    path = request.path
    if path == '/':
        path = '/index.html'
    
    try:
        with open('.' + path, 'rb') as f:
            content = f.read()
            
        content_type = 'text/html'
        if path.endswith('.js'):
            content_type = 'application/javascript'
        elif path.endswith('.css'):
            content_type = 'text/css'
            
        return web.Response(body=content, content_type=content_type)
    except FileNotFoundError:
        return web.Response(status=404, text='Not Found')

app = web.Application()
app.router.add_get('/{tail:.*}', handle)

ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain('../cert.pem', '../key.pem')

if __name__ == '__main__':
    web.run_app(app, host='localhost', port=3000, ssl_context=ssl_context)