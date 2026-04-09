from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

MAX_IMAGE_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
MIN_IMAGE_WIDTH = 120
MIN_IMAGE_HEIGHT = 120
MAX_IMAGE_WIDTH = 5000
MAX_IMAGE_HEIGHT = 5000
TARGET_MAX_DIMENSION = 1400
JPEG_QUALITY = 82


def process_listing_image(uploaded):
    if not uploaded:
        return uploaded

    if uploaded.size > MAX_IMAGE_UPLOAD_BYTES:
        raise ValidationError('Image must be 5MB or smaller.')

    filename = (uploaded.name or '').lower()
    if filename.endswith('.svg'):
        uploaded.seek(0)
        return uploaded

    uploaded.seek(0)
    try:
        image = Image.open(uploaded)
    except Exception as exc:
        raise ValidationError('Uploaded file is not a valid image.') from exc

    width, height = image.size
    if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
        raise ValidationError(
            f'Image is too small. Minimum size is {MIN_IMAGE_WIDTH}x{MIN_IMAGE_HEIGHT}px.'
        )
    if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
        raise ValidationError(
            f'Image is too large. Maximum size is {MAX_IMAGE_WIDTH}x{MAX_IMAGE_HEIGHT}px.'
        )

    should_resize = width > TARGET_MAX_DIMENSION or height > TARGET_MAX_DIMENSION
    should_compress = uploaded.size > 1_500_000
    if not should_resize and not should_compress:
        uploaded.seek(0)
        return uploaded

    original_format = (image.format or '').upper()
    image = image.copy()
    image.thumbnail((TARGET_MAX_DIMENSION, TARGET_MAX_DIMENSION), Image.Resampling.LANCZOS)

    output = BytesIO()
    image_format = original_format

    if image_format in {'JPEG', 'JPG'}:
        if image.mode in {'RGBA', 'LA', 'P'}:
            image = image.convert('RGB')
        image.save(output, format='JPEG', quality=JPEG_QUALITY, optimize=True, progressive=True)
        content_type = 'image/jpeg'
        extension = 'jpg'
    elif image_format == 'WEBP':
        image.save(output, format='WEBP', quality=JPEG_QUALITY, method=6)
        content_type = 'image/webp'
        extension = 'webp'
    elif image_format == 'PNG':
        image.save(output, format='PNG', optimize=True)
        content_type = 'image/png'
        extension = 'png'
    else:
        uploaded.seek(0)
        return uploaded

    output.seek(0)
    stem = uploaded.name.rsplit('.', 1)[0] if uploaded.name else 'listing_image'
    new_name = f'{stem}.{extension}'
    return SimpleUploadedFile(
        name=new_name,
        content=output.read(),
        content_type=content_type,
    )
