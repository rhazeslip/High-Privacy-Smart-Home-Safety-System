import uvicorn
import socket
import fastapi
import time

# Press the green button in the gutter to run the script.


def check(host,port,timeout=2):
    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM) #presumably
    sock.settimeout(timeout)
    try:
       sock.connect((host,port))
    except:
       return False
    else:
       sock.close()
       return True


async def app(scope, message, receive, send):
    assert scope['type'] == 'http'

    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            (b'content-type', b'text/plain'),
            (b'content-length', b'13'),
        ],
    })
    await send({
        'type': 'http.response.body',
        'body': f'{message}',
    })

def main():
    found = True
    port = 8080
    while found:
        found = check('http://127.0.0.1/',port, timeout=1)
        print(check('google.com',port, timeout=1), port)
        if found:
            port += 1
    print(f"Running app on port ${port}")
    uvicorn.run("main:app", port=port, reload=True)

if __name__ == '__main__':
    main()