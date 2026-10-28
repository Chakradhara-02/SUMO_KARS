"""Internal verification runner: deny non-loopback Python socket connections."""
import ipaddress
import os
import runpy
import sys
import ssl

os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD']='1'
os.environ['DOTNET_CLI_TELEMETRY_OPTOUT']='1'
os.environ['POWERSHELL_TELEMETRY_OPTOUT']='1'
os.environ['VSCODE_DISABLE_TELEMETRY']='1'
# A loopback proxy must not turn an allowed local socket into external HTTPS.
# These checks apply before tunnelling as well as to direct socket connections.
def allowed_host(host):
    if host in ('localhost',None):return True
    try:return ipaddress.ip_address(host).is_loopback
    except ValueError:return False
original_tls=ssl.SSLContext.wrap_socket
def local_tls(self,*args,**kwargs):
    if not allowed_host(kwargs.get('server_hostname')):
        raise PermissionError('Local validation denies external TLS, including proxy tunnels')
    return original_tls(self,*args,**kwargs)
ssl.SSLContext.wrap_socket=local_tls
def local_only(event,args):
    if event=='socket.getaddrinfo' and not allowed_host(args[0]):
        raise PermissionError('Local validation denies external DNS')
    if event=='http.client.connect' and not allowed_host(args[1]):
        raise PermissionError('Local validation denies external HTTP')
    if event=='socket.connect':
        address=args[1]
        if not isinstance(address,tuple):return
        host=address[0]
        if host=='localhost':return
        try:allowed=ipaddress.ip_address(host).is_loopback
        except ValueError:allowed=False
        if not allowed:raise PermissionError('Validation denies external network connections')
sys.addaudithook(local_only)
mode=sys.argv.pop(1)
if mode=='pytest':runpy.run_module('pytest',run_name='__main__',alter_sys=True)
else:
    sys.argv[0]=mode
    runpy.run_path(mode,run_name='__main__')
