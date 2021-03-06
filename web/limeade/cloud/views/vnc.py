"""Views for limeade cloud VNC"""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.sessions.models import Session
from django.shortcuts import render_to_response
from django.contrib.auth.models import User
from django.template import RequestContext
from django.http import HttpResponse
from django.utils import simplejson
from django.conf import settings
from django.http import Http404

from lxml.html import fromstring
from urlparse import urlparse

from limeade.cloud.models import Instance

import libvirt


@login_required
def instance_vnc(request, slug):
    """Lets view the authenticated user a VNC console.
    
    :param request: the request object
    :param slug: the virtual machine id
    
    :returns: the vnc template
    
    :raises: DoesNotExist
    """
    try:
        i = Instance.objects.get(pk=slug, owner=request.user).pk
    except Instance.DoesNotExist:
        raise Http404
    
    node_host = settings.NODE_HOST
    node_port = settings.NODE_PORT
    token = request.session.session_key
    
    return render_to_response('limeade_cloud/instance_vnc.html', {'id': i, 
    'host': node_host, 'port': node_port, 'token': token}, context_instance=RequestContext(request))


def instance_vnc_auth(request, slug, token):
    """API call for websocket to tcp proxy to get the settings.
    
    :param request: the request object
    :param slug: the virtual machine id
    :param token: the session id from the requesting user
    
    :returns: dictionary containing proxy settings
    
    :raises: ObjectDoesNotExist
    """
    status_code = 200 # default status code
    vnc_port = '5900' # default port
    host = None
    
    try:
        s = Session.objects.get(pk=token)
        user_id = s.get_decoded().get('_auth_user_id')
        user = User.objects.get(pk=user_id)
        i = Instance.objects.get(pk=slug, owner=user)
    except ObjectDoesNotExist:
        status_code = 500
    
    if i:
        host = urlparse(i.node.uri).netloc
    
    try:
        c = libvirt.open(i.node.uri)
        dom = c.lookupByName(i.domain)
        xml = dom.XMLDesc(0)
    except:
        # TODO: catch exception?
        pass
    
    try:
        vnc_port = fromstring(xml).xpath('../domain/devices/graphics[@type="vnc"]')[0].attrib['port']
    except:
        # TODO: catch exception?
        pass
    
    data = {
        'host': host,
        'port': int(vnc_port)
    }
    
    return HttpResponse(simplejson.dumps(data), mimetype='application/json', status=status_code)

