# http://www.ibm.com/developerworks/opensource/library/os-django-admin/index.html

import models
import django.contrib.admin

from django.core.validators import EMPTY_VALUES
from django.forms import ModelForm
from binder.admin import AdminWithReadOnly

class DocumentForm(ModelForm):
    class Meta:
        model = models.Document

    def clean(self):
        """If the title is not set, default to the name of the attached
        file with any extension (without spaces) removed."""
        
        cleaned_data = ModelForm.clean(self)
        
        if (cleaned_data['title'] in EMPTY_VALUES and
            cleaned_data['file'] is not None):
            import re
            m = re.match('(.+)\.(\w+)', cleaned_data['file'].name)
            
            if m is not None:
                cleaned_data['title'] = m.group(1)
            else:
                cleaned_data['title'] = cleaned_data['file'].name
                
        return cleaned_data
            
    def _post_clean(self):
        # import pdb; pdb.set_trace()
        return super(DocumentForm, self)._post_clean()

class DocumentAdmin(AdminWithReadOnly):
    list_display = ('title', models.Document.get_authors)
    form = DocumentForm

    formfield_overrides = {
        'title': {'required': False}
    }

    def formfield_for_dbfield(self, db_field, **kwargs):
        # import pdb; pdb.set_trace()
        return super(DocumentAdmin, self).formfield_for_dbfield(db_field, **kwargs)
    
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
