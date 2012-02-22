# http://www.ibm.com/developerworks/opensource/library/os-django-admin/index.html

import models
import django.contrib.admin

from django.core.validators import EMPTY_VALUES
from django.forms import ModelForm
from django.forms.util import ErrorList
from binder.admin import AdminWithReadOnly

class DocumentForm(ModelForm):
    title = models.Document._meta.get_field('title').formfield(required=False)
    authors = models.Document._meta.get_field('authors').formfield(required=False)
    
    def __init__(self, request, data=None, files=None, auto_id='id_%s', 
        prefix=None, initial=None, error_class=ErrorList, label_suffix=':', 
        empty_permitted=False, instance=None):
        ModelForm.__init__(self, data, files, auto_id, prefix, initial,
                error_class, label_suffix, empty_permitted, instance)
        self.request = request

    class Meta:
        model = models.Document

    def clean(self):
        """
        If the title is not set, default to the name of the attached
        file with any extension (without spaces) removed.
        
        If the authors are not set, set the author to the current logged-in
        user.
        """
        
        cleaned_data = ModelForm.clean(self)
        
        if (cleaned_data['title'] in EMPTY_VALUES and
            cleaned_data['file'] is not None):
            import re
            m = re.match('(.+)\.(\w+)', cleaned_data['file'].name)
            
            if m is not None:
                cleaned_data['title'] = m.group(1)
            else:
                cleaned_data['title'] = cleaned_data['file'].name

        if (cleaned_data['authors'] in EMPTY_VALUES):
            # import pdb; pdb.set_trace()
            cleaned_data['authors'] = [self.request.user]
                
        return cleaned_data
        
    """    
    def _post_clean(self):
        import pdb; pdb.set_trace()
        return super(DocumentForm, self)._post_clean()
    
    def save(self, commit=True):
        import pdb; pdb.set_trace()
        return ModelForm.save(self, commit=commit)
    """

class DocumentAdmin(AdminWithReadOnly):
    list_display = ('title', models.Document.get_authors)

    """
    formfield_overrides = {
        'title': {'required': False},
        'authors': {'required': False},
    }

    def formfield_for_dbfield(self, db_field, **kwargs):
        import pdb; pdb.set_trace()
        return super(DocumentAdmin, self).formfield_for_dbfield(db_field, **kwargs)
    """
    
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
    
    """
    def add_view(self, request, form_url='', extra_context=None):
        import pdb; pdb.set_trace()
        return AdminWithReadOnly.add_view(self, request, form_url=form_url, extra_context=extra_context)
    """

    def get_form(self, request, obj=None, **kwargs):
        """
        The form needs to know who the current user is, but doesn't normally
        have access to the request to find out.
        
        Unfortunately, this function doesn't return a form object, but a
        form class, so we can't just stuff the request into it. But we can
        return a curried generator function instead.
        """
        
        def generator(data=None, files=None, auto_id='id_%s', prefix=None, 
            initial=None, error_class=ErrorList, label_suffix=':', 
            empty_permitted=False, instance=None):
            return DocumentForm(request, data, files, auto_id, prefix, initial,
                error_class, label_suffix, empty_permitted, instance)
        
        # to keep ModelAdmin.get_fieldsets() happy:
        generator.base_fields = DocumentForm.base_fields
        
        return generator

django.contrib.admin.site.register(models.Document, DocumentAdmin)

django.contrib.admin.site.register(models.DocumentType, 
    django.contrib.admin.ModelAdmin)
