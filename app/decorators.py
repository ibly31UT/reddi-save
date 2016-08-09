from flask import render_template, flash, redirect, session, url_for, request, g
from functools import wraps
from . import red

def require_session(scope="identity"):
    def session_decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not(red.is_valid_session(scope)):
                print "endpoint: ", request.endpoint
                print "url:", request.url
                return redirect(url_for("auth.index/" + request.endpoint))
            return f(*args, **kwargs)
        return decorated_function
    return session_decorator


def templated(template=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            template_name = template
            if template_name is None:
                template_name = request.endpoint.replace('.', '/') + '.html'
            ctx = f(*args, **kwargs)
            if ctx is None:
                ctx = {}
            elif not isinstance(ctx, dict):
                return ctx
            return render_template(template_name, **ctx)
        return decorated_function
    return decorator