from rest_framework.throttling import SimpleRateThrottle


class LoginUsernameThrottle(SimpleRateThrottle):
    """
    Per-username login throttle (EF-09), applied alongside the per-IP scope.

    The IP throttle alone has two gaps: outlets behind one NAT share a bucket (one
    terminal's failures can lock out the outlet), and a distributed attacker gets the
    full rate from *each* IP. Keying a second bucket on the submitted username caps
    guessing against any single account no matter how many IPs it comes from, without
    penalising other users behind the same NAT.
    """
    scope = 'login_user'

    def get_cache_key(self, request, view):
        username = (request.data.get('username') or '').strip().lower()
        if not username:
            # No username to key on — leave it to the per-IP throttle.
            return None
        return self.cache_format % {'scope': self.scope, 'ident': username}
