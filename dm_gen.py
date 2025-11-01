import treepoem
import base64
import io
import argparse
import json
import sys
import math
from PIL import Image

def generate_datamatrix_base64(text_data, barcode_type = "datamatrix", options=None, padding_px=0):
    """
    Generate Data Matrix image (PNG format) with treepoem (Ghostscript)
    """
    if options is None:
        options = {}

    try:
        # 1. Generate barcode as a Pillow image object without padding
        image = treepoem.generate_barcode(
            barcode_type=barcode_type,
            data=text_data,
            options=options
        )

        # 2. Add paddings
        if padding_px > 0:
            # 2a. Get current size
            original_width, original_height = image.size

            # 2b. Calc new size
            new_width = original_width + (padding_px * 2)
            new_height = original_height + (padding_px * 2)

            # 2c. Create the new canvas with white(255) (L means grayscale)
            new_image = Image.new('L', (new_width, new_height), 255)

            # 2d. Paste the barcode the center of the new canvas
            new_image.paste(image, (padding_px, padding_px))

            # 2e. Update Image object
            image = new_image

        # 3. Convert the image to PNG format on the memory buffer
        img_buffer = io.BytesIO()
        image.save(img_buffer, format="PNG")

        # 4. Get the image as byte stream
        img_bytes = img_buffer.getvalue()

        return img_bytes

    except (FileNotFoundError, RuntimeError) as e:
        print(
            f"Error: Dependency 'Ghostscript' not found (FileNotFoundError),\n"
            f"      Failed to processing (RuntimeError): {e}",
            file=sys.stderr
        )
        print(
            "Check if Ghostscript is installed"
            " or verify that the PATH is configured properly.",
            file=sys.stderr
        )
        return None
    except Exception as e:
        print(f"Unexpected error occurred: {e}", file=sys.stderr)
        return None

def main():
    """
    main function handling command line arguments and generate Data Matrix
    """
    parser = argparse.ArgumentParser(
        description="Generate Data Matrix (ECC 200) as a PNG file (Base64 encoding)"
    )

    parser.add_argument(
        "text",
        type=str,
        help="ASCII test data to encode"
    )

    parser.add_argument(
        "-t", "--type",
        type=str,
        default="datamatrix",
        help="Barcode type (e.g., datamatrix, qrcode). Default: datamatrix"
    )

    parser.add_argument(
        "-s", "--scale",
        type=int,
        default=2,
        help="Scaling factor: pixels per module (X and Y). Default: 2"
    )

    parser.add_argument(
        "-o", "--options",
        type=str,
        default="{}",
        help="The option for treepoem (JSON)"
             "ex.: '{\"version\": \"20x20\"}'"
    )

    parser.add_argument(
        "-p", "--padding",
        type=int,
        default=5,
        help="Padding around the barcode (num of pixels)"
    )

    args = parser.parse_args()

    try:
        options = json.loads(args.options)
    except json.JSONDecodeError:
        print(
            f"Error: Invalid JSON in --options: {args.options}",
            file=sys.stderr
        )
        return

    # Add scale from -s argument into the options dict
    # This will overwrite 'scaleX'/'scaleY' if they were also in the JSON string
    options['scaleX'] = args.scale
    options['scaleY'] = args.scale

    # Call generate function
    img_bytes = generate_datamatrix_base64(
        args.text,
        barcode_type=args.type,
        options=options,
        padding_px=args.padding
    )

    try:
        # 'wb' = Write Binary
        with open(f"{args.text}.png", 'wb') as f:
            f.write(img_bytes)
    except IOError as e:
        print(f"File write error: {e}")

    # Base64 encoding
    img_b64 = base64.b64encode(img_bytes).decode('utf-8')

    if img_b64:
        print("--- Data Matrix (Base64 PNG) ---")
        print(img_b64)

if __name__ == "__main__":
    main()