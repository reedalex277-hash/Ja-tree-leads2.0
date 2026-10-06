from http.server import BaseHTTPRequestHandler
from datetime import datetime, timezone
import json, os, uuid
import urllib.request, urllib.error, urllib.parse

OWNER = 'reedalex745@gmail.com'
HOME = 'https://ja-tree-leads2-0.vercel.app'
STATUSES = {'new', 'contacted', 'quoted', 'won', 'lost'}

class handler(BaseHTTPRequestHandler):
    def reply(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def remote(self, path, method='GET', data=None, token=None):
        url = os.environ.get('SUPABASE_URL', '').rstrip('/')
        key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '')
        if not url.startswith('https://') or not key:
            raise RuntimeError('Inbox connection is not configured.')
        headers = {'apikey': key, 'Authorization': 'Bearer ' + (token or key),
                   'Content-Type': 'application/json', 'Prefer': 'return=representation'}
        req = urllib.request.Request(url + path, method=method, headers=headers,
              data=None if data is None else json.dumps(data).encode())
        with urllib.request.urlopen(req, timeout=15) as response:
            raw = response.read()
            return json.loads(raw) if raw else None

    def owner(self):
        auth = self.headers.get('Authorization', '')
        if not auth.startswith('Bearer ') or len(auth) > 8192:
            raise PermissionError('Sign in to view requests.')
        try:
            user = self.remote('/auth/v1/user', token=auth[7:])
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                raise PermissionError('Your sign-in expired. Sign in again.')
            raise
        if not isinstance(user, dict) or user.get('email', '').lower() != OWNER or not user.get('email_confirmed_at'):
            raise PermissionError('This account cannot access the contractor inbox.')

    def body(self):
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            raise ValueError('Send JSON.')
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= 12000:
            raise ValueError('Invalid request size.')
        data = json.loads(self.rfile.read(length))
        if not isinstance(data, dict):
            raise ValueError('Invalid request.')
        return data

    def perform(self, action):
        try:
            return action()
        except PermissionError as error:
            return self.reply({'error': str(error)}, 401)
        except (ValueError, TypeError, UnicodeDecodeError):
            return self.reply({'error': 'Please check the submitted values.'}, 400)
        except urllib.error.HTTPError as error:
            if error.code == 429:
                return self.reply({'error': 'Please wait before requesting another sign-in link.'}, 429)
            return self.reply({'error': 'The inbox service could not complete this action. Please try again.'}, 502)
        except (urllib.error.URLError, TimeoutError, RuntimeError):
            return self.reply({'error': 'The inbox service is unavailable. Please try again.'}, 503)

    def do_POST(self):
        def login():
            data = self.body()
            if data.get('email', '').strip().lower() != OWNER:
                return self.reply({'error': 'Use your authorized contractor email.'}, 403)
            self.remote('/auth/v1/otp?redirect_to=' + urllib.parse.quote(HOME + '/inbox', safe=''),
                        'POST', {'email': OWNER, 'create_user': True})
            return self.reply({'success': True})
        return self.perform(login)

    def do_GET(self):
        def read():
            self.owner()
            params = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            offset = int(params.get('offset', ['0'])[0])
            if not 0 <= offset <= 100000:
                raise ValueError()
            rows = self.remote('/rest/v1/customer_requests?select=*&order=created_at.desc&limit=100&offset=' + str(offset))
            return self.reply({'requests': rows})
        return self.perform(read)

    def do_PATCH(self):
        def update():
            self.owner()
            data = self.body()
            request_id = str(uuid.UUID(data.get('id', '')))
            status = data.get('status')
            notes = data.get('notes', '')
            followup = data.get('followup')
            if status not in STATUSES or not isinstance(notes, str) or len(notes) > 5000:
                raise ValueError()
            if followup is not None:
                if not isinstance(followup, str) or len(followup) > 40:
                    raise ValueError()
                date = datetime.fromisoformat(followup.replace('Z', '+00:00'))
                if date.tzinfo is None:
                    raise ValueError()
                followup = date.astimezone(timezone.utc).isoformat()
            rows = self.remote('/rest/v1/customer_requests?id=eq.' + request_id, 'PATCH',
                               {'status': status, 'notes': notes, 'followup': followup})
            if not rows:
                return self.reply({'error': 'Request no longer exists.'}, 404)
            return self.reply({'request': rows[0]})
        return self.perform(update)
