# http://www.ibm.com/developerworks/opensource/library/os-django-admin/index.html

import models
import django.contrib.admin

from binder.admin import AdminWithReadOnly
from forms import DocumentForm

class DocumentAdmin(AdminWithReadOnly):
    list_display = ('title', models.Document.get_authors)
    readonly_fields = ('uploader',)

    def queryset(self, request):
        if request.user.groups.filter(name='Guest'):
            limit_to_program = request.user.program
        else:
            limit_to_program = None

        qs = super(self.__class__, self).queryset(request)
        
        if limit_to_program:
            return qs.filter(programs=limit_to_program)
        else:
            return qs

    def get_form_class(self, request, obj=None, **kwargs):
        return DocumentForm
    
    def send_notification_email(self, document, request, template):
        if document.uploader and document.uploader != request.user:
            # If there's no uploader then there's nobody to notify.
            # We also don't notify a user when they modify their own document.
            #
            # Documents being created by add_view don't have an uploader,
            # so they don't end up sending an email either, which is what
            # we want. We could also check for change=True.

            # Load a copy of the document, so that it still has an ID
            # if the caller delete()s it later
            
            document = models.Document.objects.get(id=document.id) 

            from django.conf import settings
            context = {
                'document': document,
                'user': request.user,
                'settings': settings,
            }

            from mail_templated import EmailMessage
            email = EmailMessage(template, context,
                to=[document.uploader.email])
            email.send()

    def save_form(self, request, form, change):
        """
        Override the default save_form() to send notification emails,
        and to force the uploader field of the document to be the current
        user, whatever they may have POSTed to us.
        """

        document = form.instance
        self.send_notification_email(document, request, 
            'email/document_modified.txt.django')

        document = super(DocumentAdmin, self).save_form(request, form, change)
        document.uploader = request.user
        return document
    
    def delete_model(self, request, document):
        """
        Override the default delete_model() to send notification emails
        and implement soft deletion.
        """

        self.send_notification_email(document, request, 
            'email/document_deleted.txt.django')
        document.deleted = True
        document.save()

    """
    def delete_view(self, request, object_id, extra_context=None):
        return AdminWithReadOnly.delete_view(self, request, object_id, extra_context=extra_context)
    """

    def has_delete_permission(self, request, document=None):
        """
        Allow document uploaders to delete their own documents, despite
        lacking the Delete Document privilege.
        """
        
        if document is not None and document.uploader == request.user:
            return True

        return super(DocumentAdmin, self).has_delete_permission(request, 
            document)
            
    def get_deleted_objects(self, objs, opts, request, using):
        """
        Find all objects related to ``objs`` that should also be deleted. ``objs``
        must be a homogenous iterable of objects (e.g. a QuerySet).
    
        Returns a nested list of strings suitable for display in the
        template with the ``unordered_list`` filter.
        
        Copied from django.contrib.admin.util.get_deleted_objects and
        extended to override delete permissions to take the object's
        uploader into account, by allowing deletion if has_delete_permission()
        returns True.
        """

        from django.contrib.admin.util import NestedObjects
        collector = NestedObjects(using=using)
        collector.collect(objs)
        perms_needed = set()
    
        def format_callback(obj):
            has_admin = obj.__class__ in self.admin_site._registry
            opts = obj._meta

            from django.utils.html import escape
            from django.utils.safestring import mark_safe
            from django.utils.text import capfirst
            from django.core.urlresolvers import reverse
    
            if has_admin:
                from django.contrib.admin.util import quote
                admin_url = reverse('%s:%s_%s_change'
                                    % (self.admin_site.name,
                                       opts.app_label,
                                       opts.object_name.lower()),
                                    None, (quote(obj._get_pk_val()),))
                p = '%s.%s' % (opts.app_label,
                               opts.get_delete_permission())
                
                if isinstance(obj, self.model):
                    if not self.has_delete_permission(request, obj):
                        perms_needed.add(opts.verbose_name)
                elif not request.user.has_perm(p):
                    perms_needed.add(opts.verbose_name)
                # Display a link to the admin page.

                return mark_safe(u'%s: <a href="%s">%s</a>' %
                                 (escape(capfirst(opts.verbose_name)),
                                  admin_url,
                                  escape(obj)))
            else:
                # Don't display link to edit, because it either has no
                # admin or is edited inline.
                from django.utils.encoding import force_unicode
                return u'%s: %s' % (capfirst(opts.verbose_name),
                                    force_unicode(obj))
    
        to_delete = collector.nested(format_callback)
    
        protected = [format_callback(obj) for obj in collector.protected]
    
        return to_delete, perms_needed, protected

django.contrib.admin.site.register(models.Document, DocumentAdmin)

django.contrib.admin.site.register(models.DocumentType, 
    django.contrib.admin.ModelAdmin)
