from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
from urllib.parse import unquote, urlparse
from websocket import create_connection
import json
import argparse
import ssl

parser = argparse.ArgumentParser(description='This middleware converts HTTP query params to websocket json data')
parser.add_argument('host', metavar='target_host',help='target WebSocket host',type=str)
parser.add_argument('port', metavar='target_port', help='target Websocket port',type=int)
parser.add_argument('-proxy_host',help='proxy server host',type=str)
parser.add_argument('-proxy_port',help='proxy server port',type=int)
parser.add_argument('--ssl', help='enable SSL/TLS',action='store_true')

args = parser.parse_args()

if args.ssl:
    ws_server = "wss://"+args.host+":"+str(args.port)+"/"
else:
    ws_server = "ws://"+args.host+":"+str(args.port)+"/"

def send_ws(query):
    if not args.proxy_host and not args.proxy_port:
        ws = create_connection(ws_server, sslopt={"cert_reqs": ssl.CERT_NONE})
    else:
        ws = create_connection(ws_server, http_proxy_host=args.proxy_host, http_proxy_port=str(args.proxy_port),proxy_type="http", sslopt={"cert_reqs": ssl.CERT_NONE})
    # If the server returns a response on connect, use below line    
    #resp = ws.recv() # If server returns something like a token on connect you can find and extract from here
    
    # format the payload in JSON
    q_list = query.split('&')
    j_dict = {}
    for item in q_list:
        key, value = item.split('=')
        key = unquote(key).replace('"','\'')
        value = unquote(value).replace('"','\'')
        j_dict[key] = value

    j_str = json.dumps(j_dict)
    print("send WebSocket data:" + j_str)

    ws.send(j_str)
    resp = ws.recv()
    ws.close()

    if resp:
        return resp
    else:
        return ''

def middleware_server(host_port,content_type="text/plain"):
    class CustomHandler(SimpleHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            try:
                payload = urlparse(self.path).query
            except IndexError:
                payload = False
                
            if payload:
                content = send_ws(payload)
            else:
                content = 'No parameters specified!'

            self.send_header("Content-type", content_type)
            self.end_headers()
            self.wfile.write(content.encode())
            return

    class _TCPServer(TCPServer):
        allow_reuse_address = True

    httpd = _TCPServer(host_port, CustomHandler)
    httpd.serve_forever()

print("[+] Starting MiddleWare Server")
print("[+] Send payloads in http://localhost:9999/?key0=value0&key1=value1")

try:
    middleware_server(('0.0.0.0',9999))
except KeyboardInterrupt:
    pass