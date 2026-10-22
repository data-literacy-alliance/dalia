"""Regroup the admin app list into one block per public site.

Wraps ``admin.site.get_app_list`` so the sidebar and the admin index (both built from it)
show website content and search-portal content separately. Model dicts are moved untouched,
so URLs, permissions and anything Django already filtered out stay exactly as they were.
"""

import copy
from functools import wraps

from django.contrib import admin

WEBSITE_GROUP_LABEL = "site_website"
WEBSITE_GROUP_NAME = "Website \u2014 dalia.education"
SEARCH_GROUP_LABEL = "site_search_portal"
SEARCH_GROUP_NAME = "Search portal \u2014 search.dalia.education"

# (group label, group name, ordered (app_label, object_name) members)
SITE_GROUPS = (
    (
        WEBSITE_GROUP_LABEL,
        WEBSITE_GROUP_NAME,
        (
            ("pages", "WebsitePage"),
            ("pages", "MediaImage"),
            ("pages", "EventCategory"),
            ("mailing", "ContactFormSettings"),
            ("mailing", "EmailProvider"),
        ),
    ),
    (
        SEARCH_GROUP_LABEL,
        SEARCH_GROUP_NAME,
        (("pages", "SearchPage"),),
    ),
)
_SOURCE_APPS = frozenset(app for _, _, members in SITE_GROUPS for app, _ in members)
_PATCHED_FLAG = "_site_groups_patched"


def regroup_app_list(app_list):
    """Return ``app_list`` with the pages/mailing models moved into the two site groups."""
    by_label = {app["app_label"]: app for app in app_list}
    if not _SOURCE_APPS & by_label.keys():
        return app_list
    models = {
        (app["app_label"], model["object_name"]): model
        for app in app_list
        if app["app_label"] in _SOURCE_APPS
        for model in app["models"]
    }
    groups = []
    for label, name, members in SITE_GROUPS:
        found = [(key, models[key]) for key in members if key in models]
        if not found:
            continue
        source = by_label[found[0][0][0]]
        group = {
            **{k: v for k, v in source.items() if k not in ("models", "name", "app_label")},
            "name": name,
            "app_label": label,
            "models": [copy.copy(model) for _, model in found],
        }
        groups.append(group)

    result, inserted = [], False
    for app in app_list:
        if app["app_label"] in _SOURCE_APPS:
            if not inserted:
                result.extend(groups)
                inserted = True
            leftovers = [
                m
                for m in app["models"]
                if (app["app_label"], m["object_name"])
                not in {(a, o) for _, _, mem in SITE_GROUPS for a, o in mem}
            ]
            if leftovers:
                result.append({**app, "models": leftovers})
        else:
            result.append(app)
    return result


def install(site=None):
    """Patch ``get_app_list`` once; ``app_label`` lookups (app index pages) stay untouched."""
    site = site or admin.site
    if getattr(site, _PATCHED_FLAG, False):
        return
    original = site.get_app_list

    @wraps(original)
    def get_app_list(request, app_label=None):
        app_list = original(request, app_label)
        if app_label is not None:
            return app_list
        return regroup_app_list(app_list)

    site.get_app_list = get_app_list
    setattr(site, _PATCHED_FLAG, True)
