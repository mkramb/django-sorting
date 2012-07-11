from django import template
from django.http import Http404
from django.conf import settings
from django.template.base import TemplateSyntaxError

register = template.Library()

DEFAULT_SORT_UP = getattr(settings, 'DEFAULT_SORT_UP' , '&uarr;')
DEFAULT_SORT_DOWN = getattr(settings, 'DEFAULT_SORT_DOWN' , '&darr;')
INVALID_FIELD_RAISES_404 = getattr(settings, 
        'SORTING_INVALID_FIELD_RAISES_404' , False)

sort_directions = {
    'asc': {'icon':DEFAULT_SORT_UP, 'inverse': 'desc'}, 
    'desc': {'icon':DEFAULT_SORT_DOWN, 'inverse': 'asc'}, 
    '': {'icon':DEFAULT_SORT_DOWN, 'inverse': 'asc'}, 
}

def anchor(parser, token):
    """
    Parses a tag that's supposed to be in this format: {% anchor field title %}    
    """
    bits = [b.strip('"\'') for b in token.split_contents()]

    if len(bits) < 2:
        raise TemplateSyntaxError, "anchor tag takes at least 1 argument"

    try:
        title = bits[2]
    except IndexError:
        title = bits[1].capitalize()

    return SortAnchorNode(bits[1].strip(), title.strip())
    

class SortAnchorNode(template.Node):
    """
    Renders an <a> HTML tag with a link which href attribute 
    includes the field on which we sort and the direction.
    and adds an up or down arrow if the field is the one 
    currently being sorted on.

    Eg.
        {% anchor name Name %} generates
        <a href="/the/current/path/?sort=name" title="Name">Name</a>

    """
    def __init__(self, field, title):
        self.field = field
        self.title = template.Variable(title)

    def render(self, context):
        title = self.title.resolve(context)

        request = context['request']
        getvars = request.GET.copy()

        if context.has_key('default_sort_field'):
            sortby = context['default_sort_field']
            sortdir = context['default_sort_dir']
        else:
            if 'sort' in getvars:
                sortby = getvars['sort']
                del getvars['sort']
            else:
                sortby = ''
            if 'dir' in getvars:
                sortdir = getvars['dir']
                del getvars['dir']
            else:
                sortdir = ''

        if sortby == self.field:
            getvars['dir'] = sort_directions[sortdir]['inverse']
            icon = sort_directions[sortdir]['icon']
        else:
            icon = ''

        if len(getvars.keys()) > 0:
            urlappend = "&%s" % getvars.urlencode()
        else:
            urlappend = ''

        if icon:
            title_icon = u"%s %s" % (title, icon)
        else:
            title_icon = title

        url = '%s?sort=%s%s' % (request.path, self.field, urlappend)
        return '<a href="%s" title="%s">%s</a>' % (url, title, title_icon)

def autosort(parser, token):
    bits = [b.strip('"\'') for b in token.split_contents()]

    if len(bits) == 1:
        raise TemplateSyntaxError, "autosort tag takes at least one argument"

    kwargs = dict()

    if len(bits) > 2:
        kwargs['default_sort_field'] = bits[2]

    if len(bits) > 3:
        kwargs['default_sort_dir'] = bits[3]

    return SortedDataNode(bits[1], **kwargs)

class SortedDataNode(template.Node):
    """
    Automatically sort a queryset with {% autosort queryset %}
    """
    def __init__(self, queryset_var, default_sort_field=None, default_sort_dir='desc', context_var=None):
        self.queryset_var = template.Variable(queryset_var)
        self.default_sort_field = default_sort_field
        self.default_sort_dir = default_sort_dir
        self.context_var = context_var

    def render(self, context):
        key = self.queryset_var.var
        value = self.queryset_var.resolve(context)
        order_by = context['request'].field

        if len(order_by) == 1 and self.default_sort_field:
            context['default_sort_field'] = self.default_sort_field
            context['default_sort_dir'] = self.default_sort_dir
            order_by = (self.default_sort_dir == 'desc' and '-' or '') + self.default_sort_field

        if len(order_by) > 1:
            try:
                context[key] = value.order_by(order_by)
            except template.TemplateSyntaxError:
                if INVALID_FIELD_RAISES_404:
                    raise Http404('Invalid field sorting. If DEBUG were set to ' +
                    'False, an HTTP 404 page would have been shown instead.')
                context[key] = value
        else:
            context[key] = value

        return ''

anchor = register.tag(anchor)
autosort = register.tag(autosort)

