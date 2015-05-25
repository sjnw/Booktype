from django.views.generic import TemplateView
from django.views import static
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.shortcuts import RequestContext
from django.conf import settings
from django.template import loader
from django.http import HttpResponse

from booki.editor.models import Book, BookiGroup
from booktype.utils.security import Security, BookSecurity, GroupSecurity
from booktype.utils.security import get_security, get_security_for_book, get_security_for_group

class BasePageView(object):
    page_title = ''
    title = ''
    
    def get_context_data(self, **kwargs):
        context = super(BasePageView, self).get_context_data(**kwargs)
        context["page_title"] = self.page_title
        context["title"] = self.title
        context["request"] = self.request

        return context

class PageView(BasePageView, TemplateView):
    pass


class SecurityMixin(object):
    AVAILABLE_BRIDGES = (Security, BookSecurity, GroupSecurity)

    def __init__(self, **kwargs):
        super(SecurityMixin, self).__init__(**kwargs)
        self.security = None

        if hasattr(self, 'SECURITY_BRIDGE'):
            # validate bridge
            if self.SECURITY_BRIDGE not in self.AVAILABLE_BRIDGES:
                raise Exception('Wrong security bridge! Available bridges: '
                                '{0}'.format(",".join([str(i) for i in self.AVAILABLE_BRIDGES])))
            self.security_bridge = self.SECURITY_BRIDGE
        else:
            self.security_bridge = Security

    def dispatch(self, request, *args, **kwargs):
        # try to create security instance
        try:
            if self.security_bridge is Security:
                self.security = get_security(request.user)
            elif self.security_bridge is BookSecurity:
                book = Book.objects.get(url_title__iexact=kwargs['bookid'])
                self.security = get_security_for_book(request.user, book)
            elif self.security_bridge is GroupSecurity:
                group = BookiGroup.objects.get(url_name=kwargs['groupid'])
                self.security = get_security_for_group(request.user, group)
        except KeyError as e:
            raise Exception('{bridge} bridge requires "{key}" in request'.format(bridge=self.security_bridge,
                                                                                 key=e.message))

        # hook for checking permissions
        self.check_permissions(request, *args, **kwargs)

        return super(SecurityMixin, self).dispatch(request, *args, **kwargs)

    def check_permissions(self, request, *args, **kwargs):
        """Checking permissions

        :Args:
          - request (:class:`django.http.HttpRequest`): Django http request instance

        :Raises:
          PermissionDenied: If no access
        """
        pass

    def get_context_data(self, **kwargs):
        context = super(SecurityMixin, self).get_context_data(**kwargs)
        # add security instance in context
        if 'security' in context.keys():
            raise Exception('SecurityMixin requires context key "security" not to be used.')

        context['security'] = self.security
        return context


def staticattachment(request, bookid,  attachment, version=None, chapter = None, revid = None):
    """
    Django View. Returns content of an attachment.

    @todo: It is wrong in so many different levels to serve attachments this way.

    @type request: C{django.http.HttpRequest}
    @param request: Client Request object
    @type bookid: C{string}
    @param bookid: Unique Book ID
    @type attachment: C{string}
    @param attachment: Name of the attachment
    @type version: C{string}
    @param version: Version of the book
    """
    
    book = get_object_or_404(Book, url_title__iexact=bookid)
    book_version = book.getVersion(version)
    path = '%s/%s' % (book_version.getVersion(), attachment)
    document_root = '%s/books/%s/' % (settings.DATA_ROOT, bookid)

    return static.serve(request, path, document_root)


def ErrorPage(request, template_file, args={}, status=200, content_type='text/html'):
    """
    Returns nicely formated Error page.

    @type request: C{django.http.HttpRequest}
    @param request: Client Request object
    @type template_file: C{string}
    @param template_file: Path to template file
    @type args: C{dict}
    @param args: Additional arguments we want to pass to the template
    @type status: C{int}
    @param status: HTTP return code
    @type content_type: C{string}
    @param content_type: Content-Type for the response
    """

    t = loader.get_template(template_file)
    c = RequestContext(request, args)

    return HttpResponse(t.render(c), status=status, content_type=content_type)


def error404(request):
    return render(request, 'errors/404.html')


def error500(request):
    return render(request, 'errors/500.html')


def error403(request):
    return render(request, 'errors/403.html')


def error400(request):
    return render(request, 'errors/400.html')    