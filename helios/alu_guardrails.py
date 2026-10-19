"""Bound ALU demo request work; this is not an edge DDoS firewall."""
import hashlib
from django.db import connection, transaction, DatabaseError
from django.http import HttpResponse


class AluRequestGuardrails:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method != 'POST' or not request.path.startswith(('/helios/', '/auth/alu')):
            return self.get_response(request)
        try:
            size = int(request.META.get('CONTENT_LENGTH') or 0)
        except (TypeError, ValueError):
            return self.refuse(400, 'Invalid request length')
        if size < 0 or size > 2 * 1024 * 1024:
            return self.refuse(413, 'Request too large')
        session = getattr(request, 'session', {})
        user = session.get('user') or {}
        # Identity is from Django's server-side session, never an IP/header or
        # browser-supplied subject. Avoid campus-wide limits on shared NAT IPs.
        if session.get('alu_election') and isinstance(user, dict) and user.get('type') == 'alu':
            subject = user.get('user_id')
            if isinstance(subject, str) and request.path.rstrip('/').endswith(('/cast', '/cast_confirm', '/register', '/ui/submit')):
                digest = hashlib.sha256(subject.encode()).hexdigest()
                try:
                    # Database clock and atomic UPSERT share one limit across all
                    # workers; no process cache, supplied IP, or browser identity.
                    with transaction.atomic(), connection.cursor() as cursor:
                        cursor.execute("""INSERT INTO helios_aluratebucket (key,hits,expires_at)
                          VALUES (%s || ':' || floor(extract(epoch from statement_timestamp())/60)::bigint::text,
                            1, statement_timestamp()+interval '2 minutes')
                          ON CONFLICT (key) DO UPDATE SET hits=helios_aluratebucket.hits+1
                          WHERE helios_aluratebucket.hits<20 RETURNING hits""", [digest])
                        row = cursor.fetchone()
                        count = row[0] if row else 21
                        if count == 1:
                            cursor.execute("""DELETE FROM helios_aluratebucket WHERE key IN (
                              SELECT key FROM helios_aluratebucket WHERE expires_at<statement_timestamp()
                              ORDER BY expires_at LIMIT 64 FOR UPDATE SKIP LOCKED)""")
                except DatabaseError:
                    return self.refuse(503, 'Voting request protection unavailable. Please retry')
                if count > 20:
                    return self.refuse(429, 'Please wait before retrying')
        return self.get_response(request)

    @staticmethod
    def refuse(status, message):
        response = HttpResponse(message, status=status)
        response['Cache-Control'] = 'no-store'
        response['Referrer-Policy'] = 'no-referrer'
        if status == 429:
            response['Retry-After'] = '60'
        return response
