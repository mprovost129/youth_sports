from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from core.image_utils import (
    MAX_IMAGE_UPLOAD_BYTES,
    TARGET_MAX_DIMENSION,
    process_listing_image,
)


def build_image_file(name='sample.jpg', size=(800, 800), image_format='JPEG', quality=95):
    buffer = BytesIO()
    image = Image.new('RGB', size, color='red')
    image.save(buffer, format=image_format, quality=quality)
    return SimpleUploadedFile(name=name, content=buffer.getvalue(), content_type=f'image/{image_format.lower()}')


class ImageUploadControlsTests(TestCase):
    def test_rejects_image_smaller_than_min_dimensions(self):
        uploaded = build_image_file(size=(100, 100))
        with self.assertRaises(ValidationError):
            process_listing_image(uploaded)

    def test_rejects_image_larger_than_max_file_size(self):
        content = b'x' * (MAX_IMAGE_UPLOAD_BYTES + 1)
        uploaded = SimpleUploadedFile(name='too-big.jpg', content=content, content_type='image/jpeg')
        with self.assertRaises(ValidationError):
            process_listing_image(uploaded)

    def test_resizes_large_image_to_target_dimension(self):
        uploaded = build_image_file(size=(2400, 1800), quality=98)
        processed = process_listing_image(uploaded)

        image = Image.open(BytesIO(processed.read()))
        self.assertLessEqual(image.size[0], TARGET_MAX_DIMENSION)
        self.assertLessEqual(image.size[1], TARGET_MAX_DIMENSION)
