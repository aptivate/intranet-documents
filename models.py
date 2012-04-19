import binder.models
import django.dispatch

from django.db import models

# http://djangosnippets.org/snippets/1054/

class DocumentType(models.Model):
    class Meta:
        ordering = ('name',)
    
    name = models.CharField(max_length=255, unique=True)
    def __unicode__(self):
        return self.name

class Document(models.Model):
    class Meta:
        ordering = ('title',)
    
    title = models.CharField(max_length=255, unique=True)
    document_type = models.ForeignKey(DocumentType)
    programs = models.ManyToManyField(binder.models.Program)
    file = models.FileField(upload_to='documents', blank=True)
    notes = models.TextField(verbose_name="Description")
    authors = models.ManyToManyField(binder.models.IntranetUser,
        related_name="documents_authored")
    external_authors = models.CharField(max_length=255, blank=True)
    created = models.DateTimeField(auto_now_add = True)
    hyperlink = models.URLField(blank=True)
    uploader = models.ForeignKey(binder.models.IntranetUser,
        related_name="documents_uploaded", null=True)
    confidential = models.BooleanField("CONFIDENTIAL DO NOT SHARE OUTSIDE ATA")

    on_validate = django.dispatch.Signal(providing_args=['instance'])    
    
    def __unicode__(self):
        return "Document<%s>" % self.title
    
    def get_authors(self):
        return ', '.join([u.full_name for u in self.authors.all()])
    get_authors.short_description = 'Authors'

    def clean(self):
        # print "Document.clean starting"
        
        from django.core.exceptions import ValidationError
        # raise ValidationError("early validation error")
        
        models.Model.clean(self)
        
        if not self.file and not self.hyperlink:
            raise ValidationError('You must either attach a file ' +
                'or provide a hyperlink')
        
        try:
            self.on_validate.send(sender=Document, instance=self)
        except ValidationError as e:
            # print "on_validate raised a ValidationError: %s" % e
            raise e

        # print "Document.clean finished"
            
    @models.permalink
    def get_absolute_url(self):
        """
        The URL used in search results to link to the "document" found:
        we use this to point to the read-only view page.
        """
        return ('admin:documents_document_readonly', [str(self.id)])
