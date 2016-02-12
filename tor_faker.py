from stem.control import Controller
from stem import Signal
import _utility as utils
import stem
import sys
import pycurl
import io
import urllib
import time


class TorFaker:
    _is_renewing = False

    def __init__(self, tor_controller, sock_port, always_renew):

        self.SOCKS_PORT = 9050

        # Create tor controller
        # This object will control Tor services, it might refresh IP address
        try:
            self._tor_controller = Controller.from_port(port=9051)
        except stem.SocketError as exc:
            utils.print_log('Unable to connect tor controller on port 9051: %s' % exc, 'alert')
            sys.exit(1)

        # Authenticate tor controller. Allow it control tor service
        try:
            self._tor_controller.authenticate()
        except stem.connection.AuthenticationFailure as exc:
            utils.print_log('Unable to authenticate: %s' % exc, 'alert')
            sys.exit(1)

        utils.print_log('Tor is running version %s' % self._tor_controller.get_version(), 'success')

    def renew_ipaddress(self):
        try:
            self._tor_controller.signal(Signal.NEWNYM)
            self._is_renewing = True
            utils.print_log("Renewing IP Address", 'header')
            time.sleep(10)
            self._is_renewing = False
            return True
        except Exception, e:
            utils.print_log("Renew IP address has some error: %s" % e, 'alert')
            return False


class TorRequest:
    def __init__(self, header=None, user_agent="PyOnio", sock_port=9050):
        self.output = io.BytesIO()
        self.response_header = io.BytesIO()
        self._response = {}
        self.query_curl = pycurl.Curl()

        request_header = []

        if type(header) == dict:
            for key in header:
                request_header.append('%s: %s' % (key, header[key]))

        # Initialize CURL Config
        self.query_curl.setopt(pycurl.PROXY, '127.0.0.1')
        self.query_curl.setopt(pycurl.PROXYPORT, sock_port)
        self.query_curl.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5)
        self.query_curl.setopt(pycurl.SSL_VERIFYPEER, 1)
        self.query_curl.setopt(pycurl.SSL_VERIFYHOST, 2)
        self.query_curl.setopt(pycurl.CAINFO, '/etc/ssl/certs/ca-certificates.crt')
        self.query_curl.setopt(pycurl.WRITEFUNCTION, self.output.write)
        self.query_curl.setopt(pycurl.HEADERFUNCTION, self.response_header.write)
        self.query_curl.setopt(pycurl.USERAGENT, user_agent)
        self.query_curl.setopt(pycurl.HTTPHEADER, request_header)
        self.query_curl.setopt(self.query_curl.FOLLOWLOCATION, True)

    def request(self, url, data={}):
        self.query_curl.setopt(pycurl.URL, url)
        # Validate input form data
        if type(data) != dict:
            utils.print_log("Can't not determine type of form data")
            return False

        # encode post data
        if data != {}:
            post_fields = urllib.urlencode(data)
            self.query_curl.setopt(self.query_curl.POSTFIELDS, post_fields)

        try:
            # Request execute
            self.query_curl.perform()

            # Get response code
            self._response['code'] = self.query_curl.getinfo(pycurl.HTTP_CODE)

            # Get response value
            self._response['body'] = self.output.getvalue()

            # Get response header
            self._response['header'] = self.response_header.getvalue()

            # Get response destination
            self._response['location'] = self.query_curl.getinfo(pycurl.EFFECTIVE_URL)

        except pycurl.error as exc:
            print utils.print_log("Unable to reach %s: (%s)" % (url, exc), 'alert')
            return False

    def get_response(self):
        return self._response
