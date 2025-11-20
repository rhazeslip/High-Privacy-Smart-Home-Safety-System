import uvicorn
import socket
import fastapi
import time

def check(host,port,timeout=2):
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM) 
    sock.settimeout(timeout)
    try:
       sock.connect((host,port))
    except:
       return False
    else:
       sock.close()
       return True


async def app(scope, receive, send):
    assert scope['type'] == 'http'

    body = b'Device Online'
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            (b'content-type', b'text/plain'),
            (b'content-length', str(len(body)).encode()),
        ],
    })
    await send({
        'type': 'http.response.body',
        'body': body,
    })

def main():
    found = True
    port = 8080
    while found:
        found = check('127.0.0.1', port, timeout=1)
        if found:
            port += 1
    print(f"Running app on port {port}")
    uvicorn.run("main:app", port=port, reload=True)

if __name__ == '__main__':
    main()