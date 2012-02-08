from django.conf.urls.defaults import patterns, url

import views

NAME_PREFIX = 'org.aptivate.intranet.documents.'

urlpatterns = patterns('',
    # Examples:
    url(r'^$', views.IndexView.as_view(),
        name=NAME_PREFIX + "index"),
)
