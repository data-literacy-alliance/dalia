"""Where is a MediaImage referenced? Used by the admin to protect images in use."""

from django.db.models import Q
from pages.models import MediaImage, Page, PageBlock


def find_usages(image: MediaImage) -> list[Page]:
    """Distinct pages referencing ``image`` as cover, block image or Markdown URL."""
    url = image.image.url if image.image else ""
    condition = Q(cover_image=image) | Q(blocks__image=image)
    if url:
        condition |= Q(content_md__contains=url) | Q(blocks__body_md__contains=url)
    return list(Page.objects.filter(condition).distinct().order_by("site", "language", "slug"))


def is_in_use(image: MediaImage) -> bool:
    return bool(find_usages(image))


def usage_counts(images) -> dict[int, int]:
    """Distinct-page usage count per image id, in a constant number of queries.

    Same semantics as ``len(find_usages(image))`` for each image, but computed
    for a whole list at once (admin changelist) instead of one query per row.
    """
    images = [image for image in images if image.pk]
    pages: dict[int, set[int]] = {image.pk: set() for image in images}
    urls = {image.image.url: image.pk for image in images if image.image}

    for image_id, page_id in Page.objects.filter(cover_image__in=pages).values_list(
        "cover_image_id", "pk"
    ):
        pages[image_id].add(page_id)
    for image_id, page_id in PageBlock.objects.filter(image__in=pages).values_list(
        "image_id", "page_id"
    ):
        pages[image_id].add(page_id)

    if urls:
        page_cond, block_cond = Q(), Q()
        for url in urls:
            page_cond |= Q(content_md__contains=url)
            block_cond |= Q(body_md__contains=url)
        texts = list(Page.objects.filter(page_cond).values_list("pk", "content_md"))
        texts += list(PageBlock.objects.filter(block_cond).values_list("page_id", "body_md"))
        for page_id, text in texts:
            for url, image_id in urls.items():
                if url in text:
                    pages[image_id].add(page_id)
    return {image_id: len(ids) for image_id, ids in pages.items()}
