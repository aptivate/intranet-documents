"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from StringIO import StringIO

from django.conf import settings as django_settings
from django.contrib import admin 
from django.contrib.auth import login
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.utils.functional import curry

from binder.test_utils import AptivateEnhancedTestCase, SuperClient
from binder.models import IntranetUser, Program
from documents.admin import DocumentAdmin
from documents.models import Document, DocumentType

class DocumentsModuleTest(AptivateEnhancedTestCase):
    fixtures = ['test_permissions', 'test_users']
    
    def setUp(self):
        super(DocumentsModuleTest, self).setUp()
        
        self.john = IntranetUser.objects.get(username='john')

        # run a POST just to get a response with its embedded request...
        self.login()
        response = self.client.post(reverse('admin:documents_document_add'))
        # fails with PermissionDenied if our permissions are wrong

        self.index = self.unified_index.get_index(Document) 
    
    def login(self):
        self.assertTrue(self.client.login(username=self.john.username,
            password='johnpassword'), "Login failed")
        self.assertIn(django_settings.SESSION_COOKIE_NAME, self.client.cookies) 
        """
        print "session cookie = %s" % (
            self.client.cookies[django_settings.SESSION_COOKIE_NAME])
        """
        
    def test_create_document_object(self):
        doc = Document(title="foo", document_type=DocumentType.objects.all()[0],
            notes="bonk")
        doc.file.save(name="whee", content=ContentFile("wee willy wonka"))
        doc.programs = Program.objects.all()[:2]  
        doc.authors = [self.john.id]

        self.assertItemsEqual([doc], Document.objects.all())

    def test_document_admin_class(self):
        self.assertIn(Document, admin.site._registry)
        self.assertIsInstance(admin.site._registry[Document], DocumentAdmin)
        
    def extract_error_message(self, response):
        error_message = response.parsed.findtext('.//div[@class="error-message"]')
        if error_message is None:
            error_message = response.parsed.findtext('.//p[@class="errornote"]')
        
        if error_message is not None:
            # extract individual field errors, if any
            more_error_messages = response.parsed.findtext('.//td[@class="errors-cell"]')
            if more_error_messages is not None:
                error_message += more_error_messages
            
            # trim and canonicalise whitespace
            error_message = error_message.strip()
            import re
            error_message = re.sub('\\s+', ' ', error_message)
            
        # return message or None
        return error_message

    def extract_error_message_fallback(self, response):
        error_message = self.extract_error_message(response)
        if error_message is None:
            error_message = response.content
        return error_message
        
    def test_create_document_admin(self):
        response = self.client.get(reverse('admin:documents_document_add'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(None, self.extract_error_message(response))
        # self.assertEqual('admin/login.html', response.template_name)
        
        f = StringIO('foobar')
        setattr(f, 'name', 'boink.png')

        # without login, should fail and tell us to log in
        self.client.logout()        
        response = self.client.post(reverse('admin:documents_document_add'),
            {
                'title': 'foo',
                'document_type': DocumentType.objects.all()[0].id,
                'programs': Program.objects.all()[0].id,
                'file': f,
                'notes': 'whee',
                'authors': self.john.id,
            }, follow=True)
        self.assertEqual("Please check your user name and password and try again.",
            self.extract_error_message(response),
            "POST without login did not fail as expected: %s" % response.content)

        self.login()
        response = self.client.retry()
        # print response.content
        # print "%s" % response.context
        self.assertTrue(hasattr(response, 'context'), "Missing context " +
            "in response: %s: %s" % (response, dir(response)))
        self.assertIsNotNone(response.context, "Empty context in response: " +
            "%s: %s" % (response, dir(response)))
        
        # If this succeeds, we get redirected to the changelist_view.
        # If it fails, we get sent back to the edit page, with an error.
        if 'adminform' in response.context: 
            self.assertDictEqual({}, response.context['adminform'].form.errors)
            for fieldset in response.context['adminform']:
                for line in fieldset:
                    self.assertIsNone(line.errors)
                    for field in line:
                        self.assertIsNone(field.errors)
            self.assertIsNone(response.context['adminform'].form.non_field_errors)
            self.assertIsNone(self.extract_error_message(response))

        self.assertNotIn('adminform', response.context, "Unexpected " +
            "admin form in response context: %s" % response)
        self.assertIn('cl', response.context, "Missing changelist " +
            "in response context: %s" % response)

        # did it save?
        doc = Document.objects.get()
        self.assertEqual('foo', doc.title)
        self.assertEqual(DocumentType.objects.all()[0], doc.document_type)
        self.assertItemsEqual([Program.objects.all()[0]], doc.programs.all())
        import re
        self.assertRegexpMatches(doc.file.name, 'boink(_\d+)?.png',
            "Wrong name on uploaded file")
        self.assertEqual('whee', doc.notes)
        self.assertItemsEqual([self.john], doc.authors.all())
    
    def test_word_2003_document_indexing(self):
        doc = Document()
        self.assign_fixture_to_filefield('word_2003.doc', doc.file) 
        
        self.assertEquals("Lorem ipsum dolor sit amet, consectetur " +
            "adipiscing elit.\n\n\nPraesent pharetra urna eu arcu blandit " +
            "nec pretium odio fermentum. Sed in orci quis risus interdum " +
            "lacinia ut eu nisl.\n\n", self.index.prepare_text(doc))

    def test_word_2007_document_indexing(self):
        doc = Document()
        self.assign_fixture_to_filefield('word_2007.docx', doc.file) 
        
        self.assertEquals("Lorem ipsum dolor sit amet, consectetur " +
            "adipiscing elit.\n\nPraesent pharetra urna eu arcu blandit " +
            "nec pretium odio fermentum. Sed in orci quis risus interdum " +
            "lacinia ut eu nisl.\n", self.index.prepare_text(doc))

    def test_excel_2003_indexing(self):
        doc = Document()
        self.assign_fixture_to_filefield('excel_2003.xls', doc.file) 
        
        self.assertEquals("Sheet1\n\tLorem ipsum dolor sit amet, " +
            "consectetur adipiscing elit.\t\tPraesent pharetra urna eu " +
            "arcu blandit nec pretium odio fermentum.\n\tSed in orci " +
            "quis risus interdum lacinia ut eu nisl.\n\t\tSed facilisis " +
            "nibh eu diam tincidunt pellentesque semper nulla auctor.\n" +
            "\n\nSheet2\n\t\n\n\nSheet3\n\t\n\n\n",
            self.index.prepare_text(doc))

    def test_excel_2007_indexing(self):
        doc = Document()
        self.assign_fixture_to_filefield('excel_2007.xlsx', doc.file) 
        
        self.assertEquals("Sheet1\n\tLorem ipsum dolor sit amet, " +
            "consectetur adipiscing elit.\tPraesent pharetra urna eu " +
            "arcu blandit nec pretium odio fermentum.\n\tSed in orci " +
            "quis risus interdum lacinia ut eu nisl.\n\tSed facilisis " +
            "nibh eu diam tincidunt pellentesque semper nulla auctor." +
            "\n\n&\"Times New Roman,Regular\"&12&A\t\n\n" +
            "&\"Times New Roman,Regular\"&12Page &P\t\n\n\nSheet2\n\n" +
            "&\"Times New Roman,Regular\"&12&A\t\n\n" +
            "&\"Times New Roman,Regular\"&12Page &P\t\n\n\nSheet3\n\n" +
            "&\"Times New Roman,Regular\"&12&A\t\n\n" +
            "&\"Times New Roman,Regular\"&12Page &P\t\n\n\n",
            self.index.prepare_text(doc))

    def test_powerpoint_2003_indexing(self):
        doc = Document()
        self.assign_fixture_to_filefield('powerpoint_2003.ppt', doc.file) 
        
        self.assertEquals("Lorem Ipsum\n" +
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.\n" +
            "Praesent pharetra urna eu arcu blandit nec pretium odio " +
            "fermentum.\n" +
            "Sed in orci quis risus interdum lacinia ut eu nisl.\n\n\n\n\n",
            self.index.prepare_text(doc))

    def test_powerpoint_2007_indexing(self):
        doc = Document()
        self.assign_fixture_to_filefield('powerpoint_2007.pptx', doc.file) 
        
        self.assertEquals("Lorem Ipsum\n" +
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.\n" +
            "Praesent pharetra urna eu arcu blandit nec pretium odio " +
            "fermentum.\n" +
            "Sed in orci quis risus interdum lacinia ut eu nisl.\n\n",
            self.index.prepare_text(doc))

    def test_pdf_indexing(self):
        doc = Document()
        self.assign_fixture_to_filefield('word_pdf.pdf', doc.file) 
        
        self.assertEquals("Lorem ipsum dolor sit amet, consectetur " +
            "adipiscing elit.\nPraesent pharetra urna eu arcu blandit " +
            "nec pretium odio fermentum. Sed in orci quis risus interdum " +
            "lacinia ut eu nisl.\n\n\n", self.index.prepare_text(doc))

    def test_document_page_changelist(self):
        doc = Document(title='foo', document_type=DocumentType.objects.all()[0],
            notes="bonk")
        # from lib.monkeypatch import breakpoint
        # breakpoint()
        doc.file.save(name="foo", content=ContentFile("foo bar baz"))
        doc.authors = [self.john]
        doc.programs = [Program.objects.all()[1]]
        doc.save()
        
        response = self.client.get(reverse('search'), {'q': 'foo'})
        self.assertEqual(response.status_code, 200)
        
        try:
            table = response.context['table']
        except KeyError as e:
            self.fail("No table in response context: %s" %
                response.context.keys())

        from search.search import SearchTable 
        self.assertIsInstance(table, SearchTable)
        
        data = table.data
        from django_tables2.tables import TableData
        self.assertIsInstance(data, TableData)
        
        queryset = data.queryset
        from haystack.query import SearchQuerySet
        self.assertIsInstance(queryset, SearchQuerySet)
        
        self.assertEqual(1, len(queryset), "Unexpected search results: %s" %
            queryset)
        from haystack.utils import get_identifier
        self.assertEqual(get_identifier(doc), queryset[0].id)
        # print object.__str__(queryset[0])

        self.assertEqual("<a href='%s'>%s</a>" % (doc.get_absolute_url(),
            doc.title), table.render_title(doc.title, queryset[0]))

        row = table.page.object_list.next()
        self.assertEqual("<a href='%s'>%s</a>" % (doc.get_absolute_url(),
            doc.title), row['title'])
        self.assertEqual(doc.authors.all()[0].full_name, row['authors'])
        self.assertEqual(doc.created, row['created'])
        self.assertEqual(doc.programs.all()[0].name, row['programs'])
        self.assertEqual(doc.document_type.name, row['document_type'])
        