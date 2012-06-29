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
    fixtures = ['test_programs', 'test_permissions', 'test_users',
        'test_documenttypes']
    
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
        
        super(DocumentsModuleTest, self).login(user)
        self.assertIn(django_settings.SESSION_COOKIE_NAME, self.client.cookies) 
        
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
        
    def create_document_by_post(self, **kwargs):
        f = StringIO('foobar')
        setattr(f, 'name', 'boink.png')

        values = {
            'title': 'foo',
            'document_type': DocumentType.objects.all()[0].id,
            'programs': Program.objects.all()[0].id,
            'file': f,
            'notes': 'whee',
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

    def assert_create_document_by_post(self, **kwargs):
        response = self.create_document_by_post(**kwargs)
        self.assert_changelist_not_admin_form_with_errors(response)
        return response

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
        self.assert_create_document_by_post()

        # did it save?
        doc = Document.objects.get()
        self.assertEqual('foo', doc.title)
        self.assertEqual(DocumentType.objects.all()[0], doc.document_type)
        self.assertItemsEqual([Program.objects.all()[0]], doc.programs.all())
        import re
        self.assertRegexpMatches(doc.file.name, 'boink(_\d+)?.png',
            "Wrong name on uploaded file")
        self.assertEqual('whee', doc.notes)
        self.assertItemsEqual([], doc.authors.all())
    
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

    def test_word_2007_unicode(self):
        doc = Document()
        self.assign_fixture_to_filefield('smartquote-bullet.docx', doc.file) 
        from django.utils.encoding import force_unicode
        self.assertEquals(u'\u2019\n\u2022\t\n',
            force_unicode(self.index.prepare_text(doc)))

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
            "Sed in orci quis risus interdum lacinia ut eu nisl.\n",
            self.index.prepare_text(doc))

    def test_pdf_indexing(self):
        doc = Document()
        self.assign_fixture_to_filefield('word_pdf.pdf', doc.file) 
        
        self.assertEquals("\nLorem ipsum dolor sit amet, consectetur " +
            "adipiscing elit.\nPraesent pharetra urna eu arcu blandit " +
            "nec pretium odio fermentum. Sed in orci quis risus interdum " +
            "lacinia ut eu nisl.\n\n\n", self.index.prepare_text(doc))

    def assert_search_results_table_get_queryset(self, response):
        try:
            table = response.context['results_table']
        except KeyError as e:
            self.fail("No table in response context: %s" %
                response.context.keys())

        from search.tables import SearchTable 
        self.assertIsInstance(table, SearchTable)

        columns = table.base_columns.items()
        self.assertNotIn('score', [c[0] for c in columns],
            "Score column is disabled on request")
        
        data = table.data
        from django_tables2.tables import TableData
        self.assertIsInstance(data, TableData)
        
        queryset = data.queryset
        from haystack.query import SearchQuerySet
        self.assertIsInstance(queryset, SearchQuerySet)
        
        return table, queryset

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
        
        table, queryset = self.assert_search_results_table_get_queryset(response)
        
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
        self.assert_create_document_by_post(title='')

        # did it save?
        doc = Document.objects.get()
        self.assertEqual('boink', doc.title)

    def test_document_upload_without_author_does_not_set_author(self):
        self.assert_create_document_by_post(authors=None)

        # did it save?
        doc = Document.objects.get()
        self.assertItemsEqual([], doc.authors.all())

    def test_create_document_without_file_only_url_works(self):
        self.assert_create_document_by_post(file=None,
            hyperlink="http://foo.example.com/bar")

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
        
        doc = Document.objects.get(id=doc.id)
        self.assertTrue(doc.deleted, "Document should have been deleted")

    def test_uploader_can_delete_file(self):
        self.assert_create_document_by_post(title='whee')
        self.assert_delete_document(Document.objects.get(title="whee"))

    def test_admin_index_page_works(self):
        self.client.get(reverse("admin:index")) # no errors

    def test_admin_can_delete_file(self):
        self.client.logout() # default user

        self.login(self.john)
        self.assert_create_document_by_post(title='whee')
        self.client.logout()
        
        doc = Document.objects.get(title="whee")
        self.assertEqual(self.john, doc.uploader, "document uploader should " +
            "be John")
        
        self.login(self.ringo)
        self.assert_delete_document(Document.objects.get(title="whee"))

    def test_ordinary_user_cannot_delete_file(self):
        self.client.logout() # default user

        self.login(self.john)
        self.assert_create_document_by_post(title='whee')
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

    def assert_email(self, document, template):
        self.assertTrue(self.emails, "Expected email was not sent")
        self.assertEqual(1, len(self.emails),
            "Unexpectedly, more than one email was sent: %s" % self.emails)
        
        email = self.emails[0]
        
        expected_context = {
            'user': self.current_user,
            'settings': django_settings,
            'document': document,
        }
        
        self.assertDictContainsSubset(expected_context, email.context)
        
        from mail_templated import EmailMessage
        expected_email = EmailMessage(template, expected_context, 
            to=[self.current_user.email])

        self.assertEqual(expected_email.subject, email.subject)
        self.assertEqual(expected_email.from_email, email.from_email)
        self.assertItemsEqual([document.uploader.email], email.to)
        self.assertEqual(expected_email.body, email.body)
        
        history_url = reverse('admin:documents_document_history',
            args=[document.id])
        history_url = self.absolute_url(history_url)
        self.assertEqual(1, email.body.count(history_url), 
            "Couldn't find '%s' in response:\n\n%s" % (history_url, email.body))

    def assert_modification_email(self, document):
        self.assert_email(document, 'email/document_modified.txt.django')

    def fake_file_upload(self):
        f = StringIO('whee')
        setattr(f, 'name', 'boink.pdf')
        return f

    def change_document_by_post(self, document, **new_values):
        from django.forms.models import model_to_dict
        values = model_to_dict(document)
        values.update(new_values)

        response = self.client.post(
            reverse('admin:documents_document_change', args=[document.id]),
            values, follow=True)
        self.assert_changelist_not_admin_form_with_errors(response)
        return response

    def test_document_modify_by_different_user_sends_email(self):
        self.assert_create_document_by_post()

        doc = Document.objects.order_by('-id')[0]
        self.assert_no_emails()

        self.client.logout()
        self.login(self.ringo)
        
        self.change_document_by_post(doc, file=self.fake_file_upload())
        self.assert_modification_email(doc)

    def test_document_modify_by_same_user_does_not_send_email(self):
        self.assert_create_document_by_post()

        doc = Document.objects.order_by('-id')[0]
        self.assert_no_emails()

        self.change_document_by_post(doc, file=self.fake_file_upload())
        self.assert_no_emails()

    def test_document_without_uploader_does_not_crash(self):
        self.assert_create_document_by_post()
        
        doc = Document.objects.order_by('-id')[0]
        doc.uploader = None
        doc.save()
        
        self.client.get(reverse('admin:documents_document_readonly',
            args=[doc.id]))
        self.assert_no_emails()

    def test_view_permission_is_required_to_view_documents(self):
        self.assert_create_document_by_post()
        doc = Document.objects.order_by('-id')[0]
        
        from django.contrib.auth.models import User, Group
        guest = Group.objects.get(name="Guest")
        self.login(User.objects.get(groups=guest))
        
        groups = self.current_user.groups.all()
        self.assertEqual(1, len(groups),
            "this test requires that the current user is only in one group, " +
            "not %s" % groups)
        # to make it simpler to remove their view_document permission
        
        self.assertItemsEqual([], self.current_user.user_permissions.all(),
            "this test requires that the current user has no user permissions")
        # to make it simpler to remove their view_document permission
        
        user_group = groups[0]
        from django.contrib.auth.models import Permission
        view_document = Permission.objects.get(codename='view_document')
        self.assertIn(view_document, user_group.permissions.all(),
            ("this test requires that the user's group %s has the " +
            "view_document permission") % user_group)
        # to make it simpler to remove their view_document permission
        
        # change_document gives view_document permission, and we can't have that
        change_document = Permission.objects.get(codename='change_document')
        self.assertNotIn(change_document, user_group.permissions.all(),
            ("this test requires that the user's group %s lacks the " +
            "change_document permission") % user_group)
        
        response = self.client.get(reverse('admin:documents_document_readonly',
            args=[doc.id]))
        self.extract_admin_form(response) # check that there is one
        
        user_group.permissions.remove(view_document)
        
        from django.core.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            response = self.client.get(reverse('admin:documents_document_readonly',
                args=[doc.id]))
            
        # ensure that change_document permission works as well, for
        # backwards compatibility
        user_group.permissions.add(change_document)
        response = self.client.get(reverse('admin:documents_document_readonly',
            args=[doc.id]))
        self.extract_admin_form(response) # check that there is one
        
    def test_document_view_does_not_send_email(self):
        self.assert_create_document_by_post()

        doc = Document.objects.order_by('-id')[0]
        self.assert_no_emails()

        self.client.get(reverse('admin:documents_document_change',
            args=[doc.id]))
        self.assert_no_emails()

        self.client.get(reverse('admin:documents_document_readonly',
            args=[doc.id]))
        self.assert_no_emails()

    def test_document_delete_by_different_user_sends_email(self):
        self.assert_create_document_by_post()

        doc = Document.objects.order_by('-id')[0]
        self.assert_no_emails()

        self.client.logout()
        self.login(self.ringo)
        
        self.assert_delete_document(doc)
        self.assert_email(doc, 'email/document_deleted.txt.django')

    def test_document_delete_by_same_user_does_not_send_email(self):
        self.assert_create_document_by_post()
        
        doc = Document.objects.order_by('-id')[0]
        self.assert_no_emails()

        self.assert_delete_document(doc)
        self.assert_no_emails()
    
    def test_document_has_confidential_flag(self):
        self.assert_create_document_by_post(confidential=True)

        doc = Document.objects.order_by('-id')[0]
        self.assertTrue(doc.confidential)

        self.change_document_by_post(doc, confidential=False)
        doc = Document.objects.get(id=doc.id)
        self.assertFalse(doc.confidential)

        response = self.client.get(reverse('admin:documents_document_readonly',
            args=[doc.id]))
        self.assertEqual('No', self.extract_admin_form_field(response, 
            'confidential').contents())

    def test_uploader_field_shown_on_form(self):
        self.login()
        self.assert_create_document_by_post()
        doc = Document.objects.order_by('-id')[0]
        
        response = self.client.get(reverse('admin:documents_document_readonly',
            args=[doc.id]))
        field = self.extract_admin_form_field(response, 'uploader')

        response = self.client.get(reverse('admin:documents_document_change',
            args=[doc.id]))
        field = self.extract_admin_form_field(response, 'uploader')

        from django.contrib.admin.helpers import AdminReadonlyField
        self.assertIsInstance(field, AdminReadonlyField) 

    def test_document_download_link_shown_on_readonly_form(self):
        self.login()
        self.assert_create_document_by_post()
        doc = Document.objects.order_by('-id')[0]
        
        response = self.client.get(reverse('admin:documents_document_readonly',
            args=[doc.id]))
        field = self.extract_admin_form_field(response, 'file')
        field_name = field.field['field']
        self.assertEqual('file', field_name)
        
        from binder.widgets import AdminFileWidgetWithSize
        self.assertIsInstance(field.form[field_name].field.widget,
            AdminFileWidgetWithSize)
        
    def test_document_has_external_author_field(self):
        self.login()
        self.assert_create_document_by_post(external_authors="John Smith")
        doc = Document.objects.order_by('-id')[0]
        self.assertEqual("John Smith", doc.external_authors)

    """        
    def test_document_model_choice_fields_in_order(self):
        self.login()
        response = self.client.get(reverse('admin:documents_document_add'))
        
        document_type = self.extract_admin_form_field(response, 'document_type')
        self.assertItemsEqual(['name'], 
            document_type.field.field.queryset.query.order_by)

        programs = self.extract_admin_form_field(response, 'programs')
        self.assertItemsEqual(['name'], 
            programs.field.field.queryset.query.order_by)

        authors = self.extract_admin_form_field(response, 'authors')
        self.assertItemsEqual(['name'], 
            authors.field.field.queryset.query.order_by)
    """
        
    def test_document_admin_form_without_duplicate_fields(self):
        response = self.client.get(reverse('admin:documents_document_add'))
        self.assertEqual(response.status_code, 200)

        form = self.assertInDict('adminform', response.context)
        seen = {}
        for name, value in self.extract_fields(form):
            self.assertNotIn(name, seen, ("%s field should not have been " +
                "included twice") % name)
            seen[name] = True
            
    def test_delete_document_is_soft_delete(self):
        self.login()
        self.assert_create_document_by_post(external_authors="John Smith")
        doc = Document.objects.order_by('-id')[0]
        
        url = reverse('admin:documents_document_readonly', args=[doc.id])
        self.client.get(url)
        delete_button = self.get_page_element('.//' + self.xhtml('input') +
            '[@value="Delete"]')
        self.assertEqual("location.assign('delete/'); return false;",
            delete_button.attrib['onclick'])
        
        path,dot,file = url.rpartition("/")
        url = path + "/delete/"
        response = self.client.get(url)
        title = self.get_page_element('./' + self.xhtml('head') +
            '/' + self.xhtml('title'))
        from django.conf import settings
        self.assertEqual("%s | Are you sure?" % settings.APP_TITLE, title.text)

        # import pdb; pdb.set_trace()
        response = self.client.post(url, {"dummy": "whee"}, follow=True)
        list_url = reverse('admin:documents_document_changelist')
        list_url_full = response.real_request.build_absolute_uri(list_url)
        self.assertSequenceEqual([(list_url_full, 302)], 
            getattr(response, 'redirect_chain', []),
            "successful document deletion should be followed by a redirect, "+
            "not this: %s" % response.content)

        # document should still exist
        doc = Document.objects.get(pk=doc.id)
        self.assertTrue(doc.deleted)
        
        # and be listed only once in the search index, with deleted=True
        from search.queries import SearchQuerySetWithAllFields
        sqs = SearchQuerySetWithAllFields().models(Document)
        
        def assert_not_in_index(queryset):
            self.assertSequenceEqual([], list(queryset),
                "Document should not be listed with %s" % queryset.query)
        assert_not_in_index(sqs.exclude(deleted=True))

        def assert_in_index(queryset):
            self.assertEqual(1, len(queryset),
                "Document should be listed with %s" % queryset.query)
            result = queryset[0]
            self.assertEqual(doc.deleted, result.deleted,
                "Document stored in search index should have deleted=%s" %
                doc.deleted)
        assert_in_index(sqs.filter(deleted=True))

        # clearing the deleted flag should cause the document to only
        # be listed once, with deleted=False
        doc.deleted = False
        doc.save()
        
        assert_not_in_index(sqs.filter(deleted=True))
        assert_in_index(sqs.exclude(deleted=True))

    def test_search_results_hide_deleted_documents(self):
        self.login()
        
        self.assert_create_document_by_post(title="Dunce",
            external_authors="John Smith", deleted=True)
        dunce = Document.objects.order_by('-id')[0]
        self.assertTrue(dunce.deleted)
        
        self.assert_create_document_by_post(title="Nonce",
            external_authors="John Smith")
        nonce = Document.objects.order_by('-id')[0]
        self.assertFalse(nonce.deleted)
        
        response = self.client.get(reverse('search'), {'q': 'Dunce'})
        self.assertEqual(response.status_code, 200)
        table, queryset = self.assert_search_results_table_get_queryset(response)
        self.assertSequenceEqual([], list(queryset),
            "Unexpected search results")

        response = self.client.get(reverse('search'), {'q': 'Nonce'})
        self.assertEqual(response.status_code, 200)
        table, queryset = self.assert_search_results_table_get_queryset(response)
        self.assertEqual(1, len(queryset),
            "Missing or unexpected search results: %s" % queryset)
        self.assertEqual(nonce.id, queryset[0].pk)

    def test_external_author_is_indexed(self):
        self.assert_create_document_by_post(external_authors="Wonka")

        doc = Document.objects.get()
        self.assertEqual('Wonka', doc.external_authors)
        
        response = self.client.get(reverse('search'), {'q': 'Wonka'})
        self.assertEqual(response.status_code, 200)
        table, queryset = self.assert_search_results_table_get_queryset(response)
        self.assertEqual(1, len(queryset),
            "Missing or unexpected search results: %s" % queryset)
        self.assertEqual(doc.id, queryset[0].pk)
        self.assertEqual(doc.title, queryset[0].title)
