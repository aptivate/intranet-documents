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
    fixtures = ['ata_programs', 'test_permissions', 'test_users']
    
    def setUp(self):
        super(DocumentsModuleTest, self).setUp()
        
        self.john = IntranetUser.objects.get(username='john')
        self.ringo = IntranetUser.objects.get(username='ringo')
        self.ken = IntranetUser.objects.get(username='ken')

        # run a POST just to get a response with its embedded request...
        self.login()
        response = self.client.post(reverse('admin:documents_document_add'))
        # fails with PermissionDenied if our permissions are wrong

        self.index = self.unified_index.get_index(Document) 
    
    def login(self, user=None):
        if user is None:
            user = self.john
            
        self.assertTrue(self.client.login(username=user.username,
            password='johnpassword'), "Login failed")
        self.assertIn(django_settings.SESSION_COOKIE_NAME, self.client.cookies) 
        """
        print "session cookie = %s" % (
            self.client.cookies[django_settings.SESSION_COOKIE_NAME])
        """
        
        self.current_user = user
        
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

    def create_document_by_post(self, **kwargs):
        f = StringIO('foobar')
        setattr(f, 'name', 'boink.png')

        values = {
            'title': 'foo',
            'document_type': DocumentType.objects.all()[0].id,
            'programs': Program.objects.all()[0].id,
            'file': f,
            'notes': 'whee',
            'authors': self.john.id,
        }
        values.update(kwargs)

        # None cannot be sent over HTTP, so this means
        # "delete the parameter" rather than "send a None value"
        none_keys = [k for k, v in values.iteritems() if v is None]
        for k in none_keys:
            del values[k]
        
        response = self.client.post(reverse('admin:documents_document_add'),
            values, follow=True)

        return response

    def assert_changelist_not_admin_form_with_errors(self, response):
        self.assertTrue(hasattr(response, 'context'), "Missing context " +
            "in response: %s: %s" % (response, dir(response)))
        self.assertIsNotNone(response.context, "Empty context in response: " +
            "%s: %s" % (response, dir(response)))

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

    def test_create_document_admin(self):
        response = self.client.get(reverse('admin:documents_document_add'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(None, self.extract_error_message(response))
        # self.assertEqual('admin/login.html', response.template_name)

        # without login, should fail and tell us to log in
        self.client.logout()
        response = self.create_document_by_post()
        self.assertEqual("Please check your user name and password and try again.",
            self.extract_error_message(response),
            "POST without login did not fail as expected: %s" % response.content)

        self.login()
        response = self.create_document_by_post()

        # If this succeeds, we get redirected to the changelist_view.
        # If it fails, we get sent back to the edit page, with an error.
        self.assert_changelist_not_admin_form_with_errors(response)

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
        doc = Document(title='foo bar', document_type=DocumentType.objects.all()[0],
            notes="bonk")
        # from lib.monkeypatch import breakpoint
        # breakpoint()
        doc.file.save(name="foo", content=ContentFile("foo bar baz"))
        doc.authors = [self.john]
        doc.programs = [Program.objects.all()[1]]
        doc.save()

        doc2 = Document(title='foo baz', document_type=DocumentType.objects.all()[1],
            notes="whee")
        # from lib.monkeypatch import breakpoint
        # breakpoint()
        doc2.file.save(name="foo", content=ContentFile("foo bar baz"))
        doc2.authors = [self.ringo]
        doc2.programs = [Program.objects.all()[2]]
        doc2.save()
        
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
        
        self.assertEqual(2, len(queryset), "Unexpected search results: %s" %
            queryset)
        from haystack.utils import get_identifier
        result = [q for q in queryset if q.id == get_identifier(doc)]
        self.assertEqual(get_identifier(doc), result[0].id)
        result = result[0]
        # print object.__str__(queryset[0])

        self.assertEqual("<a href='%s'>%s</a>" % (doc.get_absolute_url(),
            doc.title), table.render_title(doc.title, result))

        row = [r for r in table.page.object_list if r.record.pk == doc.id][0]
        self.assertEqual("<a href='%s'>%s</a>" % (doc.get_absolute_url(),
            doc.title), row['title'])
        self.assertEqual(doc.authors.all()[0].full_name, row['authors'])
        self.assertEqual(doc.created, row['created'])
        self.assertEqual(doc.programs.all()[0].name, row['programs'])
        self.assertEqual(doc.document_type.name, row['document_type'])
    
    def test_document_upload_without_title_sets_title(self):
        response = self.create_document_by_post(title='')
        self.assert_changelist_not_admin_form_with_errors(response)

        # did it save?
        doc = Document.objects.get()
        self.assertEqual('boink', doc.title)

    def test_document_upload_without_author_sets_author(self):
        response = self.create_document_by_post(authors=None)
        self.assert_changelist_not_admin_form_with_errors(response)

        # did it save?
        doc = Document.objects.get()
        self.assertItemsEqual([self.john], doc.authors.all())

    def test_create_document_without_file_only_url_works(self):
        response = self.create_document_by_post(file=None,
            hyperlink="http://foo.example.com/bar")
        self.assert_changelist_not_admin_form_with_errors(response)

    def assert_delete_document(self, doc):
        response = self.client.get(reverse('admin:documents_document_delete',
            args=[doc.id]))
        self.assertEqual(response.status_code, 200,
            "deletion confirmation page should load successfully, " +
            "not this: %s" % response.content)
        self.assertTemplateUsed(response, "admin/delete_confirmation.html",
            "deletion confirmation page should render with " +
            "delete_confirmation.html template, not this: %s" % 
            response.content)
        self.assertFalse(response.context['perms_lacking'],
            "should not be any permissions lacking")
        self.assertFalse(response.context['protected'],
            "should not be protected")
        self.assertEqual("Are you sure?", response.context['title'], 
            "should be a question: are you sure?")

        # import pdb; pdb.set_trace()
        response = self.client.post(reverse('admin:documents_document_delete',
            args=[doc.id]), {'post': 'yes'}, follow=True)
        url = response.real_request.build_absolute_uri(
            reverse('admin:documents_document_changelist'))
        self.assertSequenceEqual([(url, 302)], response.redirect_chain,
            "successful document deletion should be followed by a redirect, "+
            "not this: %s" % response.content)
        
        self.assertSequenceEqual([], Document.objects.filter(id=doc.id),
            "Document should have been deleted")

    def test_uploader_can_delete_file(self):
        response = self.create_document_by_post(title="whee")
        self.assert_changelist_not_admin_form_with_errors(response)
        self.assert_delete_document(Document.objects.get(title="whee"))

    def test_admin_index_page_works(self):
        self.client.get(reverse("admin:index")) # no errors

    def test_admin_can_delete_file(self):
        self.client.logout() # default user

        self.login(self.john)
        response = self.create_document_by_post(title="whee")
        self.assert_changelist_not_admin_form_with_errors(response)
        self.client.logout()
        
        doc = Document.objects.get(title="whee")
        self.assertEqual(self.john, doc.uploader, "document uploader should " +
            "be John")
        
        self.login(self.ringo)
        self.assert_delete_document(Document.objects.get(title="whee"))

    def test_ordinary_user_cannot_delete_file(self):
        self.client.logout() # default user

        self.login(self.john)
        response = self.create_document_by_post(title="whee")
        self.assert_changelist_not_admin_form_with_errors(response)
        self.client.logout()
        
        doc = Document.objects.get(title="whee")
        self.assertEqual(self.john, doc.uploader, "document uploader should " +
            "be John")
        
        self.login(self.ken)
        from django.core.exceptions import PermissionDenied
        
        def get(): self.client.get(reverse('admin:documents_document_delete',
            args=[doc.id]))
        self.assertRaises(PermissionDenied, get)

        def post(): self.client.post(reverse('admin:documents_document_delete',
            args=[doc.id]), {'post': 'yes'})
        self.assertRaises(PermissionDenied, post)

    def assert_no_emails(self):
        self.assertListEqual([], self.emails)

    def assert_modification_email(self, document):
        self.assertEqual(1, len(self.emails), self.emails)
        email = self.emails[0]
        
        """
        expected_email = self.load_email_from_template(
            'email/document_modified.txt.django', document=doc,
            user=self.current_user, to=doc.uploader.email)
        """
        
        expected_context = {
            'document': document,
            'user': self.current_user,
            'settings': django_settings,
        }
        
        self.assertDictContainsSubset(expected_context, email.context)
        
        from mail_templated import EmailMessage
        expected_email = EmailMessage('email/document_modified.txt.django',
            expected_context, to=[self.current_user.email])

        self.assertEqual(expected_email.subject, email.subject)
        self.assertEqual(expected_email.from_email, email.from_email)
        self.assertItemsEqual([document.uploader.email], email.to)
        self.assertEqual(expected_email.body, email.body)
        
        history_url = reverse('admin:documents_document_history',
            args=[document.id])
        history_url = self.absolute_url(history_url)
        self.assertEqual(1, email.body.count(history_url), 
            "Couldn't find '%s' in response:\n\n%s" % (history_url, email.body))
        
    def test_document_modify_by_different_user_sends_email(self):
        self.create_document_by_post()
        doc = Document.objects.order_by('-id')[0]
        self.assert_no_emails()

        self.client.logout()
        self.login(self.ringo)
        
        from django.forms.models import model_to_dict
        values = model_to_dict(doc)

        f = StringIO('whee')
        setattr(f, 'name', 'boink.pdf')
        values['file'] = f
        
        response = self.client.post(
            reverse('admin:documents_document_change', args=[doc.id]),
            values, follow=True)
        self.assert_changelist_not_admin_form_with_errors(response)

        self.assert_modification_email(doc)

    def test_document_modify_by_same_user_does_not_send_email(self):
        self.create_document_by_post()
        doc = Document.objects.order_by('-id')[0]
        self.assert_no_emails()

        from django.forms.models import model_to_dict
        values = model_to_dict(doc)

        f = StringIO('whee')
        setattr(f, 'name', 'boink.pdf')
        values['file'] = f
        
        response = self.client.post(
            reverse('admin:documents_document_change', args=[doc.id]),
            values, follow=True)
        self.assert_changelist_not_admin_form_with_errors(response)

        self.assert_no_emails()

    def test_document_without_uploader_does_not_crash(self):
        self.create_document_by_post()
        doc = Document.objects.order_by('-id')[0]
        doc.uploader = None
        doc.save()
        
        self.client.get(reverse('admin:documents_document_readonly',
            args=[doc.id]))
        
        self.assert_no_emails()
        
    def test_document_view_does_not_send_email(self):
        self.create_document_by_post()
        doc = Document.objects.order_by('-id')[0]
        self.assert_no_emails()

        self.client.get(reverse('admin:documents_document_change',
            args=[doc.id]))
        self.assert_no_emails()

        self.client.get(reverse('admin:documents_document_readonly',
            args=[doc.id]))
        self.assert_no_emails()
