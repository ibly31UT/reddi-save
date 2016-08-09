from flask import render_template, flash, redirect, session, url_for, request, g
from . import auth
from ..decorators import templated, require_session
from .. import red
import json
from random import choice
from string import ascii_letters
from string import digits
import pdb


@auth.route("/")
@auth.route("/index")
@auth.route("/index/<state>", methods=["GET"])
@templated("index.html")
def index(state=None):
    if state is not None:
        red.config["state"] = state
    else:
        red.config["state"] = "posts"

    if red.config["guid"] is None:
        red.config["guid"] = "".join([choice(ascii_letters + digits) for x in range(0, 7)])
    
    if red.is_valid_session():
        return redirect(url_for("main." + red.config["page"]))

    authUrl = red.get_auth_url()
    return dict(authUrl = authUrl, title="Authorize Reddit")

@auth.route("/authorize", methods=["GET"])
@templated("auth.html")
def authorize():
    state = request.args.get("state")
    code = request.args.get("code")

    if red.get_session(dict(state=state, code=code)):
        return redirect(url_for("main." + red.config["page"]))
    else:
        red.config["state"] = state
        return redirect(url_for(".index/" + red.config["page"]))

@auth.route("/deauthorize", methods="GET")
@require_session()
def deauthorize():
    red.delete_session()
    return redirect(url_for("main.index"))