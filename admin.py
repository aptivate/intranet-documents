# http://www.ibm.com/developerworks/opensource/library/os-django-admin/index.html

import models
import django.contrib.admin

from binder.admin import AdminWithReadOnly
class DocumentAdmin(AdminWithReadOnly):
    list_display = ('title', models.Document.get_authors)
    
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

django.contrib.admin.site.register(models.Document, DocumentAdmin)

django.contrib.admin.site.register(models.DocumentType, 
    django.contrib.admin.ModelAdmin)
