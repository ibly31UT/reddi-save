from flask import render_template, flash, redirect, session, url_for, request, g
from . import main
from .. import red
from ..decorators import templated, require_session
import json
import pdb


@main.route("/")
@main.route("/index", methods=["GET", "POST"])
@templated("index.html")
def index():
    return dict(title="Home")


@main.route("/getSaved", methods=["POST"])
@require_session("read history")
def getSaved():
    request_obj = request.get_json()
    print request_obj
    print "Requesting \"/getSaved\", here are the params: "

    arguments = {}

    for key in ("subreddit", "sort", "time", "after", "count"):
        if key in request_obj:
            arguments[key] = request_obj[key]
            print "adding key ", key, " to arguments with value: ", request_obj[key]

    saved_posts = red.get_cached_results(**arguments)
    if saved_posts is None:
        saved_posts = red.get_saved_posts(**arguments)

    list_partial = render_template("list.html", posts=saved_posts)
    return json.dumps(dict(status="success", posts=saved_posts, list_partial=list_partial))

@main.route("/vote", methods=["POST"])
@require_session("read history vote")
def vote():
    request_obj = request.get_json()
    print request_obj

    red.vote_on_post(request_obj["id"], request_obj["dir"])

    return json.dumps(dict(success=True))

@main.route("/posts", methods=["GET"])
@require_session("read history")
def posts():
    user = red.r.user.json_dict
    return render_template("posts.html", title="Posts", user=user)
