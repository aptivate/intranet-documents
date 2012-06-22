from django.core.validators import EMPTY_VALUES
from django.forms import ModelForm
from django.forms.util import ErrorList

from binder.widgets import AdminYesNoWidget, AdminFileWidgetWithSize

from models import Document

class DocumentForm(ModelForm):
    MULTIPLE_SELECT_HELP = u'Hold down Ctrl to select multiple options'
    
    class Meta:
        model = Document
        fields = ('title', 'document_type', 'programs', 'notes',
            'confidential', 'file', 'hyperlink', 'authors',
            'external_authors', 'uploader', 'deleted')

    def __init__(self, data=None, files=None, auto_id='id_%s', 
        prefix=None, initial=None, error_class=ErrorList, label_suffix=':', 
        empty_permitted=False, instance=None):
        
        super(DocumentForm, self).__init__(data, files, auto_id, prefix, 
            initial, error_class, label_suffix, empty_permitted, instance)
        
        self.fields['title'].required = False
        self.fields['document_type'].queryset.order_by('name')
        self.fields['programs'].help_text = self.MULTIPLE_SELECT_HELP
        self.fields['programs'].queryset.order_by('name')
        self.fields['authors'].required = False
        self.fields['authors'].help_text = self.MULTIPLE_SELECT_HELP
        self.fields['authors'].queryset.order_by('full_name')
        self.fields['confidential'].widget = AdminYesNoWidget()
        self.fields['uploader'].required = False
        self.fields['file'].widget = AdminFileWidgetWithSize()
        
    def clean(self):
        """
        If the title is not set, default to the name of the attached
        file with any extension (without spaces) removed.
        
        If the authors are not set, set the author to the current logged-in
        user.
        """
        
        cleaned_data = ModelForm.clean(self)
        
        if (cleaned_data['title'] in EMPTY_VALUES and
            cleaned_data.get('file', None) is not None):
            import re
            m = re.match('(.+)\.(\w+)', cleaned_data['file'].name)
            
            if m is not None:
                cleaned_data['title'] = m.group(1)
            else:
                cleaned_data['title'] = cleaned_data['file'].name

        if (cleaned_data['authors'] in EMPTY_VALUES):
            cleaned_data['authors'] = [self.request.user]
                
        return cleaned_data
