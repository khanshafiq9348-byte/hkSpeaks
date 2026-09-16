import os
import io
import time
import uuid
import zipfile
import urllib.parse
import urllib.request
import logging
import asyncio
import random
from typing import Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
import httpx

from app.core.config import settings
from app.services.storage import storage_service

logger = logging.getLogger(__name__)

class ImageGeneratorService:
    @classmethod
    async def generate_single_image(
        cls,
        prompt: str,
        user_id: str,
        batch_id: str,
        item_id: str,
        index: int,
        width: int = 1024,
        height: int = 576,
        seed: int = 42
    ) -> Tuple[str, str]:
        """
        Synthesizes a REAL image from prompt and saves it into persistent storage.
        Handles provider 429 Too Many Requests with exponential backoff + jitter.
        Strictly verifies image format with Pillow before marking success.
        Returns: (storage_key, public_url)
        """
        import httpx
        import random

        clean_prompt = " ".join(prompt.split())[:350]
        if not clean_prompt:
            raise ValueError("Empty prompt text provided.")

        encoded_prompt = urllib.parse.quote(clean_prompt)
        max_attempts = 5
        image_bytes: Optional[bytes] = None
        last_error: Optional[str] = None

        # Build candidate URLs with primary dimensions and fallback dimensions
        url_candidates = [
            f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&seed={seed}&nologo=true",
            f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={min(width, 1024)}&height={min(height, 1024)}&seed={seed}&nologo=true",
            f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed}&nologo=true",
            f"https://image.pollinations.ai/prompt/{encoded_prompt}?seed={seed}",
            f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={min(width, 768)}&height={min(height, 768)}"
        ]

        async with httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "image/jpeg,image/png,image/webp,*/*;q=0.8"
            },
            follow_redirects=True,
            timeout=55.0
        ) as client:
            for attempt in range(max_attempts):
                target_url = url_candidates[attempt % len(url_candidates)]
                try:
                    logger.info(f"Generating image item #{index} (attempt {attempt+1}/{max_attempts}): {clean_prompt[:40]}...")
                    resp = await client.get(target_url)

                    if resp.status_code == 200:
                        raw_data = resp.content
                        if len(raw_data) > 1000:
                            # Strict verification of real image bytes
                            try:
                                img = Image.open(io.BytesIO(raw_data))
                                img.verify()
                                image_bytes = raw_data
                                logger.info(f"Item #{index} generated successfully: {len(raw_data)} bytes.")
                                break
                            except Exception as decode_err:
                                last_error = f"Invalid image encoding: {decode_err}"
                                logger.warning(f"Item #{index} image decode error: {decode_err}")
                        else:
                            last_error = f"Provider returned empty or truncated image ({len(raw_data)} bytes)"
                    elif resp.status_code == 429:
                        # Parse Retry-After if available, else exponential backoff with jitter
                        retry_after_hdr = resp.headers.get("retry-after")
                        if retry_after_hdr and retry_after_hdr.isdigit():
                            backoff = float(retry_after_hdr) + random.uniform(1.0, 2.5)
                        else:
                            backoff = min(25.0, (2 ** attempt) * 2.5 + random.uniform(1.0, 3.0))

                        last_error = f"HTTP 429: Provider queue busy. Retrying in {backoff:.1f}s..."
                        logger.warning(f"Item #{index} hit 429 Too Many Requests (attempt {attempt+1}/{max_attempts}). Backing off {backoff:.1f}s...")
                        await asyncio.sleep(backoff)
                        continue
                    else:
                        last_error = f"Provider HTTP {resp.status_code}"
                        logger.warning(f"Item #{index} HTTP status {resp.status_code}")
                except httpx.TimeoutException:
                    last_error = "Provider connection timed out after 55s."
                    logger.warning(f"Item #{index} timed out on attempt {attempt+1}.")
                except Exception as net_err:
                    last_error = f"Network error: {net_err}"
                    logger.warning(f"Item #{index} net error: {net_err}")

                # Cooldown between retry attempts
                await asyncio.sleep(min(15.0, 1.5 * (attempt + 1) + random.uniform(0.5, 1.5)))

        if not image_bytes:
            raise RuntimeError(f"Image generation failed: {last_error or 'No valid image returned by provider'}")

        # Store verified real image file
        storage_key, public_url = await storage_service.save_file(
            file_bytes=image_bytes,
            filename=f"{index:04d}_{item_id[:8]}.jpg",
            user_id=user_id,
            category=f"bulk_images/{batch_id}",
            mime_type="image/jpeg"
        )
        return storage_key, public_url

    @classmethod
    def create_batch_zip(
        cls,
        batch_id: str,
        user_id: str,
        items: list
    ) -> Tuple[str, str, int]:
        """
        Creates a real ZIP archive containing all completed images and manifest files.
        Returns: (zip_storage_key, zip_url, zip_size_bytes)
        """
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. Add images
            csv_lines = ["Index,ID,Status,Prompt,ImageURL\n"]
            for item in items:
                if item.status == "completed" and item.storage_key and os.path.exists(item.storage_key):
                    safe_slug = "".join(c for c in item.prompt_text[:30] if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
                    ext = os.path.splitext(item.storage_key)[1] or ".jpg"
                    entry_name = f"{item.prompt_index:04d}_{safe_slug}{ext}"
                    zf.write(item.storage_key, arcname=f"images/{entry_name}")

                esc_prompt = item.prompt_text.replace('"', '""')
                csv_lines.append(f'{item.prompt_index},"{item.id}","{item.status}","{esc_prompt}","{item.image_url or ""}"\n')

            # 2. Add prompt manifest
            zf.writestr("manifest_prompts.csv", "".join(csv_lines))

        zip_bytes = zip_buf.getvalue()
        storage_key, public_url = storage_service.save_file_sync(
            file_bytes=zip_bytes,
            filename=f"batch_{batch_id[:8]}_all_images.zip",
            user_id=user_id,
            category="bulk_images/zips",
            mime_type="application/zip"
        )
        return storage_key, public_url, len(zip_bytes)

image_generator_service = ImageGeneratorService()
