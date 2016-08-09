import json
import os
import praw
import pdb
import re
import copy
from functools import wraps

def set_default(obj):
    if isinstance(obj, set):
        return list(obj)
    raise TypeError


def options_sub(options, keys):
    return dict((k, options[k]) for k in keys)


class Reddit(object):
    # Config/Options stuff

    class Config:
        def __init__(self, config_dict):
            setDict = self.__dict__
            setDict["config_dict"] = config_dict
            setDict["orig_config"] = copy.deepcopy(config_dict)
            print "Original config: ", setDict["orig_config"]
            if not(os.path.isfile(config_dict["auth_session_path"])):
                file(config_dict["auth_session_path"], "w").close()
            setDict["auth_session_file"] = open(config_dict["auth_session_path"], "r+")
            setDict["state_re"] = re.compile(r"^(posts|subreddits)(?:\-id=)?([A-Za-z0-9_]{3,9})?")

            self.__dict__ = setDict

        def get(self, key):
            try:
                if isinstance(key, basestring):
                    if not(key == "state"):
                        ret_val = self.config_dict[key]
                        if type(ret_val) is list:
                            return tuple(ret_val)
                        return ret_val
                    else:
                        page = self.config_dict["page"]
                        guid = self.config_dict["guid"]

                        if guid is not None:
                            return page + "-id=" + guid
                        else:
                            return page
                elif type(key) is tuple or type(key) is list:
                    return self.get_options(key)
                else:
                    raise ValueError
            except AttributeError as e:
                print e

        def set(self, key, val):
            if key == "state":
                state_match = self.state_re.match(val)
                if state_match is not None:
                    if len(state_match.groups()) == 2:
                        page_guid = state_match.groups()
                        self.config_dict["page"] = page_guid[0]
                        self.config_dict["guid"] = page_guid[1]
                        self.config_dict["state"] = val
                        return

                page = self.orig_config["page"]
                guid = self.orig_config["guid"]

                self.config_dict["page"] = page
                self.config_dict["guid"] = guid
                self.config_dict["state"] = page
                print "No page or guid able to be parsed, defaulting to orig_config parameters."
                print "Page: %   Guid: %    State:   %" % (page, guid, page)
                return

            if isinstance(key, basestring):
                if isinstance(val, list):
                    self.config_dict[str(key)] = tuple(val)
                else:
                    self.config_dict[str(key)] = val
            elif type(key) is tuple or type(key) is list:
                for i, k in enumerate(key):
                    self.config_dict[k] = val[i]
            else:
                raise ValueError

        def __getitem__(self, index):
            return self.get(index)

        def __setitem__(self, key, val):
            self.set(key, val)

        def __getattr__(self, key):
            return self.get(key)

        def __setattr__(self, key, item):
            self.set(key, item)

        def __str__(self):
            return "\n".join(["self = reddit.Reddit.Config"] + [str("self[" + key + "] = " + str(val)) for key, val in self.config_dict.iteritems()])

        def load_session_file(self):
            self.auth_session_file = open(self.auth_session_path, "r+")
            access_info = None

            auth_session_data = self.auth_session_file.read()
            if(len(auth_session_data) > 0):
                try:
                    access_info = json.loads(auth_session_data)                    
                    self.update(access_info)
                    return access_info
                except ValueError:
                    print "Auth file is corrupted"
                    return "Corrupted session file"

        def delete_session_file(self):
            open(self.auth_session_path, "w").close()
            self.auth_session_file = open(self.auth_session_path, "r+")

        def update(self, new_items):
            for key, value in new_items.iteritems():
                self.config_dict[key] = value

            self.delete_session_file()
            self.auth_session_file.seek(0)
            json.dump(self[self["session_keys"]], self.auth_session_file, default=set_default)
            self.auth_session_file.flush()

        def delete(self, key=None):
            if key is not None:
                if type(key) is str:
                    del self.config_dict[key]
                elif type(key) is tuple or type(key) is list:
                    for i, k in enumerate(key):
                        if k in self.config_dict:
                            del self.config_dict[k]
            else:
                self.delete(("access_token", "refresh_token"))
                open(self.auth_session_path, "w").close()  # clear out file by closing it on "w" write mode
                self.auth_session_file = open(self.auth_session_path, "r+")

        def get_options(self, keys):
            inter_keys = set(keys) & set(self.config_dict.keys())
            inter_dict = dict([(key, self[key]) for key in inter_keys])
            return inter_dict

    class FakeReddit:
        class FakeUser:
            def __init__(self):
                self.name = "ibly31"
                self.json_dict = {"name": "ibly31"}
        def __init__(self):
            self.user = self.FakeUser()

    def __init__(self, app=None):
        if app is not None:
            self.init_reddit()

    def init_reddit(self):
        with open("app/config.json", "r") as config_file:
            self.config = self.Config(json.load(config_file))
            print "======= Initializing new Reddit instance ======="

            if not(self.config["offline"]):
                self.r = praw.Reddit(**self.config[("user_agent", "log_requests", "store_json_result")])
                self.r.set_oauth_app_info(**self.config[("client_id", "client_secret", "redirect_uri")])
            else:
                self.r = self.FakeReddit()
            self.load_session_file()

    def save_session(self, session_dict):
        if session_dict["refresh_token"] is None:
            self.config.delete()
            return False
        else:
            self.config.update(session_dict)
            return True

    def delete_session(self):
        self.config.delete()

    def refresh_session(self):
        try:
            access_info = self.r.refresh_access_information(self.config["refresh_token"])
            return self.save_session(access_info)
        except praw.errors.OAuthException:
            self.delete_session()
            return False

    def is_valid_session(self, scope="identity"):
        scope_list = [sco for sco in self.config.orig_config["scope"].split(" ")]
        #print(self.config["offline"] and True)
        return self.r.has_scope(scope_list)  # this calls is_oauth_session() under the hood

    def get_session(self, code_and_state):
        try:
            access_info = self.r.get_access_information(code_and_state["code"])
            if type(access_info) is dict:
                access_info["state"] = code_and_state["state"]
                if self.save_session(access_info):
                    return True
            self.config.delete()
            return False
        except praw.errors.OAuthException:
            return False

    def load_session_file(self):
        access_info = self.config.load_session_file()
        if type(access_info) is dict:
            try:
                try:
                    self.r.set_access_credentials(**self.config[self.config["access_keys"]])
                except TypeError:
                    pdb.set_trace()

                if(not(self.is_valid_session())):
                    return self.refresh_session()

            except praw.errors.OAuthException:
                self.delete_session()
        else:
            print "Error loading access info: ", access_info
            self.delete_session()

    def get_auth_url(self):
        return self.r.get_authorize_url(**self.config[("state", "scope", "refreshable")])

    def get_me(self):
        return self.r.get_me()

    def vote_on_post(self, sub_id, dir):
        post = self.r.get_submission(submission_id=sub_id)
        post.vote(dir)

    def get_saved_posts(self, *args, **kwargs):
        # after=None, sort=None, time=None, count=None, subreddit=None

        content_params = self.config["content_params"]
        content_params.update(kwargs)

        saved = self.r.user.get_saved(**content_params)

        saved_posts = [post.json_dict for post in iter(saved)]
        saved_posts.insert(0, content_params)

        self.save_cached_results(saved_posts)

        return saved_posts

    def save_cached_results(self, results):
        try:
            results_json = json.dumps(results)
            cached_results_file = open(self.config["cache_session_path"], "w")
            cached_results_file.seek(0)
            cached_results_file.write(results_json)
            cached_results_file.close()
            print "Finished writing cache file"
            return True
        except (IOError, ValueError):
            print "Error serializing cached results json"
            return False

    def get_cached_results(self, *args, **kwargs):
        content_params = self.config["content_params"]
        content_params.update(kwargs)

        if os.path.isfile(self.config["cache_session_path"]):
            try:
                results = open(self.config["cache_session_path"], "r+")
                results_json = json.load(results)
                if len(results_json) > 0:
                    params = results_json[0]
                    print "Params: ", params
                    if params == content_params:
                        results_json.pop(0)
                        return results_json
                else:
                    self.delete_cached_results()
            except (IOError, ValueError):
                self.delete_cached_results()
        
        return None

    def delete_cached_results(self):
        open(self.config["cache_session_path"], "w").close()