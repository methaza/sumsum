from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from metafields.models import MetaFieldsMixin
from utils.datastructures import List
from utils.fields import ChoiceField, StringField, PositionField, ImageField
from utils.fields import TransStringField, TransHandleField, TransWysiwygField
from sumsum.middleware import get_request


COLUMN_CHOICES = (
    ('title', _('Product title')),
    ('type', _('Product type')),
    ('vendor', _('Product vendor')),
    ('variant_price', _('Product price')),
    ('tag', _('Product tag')),
    ('variant_compare_at_price', _('Compare at price')),
    ('variant_weight', _('Weight')),
    ('variat_inventory', _('Inventory stock')),
    ('variant_title', _("Variant's title"))
)


RELATION_CHOICES = (
    ('equals', _('is equal to')),
    ('not_equals', _('is not equal to')),
    ('greater_than', _('is greater than')),
    ('less_than', _('is less than')),
    ('starts_with', _('starts with')),
    ('ends_with', _('ends with')),
    ('contains', _('contains')),
    ('not_contains', _('does not contain')),
)


SORT_CHOICES = (
    ('manual', _('Manually')),
    ('best-selling', _('By best selling')),
    ('alpha-asc', _('Alphabetically: A-Z')),
    ('alpha-desc', _('Alphabetically: Z-A')),
    ('price-desc', _('By price: Highest to lowest')),
    ('price-asc', _('By price: Lowest to highest')),
    ('created-descending', _('By date: Newest to oldest')),
    ('created', _('By date: Oldest to newest')),
)

PUBLICATION_CHOICES = (
    ('global', _('Online store')),
)


class CustomCollectionManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.prefetch_related('product_set')


class CustomCollection(MetaFieldsMixin, models.Model):
    body_html_t = TransWysiwygField(_('description'))
    disjunctive = models.BooleanField(_('products can match any condition'), default=False)
    handle_t = TransHandleField(_('handle'), populate_from='title_t')
    image = ImageField(_('image'), upload_to='products')
    published = models.BooleanField(_('published'), default=True)
    published_at = models.DateTimeField(_('published at'), help_text=_('publish this collection on'), blank=True, null=True)
    published_scope = ChoiceField(_('visability'), choices=PUBLICATION_CHOICES)
    sort_order = ChoiceField(_('sort'), choices=SORT_CHOICES)
    template_suffix = StringField(_('template suffix'))
    title_t = TransStringField(_('title'), required=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    objects = CustomCollectionManager()

    class Meta:
        ordering = ('-title_t',)
        verbose_name = _('collection')
        verbose_name_plural = _('collections')

    def __str__(self):
        return self.title

    @cached_property
    def all_tags(self):
        """
        Returns a list of all product tags in a collection. collection.all_tags
        will return the full list of tags even when the collection view is
        filtered.

        collection.all_tags will return at most 1,000 tags.

        In comparison, collection.tags returns all tags for a collection for
        the current view. For example, if a collection is filtered by tag,
        collection.tags returns only the tags that match the current filter.
        """
        tags = set()
        for p in self.products:
            tags.union(p.tags)
        return List(sorted(tags))

    @cached_property
    def all_types(self):
        """
        Returns a list of all product types in a collection.
        """
        return List(sorted(filter(None, set(p.product_type for p in self.products))))

    @cached_property
    def all_products_count(self):
        """
        Returns the number of products in a collection.
        collection.all_products_count will return the total number of products
        even when the collection view is filtered.

        In comparison, collection.products_count returns all tags for a
        collection for the current view. For example, if a collection is
        filtered by tag, collection.products_count returns the number of
        products that match the current filter.
        """
        return len(self.products)

    @cached_property
    def all_vendors(self):
        """
        Returns a list of all product vendors in a collection.
        """
        return List(sorted(filter(None, set(p.vendor for p in self.products))))

    def current_type(self):
        """
        Returns the product type on a /collections/types?q=TYPE collection
        page.
        """
        request = get_request()
        if request.path.endswith('/types'):
            return request.GET.get('q')

    def current_vendor(self):
        """
        Returns the product vendor on a /collections/vendors?q=VENDOR
        collection page.
        """
        request = get_request()
        if request.path.endswith('/vendors'):
            return request.GET.get('q')

    @cached_property
    def default_sort_by(self):
        """
        Returns the sort order of the collection, which is set on the
        collection's page in your admin.
        """
        # inconsistant
        # API: https://help.shopify.com/api/reference/customcollection#sort-order-property
        # template: https://help.shopify.com/themes/liquid/objects/collection#collection-default_sort_by
        mapping = {
            'alpha-asc': 'title-descending',
            'alpha-desc': 'title-asc',
            'best-selling': 'best-selling',
            'created': 'created-ascending',
            'created-desc': 'created-descending',
            'manual': 'manual',
            'price-asc': 'price-ascending',
            'price-desc': 'price-descending',
        }
        return mapping[self.sort_order]

    def get_absolute_url(self):
        return '/collection/{}'.format(self.handle)

    @cached_property
    def description(self):
        """
        Alias to body_html
        """
        return self.body_html

    @cached_property
    def adjecant_products(self):
        request = get_request()
        # request.path should look something like: /collections/contemporary-cityscapes/products/auckland
        handle = request.path.split('/')[-1]
        res = {'next': False, 'previous': False}
        for j, p in enumerate(self.products):
            if p.handle == handle:
                if j + 1 < len(self.products):
                    res['next'] = self.products[j + 1]
                if j - 1 >= 0:
                    res['previous'] = self.products[j - 1]
        return res

    @cached_property
    def next_product(self):
        """
        Returns the URL of the next product in the collection. Returns nil if
        there is no next product.

        You can use collection.next_product and collection.previous_product
        with the within filter to create "next" and "previous" links in the
        product template.
        """
        return self.adjecant_products['next']

    @cached_property
    def previous_product(self):
        """
        Returns the URL of the previous product in the collection. Returns nil
        if there is no previous product.

        You can use collection.next_product and collection.previous_product
        with the within filter to create "next" and "previous" links in the
        product template.
        """
        return self.adjecant_products['previous']

    @cached_property
    def products(self):
        """
        Returns all of the products in a collection. You can show a maximum of
        50 products per page.

        Use the paginate tag to choose how many products are shown per page.
        """
        return List(self.product_set.all())

    def products_count(self):
        """
        Returns the number of products in a collection that match the current
        view. For example, if you are viewing a collection filtered by tag,
        collection.products_count will return the number of products that match
        the chosen tag.
        """
        raise NotImplemented

    def tags(self):
        """
        Returns the tags of products in a collection that match the current
        view. For example, if you are viewing a collection filtered by tag,
        collection.tags will return the tags for the products that match the
        current filter.
        """
        raise NotImplemented

    @cached_property
    def url(self):
        return self.get_absolute_url()


class Collect(models.Model):
    collection = models.ForeignKey('products.CustomCollection')
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    featured = models.BooleanField(_('featured'))
    position = PositionField()
    product = models.ForeignKey('products.Product')
    sort_value = models.CharField(_('sort value'), max_length=10, editable=False)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        ordering = ('product', 'collection', 'position')
        verbose_name = _('collect')
        verbose_name_plural = _('collects')

    def save(self, **kwargs):
        self.sort_value = format(self.position, '010')
        super().save(**kwargs)


class CollectionRule(models.Model):
    """
    We include products in collections according to the conditions defined here which
    means that we need to recalculate the collection:ns everytime a product is updated.
    We also need to re calculate whenever a rule is updated.
    """
    collection = models.ForeignKey(CustomCollection, verbose_name=_('collection'))
    column = ChoiceField(_('column'), choices=COLUMN_CHOICES)
    condition = StringField(_('condition'), blank=False)
    position = PositionField()
    relation = ChoiceField(_('relation'), choices=RELATION_CHOICES)

    class Meta:
        unique_together = (('collection', 'column', 'condition', 'relation'))
        ordering = ('position',)
        verbose_name = _('collection rule')
        verbose_name_plural = _('collection rules')

    def __str__(self):
        return '{} - {} {} {}'.format(
            self.collection,
            self.column,
            self.relation,
            self.condition
        )
